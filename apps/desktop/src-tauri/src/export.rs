use std::io::Write;

fn valid_export(filename: &str, content: &str) -> bool {
    let Some(id) = filename
        .strip_prefix("casai-run-")
        .and_then(|s| s.strip_suffix(".json"))
    else {
        return false;
    };
    if id.is_empty()
        || id.len() > 128
        || !id
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'-' || b == b'_')
        || content.len() > 32_000_000
    {
        return false;
    }
    let Ok(value) = serde_json::from_str::<serde_json::Value>(content) else {
        return false;
    };
    value["schema_version"] == "casai.demo-export.v1"
        && value["run_id"] == id
        && value["files"].as_array().is_some_and(|files| {
            let mut names = files
                .iter()
                .filter_map(|file| file["path"].as_str())
                .collect::<Vec<_>>();
            names.sort();
            files.len() == 4
                && names == ["input.json", "provenance.json", "results.json", "run.json"]
        })
}

fn valid_fasta(filename: &str, content: &str) -> bool {
    let Some(hash) = filename
        .strip_prefix("casai-confirmed-")
        .and_then(|s| s.strip_suffix(".fasta"))
    else {
        return false;
    };
    if hash.len() != 64
        || !hash
            .bytes()
            .all(|b| b.is_ascii_digit() || (b'a'..=b'f').contains(&b))
        || content.len() > 12_000_000
        || !content.starts_with('>')
        || !content.ends_with('\n')
    {
        return false;
    }
    let tag = format!("casai_version=sha256:{hash}");
    let mut has_sequence = false;
    for line in content.lines() {
        if line.starts_with('>') {
            if !line.contains(&tag) || line.chars().any(|c| c.is_control()) {
                return false;
            }
        } else if line.is_empty() || !line.bytes().all(|b| b.is_ascii_uppercase()) {
            return false;
        } else {
            has_sequence = true;
        }
    }
    has_sequence
}

#[tauri::command]
pub async fn save_feedback(
    window: tauri::WebviewWindow,
    filename: String,
    content: String,
) -> Result<bool, String> {
    let source = window.url().map_err(|_| "Cannot verify caller")?;
    if !crate::api::app_navigation_allowed(source.scheme(), source.host_str(), source.port())
        || !valid_feedback(&filename, &content)
    {
        return Err("Invalid feedback report or caller".into());
    }
    save_selected(window, filename, content, "Save demo feedback", "json").await
}

fn valid_feedback(filename: &str, content: &str) -> bool {
    if filename != "casai-demo-feedback.json" || content.len() > 32_000 {
        return false;
    }
    let Ok(serde_json::Value::Object(report)) = serde_json::from_str(content) else {
        return false;
    };
    let fields = [
        "schema_version",
        "app_version",
        "created_at",
        "platform",
        "context",
        "category",
        "expected",
        "actual",
    ];
    report.len() == fields.len()
        && fields.iter().all(|key| {
            report
                .get(*key)
                .and_then(|v| v.as_str())
                .is_some_and(|s| s.len() <= 8_000)
        })
        && report["schema_version"] == "casai.demo-feedback.v1"
        && report["actual"]
            .as_str()
            .is_some_and(|s| !s.trim().is_empty())
}

#[tauri::command]
pub async fn save_fasta(
    window: tauri::WebviewWindow,
    filename: String,
    content: String,
) -> Result<bool, String> {
    let source = window.url().map_err(|_| "Cannot verify caller")?;
    if !crate::api::app_navigation_allowed(source.scheme(), source.host_str(), source.port())
        || !valid_fasta(&filename, &content)
    {
        return Err("Invalid confirmed FASTA or caller".into());
    }
    save_selected(window, filename, content, "Save normalized FASTA", "fasta").await
}

#[tauri::command]
pub async fn save_export(
    window: tauri::WebviewWindow,
    filename: String,
    content: String,
) -> Result<bool, String> {
    let source = window.url().map_err(|_| "Cannot verify caller")?;
    if !crate::api::app_navigation_allowed(source.scheme(), source.host_str(), source.port())
        || !valid_export(&filename, &content)
    {
        return Err("Invalid demo export or caller".into());
    }
    save_selected(
        window,
        filename,
        content,
        "Save CasAI recorded data",
        "json",
    )
    .await
}

