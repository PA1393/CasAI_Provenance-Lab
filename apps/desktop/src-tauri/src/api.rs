use std::time::Duration;

const API_ORIGIN: &str = "https://casaiprovenancelab.vercel.app";
const MAX_REQUEST_BYTES: usize = 12_000_000;
const MAX_RESPONSE_BYTES: usize = 32_000_000;

pub struct ApiClient(reqwest::Client);

impl ApiClient {
    pub fn new() -> Result<Self, reqwest::Error> {
        reqwest::Client::builder()
            .redirect(reqwest::redirect::Policy::none())
            .connect_timeout(Duration::from_secs(8))
            .build()
            .map(Self)
    }
}

#[derive(serde::Serialize)]
pub struct ApiResponse {
    status: u16,
    body: String,
}

pub fn app_navigation_allowed(scheme: &str, host: Option<&str>, port: Option<u16>) -> bool {
    matches!(
        (scheme, host, port),
        ("tauri", Some("localhost"), None) | ("https", Some("tauri.localhost"), None | Some(443))
    ) || (cfg!(debug_assertions)
        && matches!(
            (scheme, host, port),
            ("http", Some("127.0.0.1"), Some(1420))
        ))
}

fn valid_id(value: &str) -> bool {
    !value.is_empty()
        && value.len() <= 128
        && value
            .bytes()
            .all(|byte| byte.is_ascii_alphanumeric() || byte == b'-' || byte == b'_')
}

fn valid_hash(value: &str) -> bool {
    value.strip_prefix("sha256:").is_some_and(|hex| {
        hex.len() == 64
            && hex
                .bytes()
                .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
    })
}

fn request_allowed(method: &str, path: &str, body: Option<&str>) -> bool {
    if body.is_some_and(|value| value.len() > MAX_REQUEST_BYTES)
        || (method == "GET" && body.is_some())
    {
        return false;
    }
    let parts: Vec<_> = path.split('/').collect();
    match (method, parts.as_slice()) {
        ("GET", ["", "health" | "openapi.json"]) => true,
        ("GET" | "POST", ["", "api", "v1", "research-objects" | "runs"]) => true,
        ("GET", ["", "api", "v1", "research-objects" | "runs", id]) => valid_id(id),
        ("GET", ["", "api", "v1", "research-objects", id, "runs"]) => valid_id(id),
        (
            "GET",
            [
                "",
                "api",
                "v1",
                "runs",
                id,
                "provenance" | "results" | "export",
            ],
        ) => valid_id(id),
        ("POST", ["", "api", "v1", "rag", "search"]) => true,
        ("POST", ["", "api", "v1", "intake", "research-drafts"]) => true,
        ("POST", ["", "api", "v1", "intake", "datasets", "inspect-text"]) => true,
        ("GET", ["", "api", "v1", "intake", "research-drafts", id]) => valid_hash(id),
        ("POST", ["", "api", "v1", "intake", "research-drafts", id, "confirm"]) => valid_hash(id),
        ("GET", ["", "api", "v1", "intake", "confirmed-versions", id, "fasta"]) => valid_hash(id),
        (
            "POST",
            [
                "",
                "api",
                "v1",
                "intake",
                "confirmed-versions",
                id,
                "research-objects",
            ],
        ) => valid_hash(id),
        _ => false,
    }
}

