#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod api;
mod export;

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            use tauri::Manager;
            app.manage(api::ApiClient::new()?);
            let configuration = app
                .config()
                .app
                .windows
                .first()
                .ok_or("missing main window")?;
            tauri::WebviewWindowBuilder::from_config(app, configuration)?
                .on_navigation(|url| {
                    url.username().is_empty()
                        && url.password().is_none()
                        && api::app_navigation_allowed(url.scheme(), url.host_str(), url.port())
                })
                .build()?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            api::api_request,
            export::save_export,
            export::save_fasta
        ])
        .run(tauri::generate_context!())
        .expect("failed to run CasAI Provenance Lab desktop shell");
}
