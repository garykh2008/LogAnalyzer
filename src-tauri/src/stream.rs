// Live log streaming engine.
//
// Unlike the static `LogEngine` (immutable snapshot of a memory-mapped file), a
// live source grows over time. All capture sources (local/remote DbgView, WPP,
// a generic growing file, ...) converge onto the same abstraction: a stream of
// text lines fed into a `LiveEngine`. This module implements that engine plus a
// generic file-tail producer (Milestone 1).

use std::collections::{HashMap, VecDeque};
use std::fs::File;
use std::io::{ErrorKind, Read, Seek, SeekFrom};
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::{Arc, Mutex, OnceLock, RwLock};
use std::thread::JoinHandle;
use std::time::Duration;

use regex::Regex;
use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter};

use crate::engine::FilterItem;
use crate::remote::{self, SshConfig};

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
    /// Whether any filter is a highlight (non-exclude) / an exclude filter.
    has_highlight: bool,
    has_exclude: bool,
    /// Current view mode (mirrors the frontend "show filtered only" toggle).
    show_filtered_only: bool,
    /// Absolute indices of the lines visible in the current mode, ascending.
    /// Only maintained when a display list is actually needed (see tracking_needed).
    filtered_abs: VecDeque<usize>,
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
            has_highlight: false,
            has_exclude: false,
            show_filtered_only: false,
            filtered_abs: VecDeque::new(),
        }
    }

    /// Whether a display index list is needed at all. Full view with no exclude
    /// filters is just identity (every line shown), so no list is tracked.
    fn tracking_needed(&self) -> bool {
        self.show_filtered_only || self.has_exclude
    }

    /// Is a line visible in the current mode?
    ///  - filtered view: matched a highlight (code>=2), or — with no highlight
    ///    filters — simply not excluded (code 0);
    ///  - full view: anything not excluded (code != 1).
    fn is_visible(&self, code: u8) -> bool {
        if self.show_filtered_only {
            code >= 2 || (code == 0 && !self.has_highlight)
        } else {
            code != 1
        }
    }

    /// Append a batch and return (newly matched absolute indices, count of
    /// matched indices trimmed off the front by ring-buffer eviction).
    fn append(&mut self, batch: Vec<String>) -> (Vec<usize>, usize) {
        let mut added: Vec<usize> = Vec::new();
        let mut trimmed = 0usize;
        for line in batch {
            let abs = self.total;
            let code = classify_line(&line, &self.filters);
            self.lines.push_back(line);
            self.codes.push_back(code);
            self.total += 1;
            if self.tracking_needed() && self.is_visible(code) {
                self.filtered_abs.push_back(abs);
                added.push(abs);
            }
            if self.lines.len() > self.cap {
                self.lines.pop_front();
                self.codes.pop_front();
                self.first_abs += 1;
                self.dropped += 1;
                while let Some(&front) = self.filtered_abs.front() {
                    if front < self.first_abs {
                        self.filtered_abs.pop_front();
                        trimmed += 1;
                    } else {
                        break;
                    }
                }
            }
        }
        (added, trimmed)
    }

    fn clear(&mut self) {
        self.lines.clear();
        self.codes.clear();
        self.filtered_abs.clear();
        self.first_abs = 0;
        self.total = 0;
        self.dropped = 0;
    }

    fn set_filters(&mut self, compiled: Vec<CompiledFilter>, show_filtered_only: bool) {
        self.has_highlight = compiled.iter().any(|f| !f.is_exclude);
        self.has_exclude = compiled.iter().any(|f| f.is_exclude);
        self.show_filtered_only = show_filtered_only;
        self.filters = compiled;
        // Reclassify the whole buffer and rebuild the display index list.
        self.filtered_abs.clear();
        let track = self.tracking_needed();
        for i in 0..self.lines.len() {
            let code = classify_line(&self.lines[i], &self.filters);
            self.codes[i] = code;
            if track && self.is_visible(code) {
                self.filtered_abs.push_back(self.first_abs + i);
            }
        }
    }

    fn filtered_snapshot(&self) -> Vec<usize> {
        self.filtered_abs.iter().copied().collect()
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

    fn make_delta(&self, source_id: &str, filtered_added: Vec<usize>, filtered_trimmed: usize) -> StreamDelta {
        StreamDelta {
            source_id: source_id.to_string(),
            total: self.total,
            first_abs: self.first_abs,
            buffer_len: self.lines.len(),
            dropped: self.dropped,
            filtered_added,
            filtered_trimmed,
        }
    }
}

