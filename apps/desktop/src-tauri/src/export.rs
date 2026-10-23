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
    // The webview never supplies an absolute path. Only the user's native Save
    // selection grants a destination, and existing files are never overwritten.
    let Some(file) = rfd::AsyncFileDialog::new()
        .set_title("Save CasAI recorded data")
        .set_file_name(&filename)
        .add_filter("JSON package", &["json"])
        .save_file()
        .await
    else {
        return Ok(false);
    };
    let path = file.path().to_owned();
    tauri::async_runtime::spawn_blocking(move || {
        let mut target = std::fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(path)
            .map_err(|_| {
                "Choose a new filename; existing files will not be overwritten".to_string()
            })?;
        target
            .write_all(content.as_bytes())
            .and_then(|_| target.sync_all())
            .map_err(|_| {
                "Save failed; inspect the selected file for an incomplete package".to_string()
            })?;
        Ok(true)
    })
    .await
    .map_err(|_| "Save task interrupted".to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;
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
}