#[tauri::command]
pub async fn api_request(
    window: tauri::WebviewWindow,
    client: tauri::State<'_, ApiClient>,
    method: String,
    path: String,
    body: Option<String>,
) -> Result<ApiResponse, String> {
    let source = window.url().map_err(|_| "Cannot verify caller")?;
    if !app_navigation_allowed(source.scheme(), source.host_str(), source.port())
        || !request_allowed(&method, &path, body.as_deref())
    {
        return Err("Desktop request is outside the permitted API scope".into());
    }
    let timeout = if path == "/health" {
        8
    } else if method == "GET" {
        15
    } else {
        120
    };
    let mut request = client
        .0
        .request(
            reqwest::Method::from_bytes(method.as_bytes()).map_err(|_| "Invalid request method")?,
            format!("{API_ORIGIN}{path}"),
        )
        .timeout(Duration::from_secs(timeout));
    if let Some(content) = body {
        request = request
            .header("content-type", "application/json")
            .body(content);
    }
    // Never forward browser cookies, API keys, arbitrary headers or redirects.
    let mut response = request.send().await.map_err(|error| {
        if error.is_timeout() {
            "Backend request timed out; a submitted run may still have completed. Check Runs before resubmitting."
        } else {
            "Cannot reach the CasAI backend. Check your connection and deployment."
        }.to_string()
    })?;
    if response
        .content_length()
        .is_some_and(|length| length > MAX_RESPONSE_BYTES as u64)
    {
        return Err("Backend response exceeds the desktop size limit".into());
    }
    let status = response.status().as_u16();
    let mut bytes = Vec::new();
    while let Some(chunk) = response
        .chunk()
        .await
        .map_err(|_| "Backend response interrupted")?
    {
        if bytes.len() + chunk.len() > MAX_RESPONSE_BYTES {
            return Err("Backend response exceeds the desktop size limit".into());
        }
        bytes.extend_from_slice(&chunk);
    }
    let body = String::from_utf8(bytes).map_err(|_| "Backend returned non-text content")?;
    Ok(ApiResponse { status, body })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn only_known_read_and_submit_routes_are_allowed() {
        for path in [
            "/health",
            "/openapi.json",
            "/api/v1/runs",
            "/api/v1/research-objects",
            "/api/v1/runs/demo-1/results",
            "/api/v1/runs/demo-1/export",
            "/api/v1/research-objects/demo-1/runs",
        ] {
            assert!(request_allowed("GET", path, None));
        }
        assert!(request_allowed("POST", "/api/v1/runs", Some("{}")));
        assert!(request_allowed(
            "POST",
            "/api/v1/intake/datasets/inspect-text",
            Some("{}")
        ));
        let hash = format!("sha256:{}", "a".repeat(64));
        assert!(request_allowed(
            "GET",
            &format!("/api/v1/intake/confirmed-versions/{hash}/fasta"),
            None
        ));
        assert!(request_allowed(
            "POST",
            &format!("/api/v1/intake/confirmed-versions/{hash}/research-objects"),
            Some("{}")
        ));
        assert!(!request_allowed(
            "GET",
            "/api/v1/intake/confirmed-versions/../fasta",
            None
        ));
        assert!(request_allowed(
            "GET",
            &format!("/api/v1/intake/research-drafts/{hash}"),
            None
        ));
        assert!(request_allowed(
            "POST",
            &format!("/api/v1/intake/research-drafts/{hash}/confirm"),
            Some("{}")
        ));
        for (method, path) in [
            ("DELETE", "/api/v1/runs"),
            ("POST", "/health"),
            ("GET", "https://evil.example"),
            ("GET", "/api/v1/runs/../secret"),
            ("GET", "/api/v1/runs/id?token=x"),
            ("GET", "/api/v1/runs/%2fsecret"),
            ("POST", "/api/v1/intake/research-drafts/not-a-hash/confirm"),
        ] {
            assert!(!request_allowed(method, path, None));
        }
    }

    #[test]
    fn request_bodies_are_bounded_and_get_has_no_body() {
        assert!(!request_allowed("GET", "/health", Some("{}")));
        assert!(!request_allowed(
            "POST",
            "/api/v1/runs",
            Some(&"x".repeat(MAX_REQUEST_BYTES + 1))
        ));
    }

    #[test]
    fn remote_pages_cannot_become_app_navigation() {
        assert!(app_navigation_allowed("tauri", Some("localhost"), None));
        assert!(app_navigation_allowed(
            "https",
            Some("tauri.localhost"),
            None
        ));
        assert!(!app_navigation_allowed("https", Some("evil.example"), None));
        assert!(!app_navigation_allowed(
            "https",
            Some("tauri.localhost.evil.example"),
            None
        ));
        assert!(!app_navigation_allowed("file", None, None));
    }
}