/// Delta emitted to the frontend on each batch. The frontend fetches line
/// text/codes for its visible window lazily via commands; `filtered_added` /
/// `filtered_trimmed` let it maintain the filtered-view index list incrementally.
#[derive(Serialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct StreamDelta {
    pub source_id: String,
    pub total: usize,
    pub first_abs: usize,
    pub buffer_len: usize,
    pub dropped: usize,
    pub filtered_added: Vec<usize>,
    pub filtered_trimmed: usize,
}

/// A running live source: its engine plus a stop flag and producer thread.
pub struct LiveSource {
    pub engine: Arc<Mutex<LiveEngine>>,
    stop: Arc<AtomicBool>,
    handle: Option<JoinHandle<()>>,
    /// For DbgView sources: writing this file signals the elevated watcher to
    /// terminate DbgView and clean up (see `start_dbgview_local`).
    stop_file: Option<PathBuf>,
}

impl LiveSource {
    fn stop(&mut self) {
        // Signal the elevated watcher (if any) before stopping the tail thread.
        if let Some(sf) = &self.stop_file {
            let _ = std::fs::write(sf, b"stop");
        }
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
                                    let (added, trimmed) = eng.append(batch);
                                    eng.make_delta(&source_id, added, trimmed)
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
            stop_file: None,
        },
    );
    Ok(source_id)
}

/// Build the elevated PowerShell watcher: it accepts the EULA, kills any stale
/// DbgView, launches DbgView with kernel capture logging to `log`, then waits
/// for `stop` to appear (written by the app) before terminating DbgView.
#[cfg(target_os = "windows")]
fn build_watcher_script(dbgview: &str, log: &Path, stop: &Path) -> String {
    let esc = |s: &str| s.replace('\'', "''");
    format!(
        "$ErrorActionPreference='SilentlyContinue'\n\
         reg add \"HKCU\\Software\\Sysinternals\\DebugView\" /v EulaAccepted /t REG_DWORD /d 1 /f | Out-Null\n\
         Get-Process Dbgview* | Stop-Process -Force\n\
         Start-Process -FilePath '{dbg}' -ArgumentList '/t','/f','/v','/k','/g','/l','{log}'\n\
         while (-not (Test-Path -LiteralPath '{stop}')) {{ Start-Sleep -Milliseconds 300 }}\n\
         Get-Process Dbgview* | Stop-Process -Force\n\
         Remove-Item -LiteralPath '{stop}' -Force\n",
        dbg = esc(dbgview),
        log = esc(&log.to_string_lossy()),
        stop = esc(&stop.to_string_lossy()),
    )
}

/// Launch the watcher script elevated (single UAC prompt) via a non-elevated
/// PowerShell that calls `Start-Process -Verb RunAs`.
#[cfg(target_os = "windows")]
fn launch_elevated_watcher(ps1: &Path) -> Result<(), String> {
    use std::os::windows::process::CommandExt;
    const CREATE_NO_WINDOW: u32 = 0x0800_0000;

    let ps1s = ps1.to_string_lossy().replace('\'', "''");
    let inner = format!(
        "@('-NoProfile','-ExecutionPolicy','Bypass','-WindowStyle','Hidden','-File','{}')",
        ps1s
    );
    let outer = format!(
        "Start-Process -Verb RunAs -WindowStyle Hidden -FilePath 'powershell' -ArgumentList {}",
        inner
    );

    let status = std::process::Command::new("powershell")
        .args(["-NoProfile", "-WindowStyle", "Hidden", "-Command", &outer])
        .creation_flags(CREATE_NO_WINDOW)
        .status()
        .map_err(|e| e.to_string())?;

    if !status.success() {
        return Err("Failed to launch elevated DbgView (UAC declined or blocked).".to_string());
    }
    Ok(())
}

fn strip_ansi(s: &str) -> String {
    static ANSI_RE: OnceLock<Regex> = OnceLock::new();
    let re = ANSI_RE.get_or_init(|| Regex::new(r"\x1b\[[0-9;?]*[ -/]*[@-~]").unwrap());
    re.replace_all(s, "").into_owned()
}

fn ps_escape(s: &str) -> String {
    s.replace('\'', "''")
}

/// Config for remote kernel capture over SSH (DbgView on a target machine).
#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct RemoteDbgConfig {
    pub host: String,
    pub port: Option<u16>,
    pub user: String,
    pub password: String,
    pub dbgview_path: String,
}