async fn save_selected(
    window: tauri::WebviewWindow,
    filename: String,
    content: String,
    title: &str,
    extension: &str,
) -> Result<bool, String> {
    // The webview never supplies an absolute path. Only the user's native Save
    // selection grants a destination, and existing files are never overwritten.
    let Some(file) = rfd::AsyncFileDialog::new()
        .set_parent(&window)
        .set_title(title)
        .set_file_name(&filename)
        .add_filter("CasAI data", &[extension])
        .save_file()
        .await
    else {
        return Ok(false);
    };
    let path = file.path().to_owned();
    tauri::async_runtime::spawn_blocking(move || write_new_file(&path, &content))
        .await
        .map_err(|_| "Save task interrupted".to_string())?
}

fn write_new_file(path: &std::path::Path, content: &str) -> Result<bool, String> {
    let mut target = std::fs::OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(path)
        .map_err(|_| "Choose a new filename; existing files will not be overwritten".to_string())?;
    target
        .write_all(content.as_bytes())
        .and_then(|_| target.sync_all())
        .map_err(|_| {
            "Save failed; inspect the selected file for an incomplete package".to_string()
        })?;
    Ok(true)
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn saves_exact_utf8_bytes_and_never_overwrites() {
        let nonce = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let path = std::env::temp_dir().join(format!(
            "casai-save-test-{}-{nonce}.json",
            std::process::id()
        ));
        let content = "{\"feedback\":\"Test → saved\"}";
        assert!(write_new_file(&path, content).unwrap());
        assert_eq!(std::fs::read_to_string(&path).unwrap(), content);
        assert!(write_new_file(&path, "replacement").is_err());
        assert_eq!(std::fs::read_to_string(&path).unwrap(), content);
        std::fs::remove_file(path).unwrap();
    }

    #[test]
    fn feedback_is_bounded_and_has_only_review_fields() {
        let mut report = serde_json::json!({
            "schema_version": "casai.demo-feedback.v1", "app_version": "demo-review-1",
            "created_at": "2026-11-02", "platform": "Test OS", "context": "/runs/demo",
            "category": "export", "expected": "Save", "actual": "Saved"
        });
        assert!(valid_feedback(
            "casai-demo-feedback.json",
            &report.to_string()
        ));
        assert!(!valid_feedback("../escape.json", &report.to_string()));
        report["actual"] = serde_json::json!("");
        assert!(!valid_feedback(
            "casai-demo-feedback.json",
            &report.to_string()
        ));
        report["actual"] = serde_json::json!("Saved");
        report["sequence"] = serde_json::json!("Unexpected data");
        assert!(!valid_feedback(
            "casai-demo-feedback.json",
            &report.to_string()
        ));
        assert!(!valid_feedback(
            "casai-demo-feedback.json",
            &"x".repeat(32_001)
        ));
    }

    #[test]
    fn only_bounded_run_json_packages_are_accepted() {
        let content = r#"{"schema_version":"casai.demo-export.v1","run_id":"test","files":[{"path":"input.json"},{"path":"provenance.json"},{"path":"results.json"},{"path":"run.json"}]}"#;
        assert!(valid_export("casai-run-test.json", content));
        assert!(!valid_export("../../escape.json", content));
        assert!(!valid_export("casai-run-other.json", content));
        assert!(!valid_export(
            "casai-run-test.json",
            &content.replace("input.json", "../secret")
        ));
        assert!(!valid_export("casai-run-test.json", "{}"));
    }

    #[test]
    fn fasta_saves_accept_only_named_confirmed_sequences() {
        let hash = "a".repeat(64);
        let name = format!("casai-confirmed-{hash}.fasta");
        let content = format!(">record casai_version=sha256:{hash}\nACGT\n");
        assert!(valid_fasta(&name, &content));
        assert!(!valid_fasta("../escape.fasta", &content));
        assert!(!valid_fasta(&name, "plain text"));
        assert!(!valid_fasta(&name, &content.replace("ACGT", "acgt")));
        assert!(!valid_fasta(&name, &content.replace("ACGT", "../escape")));
    }
}
