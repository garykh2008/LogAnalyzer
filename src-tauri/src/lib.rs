// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
mod engine;
mod stream;

use std::collections::HashMap;
use std::sync::RwLock;
use tauri::{State, Emitter};
use crate::engine::{LogEngine, FilterItem};
use crate::stream::StreamState;

struct AppState {
    engines: RwLock<HashMap<String, LogEngine>>,
}

#[tauri::command]
fn load_log(state: State<'_, AppState>, filepath: String) -> Result<usize, String> {
    {
        let engines = state.engines.read().map_err(|e| e.to_string())?;
        if let Some(engine) = engines.get(&filepath) {
            return Ok(engine.line_count());
        }
    }
    // Create engine OUTSIDE any lock
    let engine = LogEngine::new(&filepath)?;
    let count = engine.line_count();
    let mut engines = state.engines.write().map_err(|e| e.to_string())?;
    engines.insert(filepath, engine);
    Ok(count)
}

#[tauri::command]
fn close_log(state: State<'_, AppState>, filepath: String) -> Result<(), String> {
    let mut engines = state.engines.write().map_err(|e| e.to_string())?;
    engines.remove(&filepath);
    Ok(())
}

#[tauri::command]
fn get_lines(state: State<'_, AppState>, filepath: String, indices: Vec<usize>) -> Result<Vec<String>, String> {
    let engines = state.engines.read().map_err(|e| e.to_string())?;
    let engine = engines.get(&filepath).ok_or_else(|| "Log file not loaded".to_string())?;

    let lines = indices.iter()
        .map(|&idx| engine.get_line(idx))
        .collect();
    Ok(lines)
}

#[tauri::command]
fn search_log(state: State<'_, AppState>, filepath: String, query: String, is_regex: bool, case_sensitive: bool) -> Result<Vec<usize>, String> {
    let engines = state.engines.read().map_err(|e| e.to_string())?;
    let engine = engines.get(&filepath).ok_or_else(|| "Log file not loaded".to_string())?;

    engine.search(&query, is_regex, case_sensitive)
}

#[tauri::command]
fn filter_log(state: State<'_, AppState>, filepath: String, filters: Vec<FilterItem>) -> Result<(Vec<u8>, Vec<usize>, Vec<usize>, Vec<(String, String, usize)>), String> {
    let engines = state.engines.read().map_err(|e| e.to_string())?;
    let engine = engines.get(&filepath).ok_or_else(|| "Log file not loaded".to_string())?;

    engine.filter(&filters)
}

#[tauri::command]
fn open_file_dialog() -> Result<Option<String>, String> {
    let file = rfd::FileDialog::new()
        .add_filter("Log Files", &["log", "txt", "tat"])
        .pick_file();
    Ok(file.map(|p| p.to_string_lossy().to_string()))
}

#[tauri::command]
fn save_file_dialog(default_name: String, extension: String) -> Result<Option<String>, String> {
    let file = rfd::FileDialog::new()
        .set_file_name(&default_name)
        .add_filter("Files", &[&extension])
        .save_file();
    Ok(file.map(|p| p.to_string_lossy().to_string()))
}

#[tauri::command]
fn read_text_file(path: String) -> Result<String, String> {
    std::fs::read_to_string(path).map_err(|e| e.to_string())
}

#[tauri::command]
fn write_text_file(path: String, content: String) -> Result<(), String> {
    std::fs::write(path, content).map_err(|e| e.to_string())
}

#[tauri::command]
fn create_temp_log(content: String) -> Result<String, String> {
    let timestamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis();
    let tmp_dir = std::env::temp_dir();
    let filename = format!("loganalyzer_clipboard_{}.log", timestamp);
    let path = tmp_dir.join(filename);
    std::fs::write(&path, content).map_err(|e| e.to_string())?;
    Ok(path.to_string_lossy().to_string())
}