/// Producer thread for a remote DbgView source: SSH to the target, run DbgView
/// elevated (scheduled task, RunLevel Highest) logging to a temp file, then tail
/// that file over SSH (`Get-Content -Wait`) and feed the engine. Cleans up on stop.
fn spawn_ssh_dbgview(
    app: AppHandle,
    source_id: String,
    cfg: SshConfig,
    dbgview_path: String,
    engine: Arc<Mutex<LiveEngine>>,
    stop: Arc<AtomicBool>,
) -> JoinHandle<()> {
    std::thread::spawn(move || {
        let sess = match remote::connect(&cfg) {
            Ok(s) => s,
            Err(e) => {
                eprintln!("Remote DbgView connect failed: {}", e);
                return;
            }
        };

        let safe = source_id.replace('-', "_");
        let log = format!("C:\\Windows\\Temp\\loganalyzer_{}.log", safe);
        let task = format!("LogAnalyzer_{}", safe);

        let setup = format!(
            "$ErrorActionPreference='SilentlyContinue'\n\
             reg add \"HKCU\\Software\\Sysinternals\\DebugView\" /v EulaAccepted /t REG_DWORD /d 1 /f | Out-Null\n\
             Get-Process Dbgview* | Stop-Process -Force\n\
             Remove-Item -LiteralPath '{log}' -Force\n\
             New-Item -ItemType File -Path '{log}' -Force | Out-Null\n\
             Unregister-ScheduledTask -TaskName '{task}' -Confirm:$false\n\
             $a = New-ScheduledTaskAction -Execute '{dbg}' -Argument '/t /f /v /k /g /l \"{logq}\"'\n\
             $p = New-ScheduledTaskPrincipal -UserId '{user}' -RunLevel Highest -LogonType Password\n\
             $t = New-ScheduledTask -Action $a -Principal $p\n\
             Register-ScheduledTask -TaskName '{task}' -InputObject $t -User '{user}' -Password '{pass}' -Force | Out-Null\n\
             Start-ScheduledTask -TaskName '{task}'\n",
            log = ps_escape(&log),
            logq = log,
            task = ps_escape(&task),
            dbg = ps_escape(&dbgview_path),
            user = ps_escape(&cfg.user),
            pass = ps_escape(&cfg.password),
        );
        if let Err(e) = remote::run_ps(&sess, &setup) {
            eprintln!("Remote DbgView setup failed: {}", e);
        }

        // Give the scheduled task a moment to launch DbgView.
        std::thread::sleep(Duration::from_secs(2));

        let stream_script = format!("Get-Content -LiteralPath '{}' -Wait -Tail 0", ps_escape(&log));
        let mut ch = match sess.channel_session() {
            Ok(c) => c,
            Err(e) => {
                eprintln!("Remote stream channel failed: {}", e);
                return;
            }
        };
        if ch.exec(&remote::ps_command(&stream_script)).is_err() {
            return;
        }

        sess.set_blocking(false);
        let mut carry = String::new();
        let mut buf = [0u8; 8192];

        while !stop.load(Ordering::Relaxed) {
            match ch.read(&mut buf) {
                Ok(0) => {
                    if ch.eof() {
                        break;
                    }
                    std::thread::sleep(Duration::from_millis(50));
                }
                Ok(n) => {
                    carry.push_str(&String::from_utf8_lossy(&buf[..n]));
                    let mut parts: Vec<&str> = carry.split('\n').collect();
                    let last = parts.pop().unwrap_or("").to_string();
                    let batch: Vec<String> = parts
                        .into_iter()
                        .map(|p| strip_ansi(p.trim_end_matches('\r')))
                        .collect();
                    carry = last;

                    if !batch.is_empty() {
                        let delta = {
                            let mut eng = match engine.lock() {
                                Ok(e) => e,
                                Err(_) => break,
                            };
                            let (added, trimmed) = eng.append(batch);
                            eng.make_delta(&source_id, added, trimmed)
                        };
                        let _ = app.emit("stream-appended", delta);
                    }
                }
                Err(ref e) if e.kind() == ErrorKind::WouldBlock => {
                    std::thread::sleep(Duration::from_millis(50));
                }
                Err(_) => break,
            }
        }

        // Cleanup: stop DbgView and remove the task/log on the target.
        sess.set_blocking(true);
        let cleanup = format!(
            "$ErrorActionPreference='SilentlyContinue'\n\
             Get-Process Dbgview* | Stop-Process -Force\n\
             Unregister-ScheduledTask -TaskName '{task}' -Confirm:$false\n\
             Remove-Item -LiteralPath '{log}' -Force\n",
            task = ps_escape(&task),
            log = ps_escape(&log),
        );
        let _ = remote::run_ps(&sess, &cleanup);
    })
}

