// Live log streaming engine.
//
// Unlike the static `LogEngine` (immutable snapshot of a memory-mapped file), a
// live source grows over time. All capture sources (local/remote DbgView, WPP,
// a generic growing file, ...) converge onto the same abstraction: a stream of
// text lines fed into a `LiveEngine`. This module implements that engine plus a
// generic file-tail producer (Milestone 1).

use std::collections::{HashMap, VecDeque};
use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex, RwLock};
use std::thread::JoinHandle;

use regex::Regex;
use serde::Serialize;
use tauri::{AppHandle, Emitter};

use crate::engine::FilterItem;

/// Max lines retained per live source. Bounds memory under continuous
/// high-volume kernel logging; older lines are dropped from the front.
const RING_CAP: usize = 500_000;

/// Poll interval for the file-tail producer.
const POLL_MS: u64 = 80;

/// A filter compiled once for fast per-line classification. Mirrors the
/// classification contract in `engine.rs::filter` so tag codes line up with the
/// frontend palette (exclude match => 1; first highlight match => 2 + index).
struct CompiledFilter {
    text: String,
    re: Option<Regex>,
    is_regex: bool,
    is_exclude: bool,
}

fn compile_filters(filters: &[FilterItem]) -> Result<Vec<CompiledFilter>, String> {
    let mut errors: Vec<String> = Vec::new();
    let compiled: Vec<CompiledFilter> = filters
        .iter()
        .map(|f| {
            let re = if f.is_regex {
                match Regex::new(&f.text) {
                    Ok(r) => Some(r),
                    Err(e) => {
                        errors.push(format!("Filter '{}': {}", f.text, e));
                        None
                    }
                }
            } else {
                None
            };
            CompiledFilter {
                text: f.text.clone(),
                re,
                is_regex: f.is_regex,
                is_exclude: f.is_exclude,
            }
        })
        .collect();

    if !errors.is_empty() {
        return Err(format!("Invalid regex patterns:\n{}", errors.join("\n")));
    }
    Ok(compiled)
}

fn classify_line(line: &str, filters: &[CompiledFilter]) -> u8 {
    // Exclude pass first (matches engine.rs): any exclude hit => code 1.
    for f in filters.iter() {
        if !f.is_exclude {
            continue;
        }
        let matched = if f.is_regex {
            f.re.as_ref().map_or(false, |r| r.is_match(line))
        } else {
            line.contains(&f.text)
        };
        if matched {
            return 1;
        }
    }
    // Highlight pass: first non-exclude match => 2 + its index.
    for (i, f) in filters.iter().enumerate() {
        if f.is_exclude {
            continue;
        }
        let matched = if f.is_regex {
            f.re.as_ref().map_or(false, |r| r.is_match(line))
        } else {
            line.contains(&f.text)
        };
        if matched {
            return (2 + i) as u8;
        }
    }
    0
}

/// Ring buffer of live log lines with absolute line numbering. Absolute indices
/// stay stable across front-eviction so selections/notes keyed by absolute
/// index don't shift (evicted lines simply become unreachable).
pub struct LiveEngine {
    lines: VecDeque<String>,
    codes: VecDeque<u8>,
    /// Absolute index of the front element in the ring buffer.
    first_abs: usize,
    /// Total lines ever appended (== first_abs + lines.len()).
    total: usize,
    cap: usize,
    /// Total lines dropped from the front since the source started.
    dropped: usize,
    filters: Vec<CompiledFilter>,
}

impl LiveEngine {
    fn new(cap: usize) -> Self {
        LiveEngine {
            lines: VecDeque::new(),
            codes: VecDeque::new(),
            first_abs: 0,
            total: 0,
            cap,
            dropped: 0,
            filters: Vec::new(),
        }
    }

    fn append(&mut self, batch: Vec<String>) {
        for line in batch {
            let code = classify_line(&line, &self.filters);
            self.lines.push_back(line);
            self.codes.push_back(code);
            self.total += 1;
            if self.lines.len() > self.cap {
                self.lines.pop_front();
                self.codes.pop_front();
                self.first_abs += 1;
                self.dropped += 1;
            }
        }
    }

    fn set_filters(&mut self, compiled: Vec<CompiledFilter>) {
        self.filters = compiled;
        // Reclassify the current buffer (bounded by cap, so one-shot is fine).
        for i in 0..self.lines.len() {
            self.codes[i] = classify_line(&self.lines[i], &self.filters);
        }
    }

    fn line_at(&self, abs: usize) -> String {
        if abs >= self.first_abs && abs < self.first_abs + self.lines.len() {
            self.lines[abs - self.first_abs].clone()
        } else {
            String::new()
        }
    }

    fn code_at(&self, abs: usize) -> u8 {
        if abs >= self.first_abs && abs < self.first_abs + self.lines.len() {
            self.codes[abs - self.first_abs]
        } else {
            0
        }
    }

    fn snapshot(&self, source_id: &str) -> StreamDelta {
        StreamDelta {
            source_id: source_id.to_string(),
            total: self.total,
            first_abs: self.first_abs,
            buffer_len: self.lines.len(),
            dropped: self.dropped,
        }
    }
}

/// Delta emitted to the frontend on each batch (and on demand). The frontend
/// fetches line text/codes for its visible window lazily via commands.
#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct StreamDelta {
    pub source_id: String,
    pub total: usize,
    pub first_abs: usize,
    pub buffer_len: usize,
    pub dropped: usize,
}

