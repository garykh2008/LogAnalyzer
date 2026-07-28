// Learn more about Tauri commands at https://tauri.app/develop/calling-rust/
mod engine;

use std::collections::HashMap;
use std::sync::Mutex;
use tauri::State;
use crate::engine::{LogEngine, FilterItem};

struct AppState {
    engines: Mutex<HashMap<String, LogEngine>>,
}

#[tauri::command]
fn load_log(state: State<'_, AppState>, filepath: String) -> Result<usize, String> {
    let mut engines = state.engines.lock().map_err(|e| e.to_string())?;
    
    // If already loaded, return line count
    if let Some(engine) = engines.get(&filepath) {
        return Ok(engine.line_count());
    }
    
    let engine = LogEngine::new(&filepath)?;
    let count = engine.line_count();
    engines.insert(filepath, engine);
    Ok(count)
}

#[tauri::command]
fn close_log(state: State<'_, AppState>, filepath: String) -> Result<(), String> {
    let mut engines = state.engines.lock().map_err(|e| e.to_string())?;
    engines.remove(&filepath);
    Ok(())
}

#[tauri::command]
fn get_lines(state: State<'_, AppState>, filepath: String, indices: Vec<usize>) -> Result<Vec<String>, String> {
    let engines = state.engines.lock().map_err(|e| e.to_string())?;
    let engine = engines.get(&filepath).ok_or_else(|| "Log file not loaded".to_string())?;
    
    let lines = indices.iter()
        .map(|&idx| engine.get_line(idx))
        .collect();
    Ok(lines)
}

#[tauri::command]
fn search_log(state: State<'_, AppState>, filepath: String, query: String, is_regex: bool, case_sensitive: bool) -> Result<Vec<usize>, String> {
    let engines = state.engines.lock().map_err(|e| e.to_string())?;
    let engine = engines.get(&filepath).ok_or_else(|| "Log file not loaded".to_string())?;
    
    engine.search(&query, is_regex, case_sensitive)
}

#[tauri::command]
fn filter_log(state: State<'_, AppState>, filepath: String, filters: Vec<FilterItem>) -> Result<(Vec<u8>, Vec<usize>, Vec<usize>, Vec<(String, String, usize)>), String> {
    let engines = state.engines.lock().map_err(|e| e.to_string())?;
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(AppState {
            engines: Mutex::new(HashMap::new()),
        })
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            load_log,
            close_log,
            get_lines,
            search_log,
            filter_log,
            open_file_dialog,
            save_file_dialog,
            read_text_file,
            write_text_file
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