/// Start remote kernel-mode capture over SSH.
#[tauri::command]
pub fn start_dbgview_remote(
    app: AppHandle,
    state: tauri::State<'_, StreamState>,
    config: RemoteDbgConfig,
) -> Result<String, String> {
    let cfg = SshConfig {
        host: config.host,
        port: config.port.unwrap_or(22),
        user: config.user,
        password: config.password,
    };

    // Validate connectivity/credentials up front so the UI gets an error.
    let test = remote::connect(&cfg)?;
    drop(test);

    let source_id = state.next_id();
    let engine = Arc::new(Mutex::new(LiveEngine::new(RING_CAP)));
    let stop = Arc::new(AtomicBool::new(false));
    let handle = spawn_ssh_dbgview(
        app,
        source_id.clone(),
        cfg,
        config.dbgview_path,
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
            stop_file: None,
        },
    );
    Ok(source_id)
}

/// Start local kernel-mode capture with a user-provided DbgView.exe.
#[tauri::command]
pub fn start_dbgview_local(
    app: AppHandle,
    state: tauri::State<'_, StreamState>,
    dbgview_path: String,
) -> Result<String, String> {
    #[cfg(not(target_os = "windows"))]
    {
        let _ = (app, state, dbgview_path);
        Err("DbgView capture is only supported on Windows.".to_string())
    }

    #[cfg(target_os = "windows")]
    {
        if !Path::new(&dbgview_path).exists() {
            return Err(format!("DbgView.exe not found: {}", dbgview_path));
        }

        let source_id = state.next_id();
        let tmp = std::env::temp_dir();
        let log = tmp.join(format!("loganalyzer_dbgview_{}.log", source_id));
        let stop = tmp.join(format!("loganalyzer_dbgview_{}.stop", source_id));
        let ps1 = tmp.join(format!("loganalyzer_dbgview_{}.ps1", source_id));

        // Start from a clean slate; create the log so the tailer can open it.
        let _ = std::fs::remove_file(&log);
        let _ = std::fs::remove_file(&stop);
        std::fs::write(&log, b"").map_err(|e| e.to_string())?;

        std::fs::write(&ps1, build_watcher_script(&dbgview_path, &log, &stop))
            .map_err(|e| e.to_string())?;

        launch_elevated_watcher(&ps1)?;

        let engine = Arc::new(Mutex::new(LiveEngine::new(RING_CAP)));
        let stop_flag = Arc::new(AtomicBool::new(false));
        let handle = spawn_file_tail(
            app,
            source_id.clone(),
            log.to_string_lossy().to_string(),
            Arc::clone(&engine),
            Arc::clone(&stop_flag),
        );

        let mut sources = state.sources.write().map_err(|e| e.to_string())?;
        sources.insert(
            source_id.clone(),
            LiveSource {
                engine,
                stop: stop_flag,
                handle: Some(handle),
                stop_file: Some(stop),
            },
        );
        Ok(source_id)
    }
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
pub fn clear_stream(state: tauri::State<'_, StreamState>, source_id: String) -> Result<(), String> {
    state.with_engine(&source_id, |eng| eng.clear())
}

#[tauri::command]
pub fn set_stream_filters(
    state: tauri::State<'_, StreamState>,
    source_id: String,
    filters: Vec<FilterItem>,
    show_filtered_only: bool,
) -> Result<(), String> {
    let compiled = compile_filters(&filters)?;
    state.with_engine(&source_id, move |eng| eng.set_filters(compiled, show_filtered_only))
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
pub fn get_stream_filtered(
    state: tauri::State<'_, StreamState>,
    source_id: String,
) -> Result<Vec<usize>, String> {
    state.with_engine(&source_id, |eng| eng.filtered_snapshot())
}

#[tauri::command]
pub fn get_stream_codes(
    state: tauri::State<'_, StreamState>,
    source_id: String,
    indices: Vec<usize>,
) -> Result<Vec<u8>, String> {
    state.with_engine(&source_id, |eng| indices.iter().map(|&i| eng.code_at(i)).collect())
}