#[tauri::command]
fn delete_file(path: String) -> Result<(), String> {
    let canonical = std::path::Path::new(&path).canonicalize()
        .map_err(|e| format!("Path not found: {}", e))?;
    let tmp_dir = std::env::temp_dir().canonicalize()
        .map_err(|e| format!("Temp dir error: {}", e))?;
    if !canonical.starts_with(&tmp_dir) {
        return Err("Only temp directory files can be deleted this way".to_string());
    }
    let filename = canonical.file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("");
    if !filename.starts_with("loganalyzer_clipboard_") {
        return Err("Only clipboard temp files can be deleted this way".to_string());
    }
    std::fs::remove_file(&canonical).map_err(|e| e.to_string())
}

/// Parse CLI arguments matching the original Python app behaviour:
///   LogAnalyzer.exe [log1 log2 *.log ...] [-f filter.tat]
struct CliArgs {
    /// Expanded list of log file paths (glob-resolved)
    log_files: Vec<String>,
    /// Optional .tat filter file path
    filter_file: Option<String>,
}

fn parse_cli_args() -> CliArgs {
    let raw: Vec<String> = std::env::args().skip(1).collect();
    let mut log_patterns: Vec<String> = Vec::new();
    let mut filter_file: Option<String> = None;
    let mut i = 0;
    while i < raw.len() {
        match raw[i].as_str() {
            "-f" | "--filter" => {
                i += 1;
                if i < raw.len() {
                    filter_file = Some(raw[i].clone());
                }
            }
            arg if !arg.starts_with('-') => {
                log_patterns.push(arg.to_string());
            }
            _ => {} // Ignore unknown flags (Tauri own flags)
        }
        i += 1;
    }

    // Expand globs (e.g., *.log)
    let mut log_files: Vec<String> = Vec::new();
    for pattern in &log_patterns {
        if let Ok(matches) = glob::glob(pattern) {
            let mut matched: Vec<String> = matches
                .filter_map(|m| m.ok())
                .filter_map(|p| p.canonicalize().ok())
                .map(|p| p.to_string_lossy().to_string())
                .collect();
            if matched.is_empty() {
                // Fallback: pass the raw path if glob yields nothing
                let p = std::path::Path::new(pattern);
                if p.exists() {
                    if let Ok(abs) = p.canonicalize() {
                        matched.push(abs.to_string_lossy().to_string());
                    }
                }
            }
            log_files.extend(matched);
        }
    }

    // Resolve filter path
    let filter_file = filter_file.and_then(|f| {
        let p = std::path::Path::new(&f);
        if p.exists() {
            p.canonicalize().ok().map(|a| a.to_string_lossy().to_string())
        } else {
            None
        }
    });

    CliArgs { log_files, filter_file }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let cli = parse_cli_args();

    tauri::Builder::default()
        .manage(AppState {
            engines: RwLock::new(HashMap::new()),
        })
        .manage(StreamState::new())
        .plugin(tauri_plugin_opener::init())
        .setup(move |app| {
            let has_logs = !cli.log_files.is_empty();
            let has_filter = cli.filter_file.is_some();

            if has_logs || has_filter {
                let app_handle = app.handle().clone();
                let log_files = cli.log_files.clone();
                let filter_file = cli.filter_file.clone();

                std::thread::spawn(move || {
                    // Small delay to let the frontend finish mounting
                    std::thread::sleep(std::time::Duration::from_millis(600));

                    // Emit log files first so tabs are created
                    if has_logs {
                        let _ = app_handle.emit("cli-open-files", log_files);
                    }

                    // Then emit the filter file (frontend applies it after logs are loaded)
                    if let Some(f) = filter_file {
                        std::thread::sleep(std::time::Duration::from_millis(200));
                        let _ = app_handle.emit("cli-open-filter", f);
                    }
                });
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            load_log,
            close_log,
            get_lines,
            search_log,
            filter_log,
            open_file_dialog,
            save_file_dialog,
            read_text_file,
            write_text_file,
            create_temp_log,
            delete_file,
            stream::start_file_tail,
            stream::stop_stream,
            stream::set_stream_filters,
            stream::get_stream_lines,
            stream::get_stream_codes
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
