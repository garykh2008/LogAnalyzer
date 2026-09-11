// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
mod engine;
mod remote;
mod stream;

use std::collections::HashMap;
use std::sync::RwLock;
use tauri::{State, Emitter, Manager};
use crate::engine::{LogEngine, FilterItem};
use crate::stream::StreamState;

struct AppState {
    engines: RwLock<HashMap<String, LogEngine>>,
}

/// Per-purpose last-used directory for file dialogs, keyed by dialog kind
/// ("log", "folder", "filter", "save_log", "save_notes", "exe"). "filter" is
/// shared by Import Filters and Save Filters As so they track the same folder.
/// Without this, Windows gives every dialog the same single remembered
/// location, so opening a log drags Import Filters (and friends) along.
#[derive(Default)]
struct DialogDirs(RwLock<HashMap<String, std::path::PathBuf>>);

impl DialogDirs {
    /// Start a dialog for `kind` from its remembered directory, if still valid.
    fn apply(&self, dialog: rfd::FileDialog, kind: &str) -> rfd::FileDialog {
        let dir = self.0.read().ok().and_then(|m| m.get(kind).cloned());
        match dir {
            Some(d) if d.is_dir() => dialog.set_directory(d),
            _ => dialog,
        }
    }

    /// Remember the directory containing `picked` for `kind`.
    fn remember(&self, kind: &str, picked: &std::path::Path) {
        let dir = if picked.is_dir() {
            picked.to_path_buf()
        } else {
            picked.parent().map(|p| p.to_path_buf()).unwrap_or_default()
        };
        if !dir.as_os_str().is_empty() && dir.is_dir() {
            if let Ok(mut m) = self.0.write() {
                m.insert(kind.to_string(), dir);
            }
        }
    }
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

/// Save a static log to `path`. An empty `indices` writes the whole file (full
/// view); otherwise only the given display lines are written (filtered view).
#[tauri::command]
fn save_log(state: State<'_, AppState>, filepath: String, path: String, indices: Vec<usize>) -> Result<usize, String> {
    let engines = state.engines.read().map_err(|e| e.to_string())?;
    let engine = engines.get(&filepath).ok_or_else(|| "Log file not loaded".to_string())?;

    let lines: Vec<String> = if indices.is_empty() {
        (0..engine.line_count()).map(|i| engine.get_line(i)).collect()
    } else {
        indices.iter().map(|&i| engine.get_line(i)).collect()
    };
    crate::stream::write_lines(&path, &lines)
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

/// `kind` selects the remembered start directory: "log" or "filter".
#[tauri::command]
fn open_file_dialog(state: State<'_, DialogDirs>, kind: String) -> Result<Option<String>, String> {
    let dialog = state
        .apply(rfd::FileDialog::new(), &kind)
        .add_filter("Log Files", &["log", "txt", "tat"]);
    let file = dialog.pick_file();
    if let Some(p) = &file {
        state.remember(&kind, p);
    }
    Ok(file.map(|p| p.to_string_lossy().to_string()))
}

/// Pick a folder and return its log-like files (non-recursive, sorted).
#[tauri::command]
fn open_folder_dialog(state: State<'_, DialogDirs>) -> Result<Vec<String>, String> {
    let dialog = state.apply(rfd::FileDialog::new(), "folder");
    let Some(dir) = dialog.pick_folder() else {
        return Ok(Vec::new());
    };
    state.remember("folder", &dir);
    let mut files: Vec<std::path::PathBuf> = std::fs::read_dir(&dir)
        .map_err(|e| e.to_string())?
        .filter_map(|e| e.ok().map(|e| e.path()))
        .filter(|p| {
            p.is_file()
                && p.extension()
                    .and_then(|e| e.to_str())
                    .map(|e| matches!(e.to_ascii_lowercase().as_str(), "log" | "txt" | "tat"))
                    .unwrap_or(false)
        })
        .collect();
    files.sort();
    Ok(files.into_iter().map(|p| p.to_string_lossy().to_string()).collect())
}

#[tauri::command]
fn open_exe_dialog(state: State<'_, DialogDirs>) -> Result<Option<String>, String> {
    let dialog = state.apply(rfd::FileDialog::new(), "exe").add_filter("Executable", &["exe"]);
    let file = dialog.pick_file();
    if let Some(p) = &file {
        state.remember("exe", p);
    }
    Ok(file.map(|p| p.to_string_lossy().to_string()))
}

/// `kind` selects the remembered start directory, e.g. "save_log" / "save_notes" / "filter".
#[tauri::command]
fn save_file_dialog(state: State<'_, DialogDirs>, kind: String, default_name: String, extension: String) -> Result<Option<String>, String> {
    let dialog = state
        .apply(rfd::FileDialog::new(), &kind)
        .set_file_name(&default_name)
        .add_filter("Files", &[&extension]);
    let file = dialog.save_file();
    if let Some(p) = &file {
        state.remember(&kind, p);
    }
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
        .manage(DialogDirs::default())
        .manage(StreamState::new())
        .plugin(tauri_plugin_opener::init())
        .on_window_event(|window, event| {
            // On app exit, stop every live source so a stale elevated DbgView
            // (or remote scheduled task) doesn't survive and keep capturing to
            // a log file a future run would reuse (causing interleaved gaps).
            if let tauri::WindowEvent::Destroyed = event {
                if let Some(stream) = window.app_handle().try_state::<StreamState>() {
                    stream.shutdown();
                }
            }
        })
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
            save_log,
            search_log,
            filter_log,
            open_file_dialog,
            open_folder_dialog,
            open_exe_dialog,
            save_file_dialog,
            read_text_file,
            write_text_file,
            create_temp_log,
            delete_file,
            stream::start_file_tail,
            stream::start_dbgview_local,
            stream::start_dbgview_remote,
            stream::stop_stream,
            stream::clear_stream,
            stream::set_stream_paused,
            stream::set_stream_filters,
            stream::get_stream_lines,
            stream::get_stream_codes,
            stream::get_stream_filtered,
            stream::save_stream
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