/// A running live source: its engine plus a stop flag and producer thread.
pub struct LiveSource {
    pub engine: Arc<Mutex<LiveEngine>>,
    stop: Arc<AtomicBool>,
    handle: Option<JoinHandle<()>>,
}

impl LiveSource {
    fn stop(&mut self) {
        self.stop.store(true, Ordering::Relaxed);
        if let Some(h) = self.handle.take() {
            let _ = h.join();
        }
    }
}

/// Registry of live sources, held in Tauri's managed state.
pub struct StreamState {
    sources: RwLock<HashMap<String, LiveSource>>,
    seq: AtomicU64,
}

impl StreamState {
    pub fn new() -> Self {
        StreamState {
            sources: RwLock::new(HashMap::new()),
            seq: AtomicU64::new(0),
        }
    }

    fn next_id(&self) -> String {
        let n = self.seq.fetch_add(1, Ordering::Relaxed);
        format!("stream-{}", n)
    }

    fn with_engine<T>(&self, source_id: &str, f: impl FnOnce(&mut LiveEngine) -> T) -> Result<T, String> {
        let sources = self.sources.read().map_err(|e| e.to_string())?;
        let src = sources.get(source_id).ok_or_else(|| "Stream not found".to_string())?;
        let mut eng = src.engine.lock().map_err(|e| e.to_string())?;
        Ok(f(&mut eng))
    }
}

/// Spawn the generic file-tail producer: poll the file, read newly appended
/// bytes, split into lines, append to the engine, and emit a delta per batch.
fn spawn_file_tail(
    app: AppHandle,
    source_id: String,
    path: String,
    engine: Arc<Mutex<LiveEngine>>,
    stop: Arc<AtomicBool>,
) -> JoinHandle<()> {
    std::thread::spawn(move || {
        let mut offset: u64 = 0;
        let mut carry = String::new();

        while !stop.load(Ordering::Relaxed) {
            if let Ok(mut f) = File::open(&path) {
                let len = f.metadata().map(|m| m.len()).unwrap_or(0);

                // File shrank (truncated/rotated) -> restart from the top.
                if len < offset {
                    offset = 0;
                    carry.clear();
                }

                if len > offset {
                    if f.seek(SeekFrom::Start(offset)).is_ok() {
                        let to_read = (len - offset) as usize;
                        let mut buf = vec![0u8; to_read];
                        if let Ok(n) = f.read(&mut buf) {
                            buf.truncate(n);
                            offset += n as u64;

                            // NOTE (M1): UTF-8 lossy decode. Encoding detection
                            // (DbgView output can be ANSI/OEM) comes in a later pass.
                            carry.push_str(&String::from_utf8_lossy(&buf));

                            // Split complete lines; keep the trailing partial line.
                            let mut parts: Vec<&str> = carry.split('\n').collect();
                            let last = parts.pop().unwrap_or("").to_string();
                            let batch: Vec<String> = parts
                                .into_iter()
                                .map(|p| p.trim_end_matches('\r').to_string())
                                .collect();
                            carry = last;

                            if !batch.is_empty() {
                                let delta = {
                                    let mut eng = match engine.lock() {
                                        Ok(e) => e,
                                        Err(_) => break,
                                    };
                                    eng.append(batch);
                                    eng.snapshot(&source_id)
                                };
                                let _ = app.emit("stream-appended", delta);
                            }
                        }
                    }
                }
            }

            std::thread::sleep(std::time::Duration::from_millis(POLL_MS));
        }
    })
}

// ---- Tauri commands ----

#[tauri::command]
pub fn start_file_tail(
    app: AppHandle,
    state: tauri::State<'_, StreamState>,
    path: String,
) -> Result<String, String> {
    let source_id = state.next_id();
    let engine = Arc::new(Mutex::new(LiveEngine::new(RING_CAP)));
    let stop = Arc::new(AtomicBool::new(false));

    let handle = spawn_file_tail(
        app,
        source_id.clone(),
        path,
        Arc::clone(&engine),
        Arc::clone(&stop),
    );

    let mut sources = state.sources.write().map_err(|e| e.to_string())?;
    sources.insert(
        source_id.clone(),
        LiveSource {
            engine,
            stop,
            handle: Some(handle),
        },
    );
    Ok(source_id)
}

#[tauri::command]
pub fn stop_stream(state: tauri::State<'_, StreamState>, source_id: String) -> Result<(), String> {
    let mut sources = state.sources.write().map_err(|e| e.to_string())?;
    if let Some(mut src) = sources.remove(&source_id) {
        src.stop();
    }
    Ok(())
}

#[tauri::command]
pub fn set_stream_filters(
    state: tauri::State<'_, StreamState>,
    source_id: String,
    filters: Vec<FilterItem>,
) -> Result<(), String> {
    let compiled = compile_filters(&filters)?;
    state.with_engine(&source_id, move |eng| eng.set_filters(compiled))
}

#[tauri::command]
pub fn get_stream_lines(
    state: tauri::State<'_, StreamState>,
    source_id: String,
    indices: Vec<usize>,
) -> Result<Vec<String>, String> {
    state.with_engine(&source_id, |eng| indices.iter().map(|&i| eng.line_at(i)).collect())
}

#[tauri::command]
pub fn get_stream_codes(
    state: tauri::State<'_, StreamState>,
    source_id: String,
    indices: Vec<usize>,
) -> Result<Vec<u8>, String> {
    state.with_engine(&source_id, |eng| indices.iter().map(|&i| eng.code_at(i)).collect())
}
