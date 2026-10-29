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

    /// Snapshot of the retained lines for saving to disk. A live capture is
    /// always dumped in full: the ring buffer is the only place captured lines
    /// live, so a filtered export would permanently lose the currently hidden
    /// lines (excluded / not matching the current view).
    fn dump(&self) -> Vec<String> {
        self.lines.iter().cloned().collect()
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

/// A running live source: its engine plus a stop flag, pause flag, and
/// producer thread.
pub struct LiveSource {
    pub engine: Arc<Mutex<LiveEngine>>,
    stop: Arc<AtomicBool>,
    /// When set, the producer stops feeding the engine (see
    /// `set_stream_paused`): the ring buffer freezes so nothing is evicted
    /// underneath a paused view.
    paused: Arc<AtomicBool>,
    handle: Option<JoinHandle<()>>,
    /// For DbgView sources: writing this file signals the elevated watcher to
    /// terminate DbgView and clean up (see `start_dbgview_local`).
    stop_file: Option<PathBuf>,
    /// Capture exe for this source, set only for DbgView captures. Used to
    /// pause/resume the capture itself (`--pause` / `--resume`) rather than
    /// just the reading side, so resuming starts from the current moment
    /// instead of replaying everything logged during the pause.
    dbgview_exe: Option<String>,
    /// Local captures: set on resume so the tailer jumps to the current end of
    /// the log file, dropping whatever was written while paused. Without it a
    /// resume would replay the whole paused stretch at once. (Remote captures
    /// clear their carry buffer in the producer instead, since their reads go
    /// through SSH rather than a seekable file handle.)
    resume_seek: Arc<AtomicBool>,
    /// Temp files owned by this source (e.g. the local watch script + log
    /// path). Removed best-effort once the source is stopped.
    cleanup_files: Vec<PathBuf>,
}

impl LiveSource {
    fn stop(&mut self) {
        // Signal the elevated watcher (if any) before stopping the tail thread.
        if let Some(sf) = &self.stop_file {
            if std::fs::write(sf, b"stop").is_ok() {
                // Wait (bounded) for the elevated watcher to kill DbgView and
                // consume the stop file, so a quick stop -> start can't overlap
                // two DbgView instances writing logs (which produces gaps).
                let deadline = std::time::Instant::now() + Duration::from_secs(5);
                while std::time::Instant::now() < deadline && sf.exists() {
                    std::thread::sleep(Duration::from_millis(100));
                }
            }
        }
        self.stop.store(true, Ordering::Relaxed);
        if let Some(h) = self.handle.take() {
            let _ = h.join();
        }
        // Remove our own artifacts now that DbgView is gone and the tail
        // thread is joined (best-effort; the watcher already removed the stop
        // file, log / script may still be on disk).
        for p in self.cleanup_files.drain(..) {
            let _ = std::fs::remove_file(p);
        }
        if let Some(sf) = &self.stop_file {
            let _ = std::fs::remove_file(sf);
        }
    }
}

/// Registry of live sources, held in Tauri's managed state.
pub struct StreamState {
    sources: RwLock<HashMap<String, LiveSource>>,
    seq: AtomicU64,
    /// Boot-stability salt so per-run temp paths / task names never collide
    /// across app launches (a stale elevated DbgView from a previous run can
    /// otherwise keep writing to a file a fresh capture also reuses).
    run_id: String,
}

impl StreamState {
    pub fn new() -> Self {
        use std::time::{SystemTime, UNIX_EPOCH};
        let run_nanos = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default()
            .as_nanos();
        // `run_id` is only used to build per-run unique names, so the
        // sanitized current time is sufficient (trailing digits stay intact).
        let run_id: String = run_nanos.to_string().chars().filter(|c| c.is_ascii_alphanumeric()).collect();
        StreamState {
            sources: RwLock::new(HashMap::new()),
            seq: AtomicU64::new(0),
            run_id,
        }
    }

    fn next_id(&self) -> String {
        let n = self.seq.fetch_add(1, Ordering::Relaxed);
        format!("stream-{}-{}", self.run_id, n)
    }

    /// Stop every live source: write the DbgView stop files, join the producer
    /// threads, and remove temp files. Invoked on app exit so an app restart no
    /// longer leaks an elevated DbgView (or orphaned remote task) that keeps
    /// capturing.
    pub fn shutdown(&self) {
        let mut sources = match self.sources.write() {
            Ok(w) => w,
            Err(_) => return,
        };
        let mut stopped: Vec<LiveSource> = sources.drain().map(|(_, s)| s).collect();
        for src in stopped.iter_mut() {
            src.stop();
        }
    }

    fn with_engine<T>(&self, source_id: &str, f: impl FnOnce(&mut LiveEngine) -> T) -> Result<T, String> {
        let sources = self.sources.read().map_err(|e| e.to_string())?;
        let src = sources.get(source_id).ok_or_else(|| "Stream not found".to_string())?;
        let mut eng = src.engine.lock().map_err(|e| e.to_string())?;
        Ok(f(&mut eng))
    }
}

/// A file-tail producer whose `offset`/`carry` are re-openable, so the
/// producer may be paused (skipping its reads) and resumed without losing or
/// duplicating data.
struct TailPos {
    offset: u64,
    carry: String,
}

/// Spawn the generic file-tail producer: poll the file, read newly appended
/// bytes, split into lines, append to the engine, and emit a delta per batch.
/// While `paused` is set the producer skips reads entirely (the ring buffer
/// freezes). `resume_seek` makes it jump to the current end of the file on
/// resume instead of picking up where it left off, so a paused stretch is
/// dropped rather than replayed — used by DbgView captures, where the user
/// expects resume to mean "from now on".
fn spawn_file_tail(
    app: AppHandle,
    source_id: String,
    path: String,
    engine: Arc<Mutex<LiveEngine>>,
    stop: Arc<AtomicBool>,
    paused: Arc<AtomicBool>,
    resume_seek: Option<Arc<AtomicBool>>,
) -> JoinHandle<()> {
    std::thread::spawn(move || {
        let mut pos = TailPos { offset: 0, carry: String::new() };

        while !stop.load(Ordering::Relaxed) {
            // Paused: keep sleeping until resumed or stopped. The producer must
            // NOT treat "still paused" as a stop signal — otherwise pausing for
            // longer than one sleep window would kill the thread permanently
            // and resume (start) would never capture again.
            while paused.load(Ordering::Relaxed) {
                if stop.load(Ordering::Relaxed) {
                    return;
                }
                std::thread::sleep(Duration::from_millis(POLL_MS / 8));
            }
            // Resumed with the seek flag raised: skip the paused stretch.
            if let Some(flag) = &resume_seek {
                if flag.swap(false, Ordering::Relaxed) {
                    pos.offset = std::fs::metadata(&path).map(|m| m.len()).unwrap_or(pos.offset);
                    pos.carry.clear();
                }
            }
            if let Ok(mut f) = File::open(&path) {
                let len = f.metadata().map(|m| m.len()).unwrap_or(0);

                // File shrank (truncated/rotated) -> restart from the top.
                if len < pos.offset {
                    pos.offset = 0;
                    pos.carry.clear();
                }

                if len > pos.offset {
                    if f.seek(SeekFrom::Start(pos.offset)).is_ok() {
                        let to_read = (len - pos.offset) as usize;
                        let mut buf = vec![0u8; to_read];
                        if let Ok(n) = f.read(&mut buf) {
                            buf.truncate(n);
                            pos.offset += n as u64;

                            // NOTE (M1): UTF-8 lossy decode. Encoding detection
                            // (DbgView output can be ANSI/OEM) comes in a later pass.
                            pos.carry.push_str(&String::from_utf8_lossy(&buf));

                            // Split complete lines; keep the trailing partial line.
                            let mut parts: Vec<&str> = pos.carry.split('\n').collect();
                            let last = parts.pop().unwrap_or("").to_string();
                            let batch: Vec<String> = parts
                                .into_iter()
                                .map(|p| p.trim_end_matches('\r').to_string())
                                .collect();
                            pos.carry = last;

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
    let paused = Arc::new(AtomicBool::new(false));

    let handle = spawn_file_tail(
        app,
        source_id.clone(),
        path,
        Arc::clone(&engine),
        Arc::clone(&stop),
        Arc::clone(&paused),
        None,
    );

    let mut sources = state.sources.write().map_err(|e| e.to_string())?;
    sources.insert(
        source_id.clone(),
        LiveSource {
            engine,
            stop,
            paused,
            handle: Some(handle),
            stop_file: None,
            dbgview_exe: None,
            resume_seek: Arc::new(AtomicBool::new(false)),
            cleanup_files: Vec::new(),
        },
    );
    Ok(source_id)
}

/// Which capture front-end the configured path points at. Sysinternals shipped
/// `DbgViewCli.exe` with DebugView v5.02: same capture engine (kernel via
/// Dbgv.sys, Win32 via the DBWIN buffer), but a real command line — `--log` for
/// the output file, `--stop`/`--status` for runtime control, no GUI window.
#[cfg(target_os = "windows")]
#[derive(Clone, Copy, PartialEq)]
enum DbgViewFlavor {
    /// Classic GUI `Dbgview.exe` (v4.x and earlier 5.x): `/k /l <file>`, killed
    /// by process name when the stop file appears.
    Gui,
    /// `DbgViewCli.exe` (v5.02+): long-option CLI, stops itself on `--stop`.
    Cli,
}

/// Detected from the file name, so one path setting keeps working for both the
/// GUI and CLI builds without adding a mode the user has to understand.
#[cfg(target_os = "windows")]
fn detect_flavor(exe: &str) -> DbgViewFlavor {
    let stem = Path::new(exe)
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("")
        .to_ascii_lowercase();
    if stem.contains("cli") {
        DbgViewFlavor::Cli
    } else {
        DbgViewFlavor::Gui
    }
}

/// The `--stop`/`--status` invocations only reach the running instance's control
/// channel; they do not capture anything, so they need no elevation even when
/// the capturing instance itself holds Highest.
#[cfg(target_os = "windows")]
fn cli_argument_list(flavor: DbgViewFlavor, log: &str) -> Vec<String> {
    match flavor {
        DbgViewFlavor::Cli => vec![
            "--capture".into(),
            "--kernel".into(),
            // Kernel-only: user-mode OutputDebugString is not wanted here, and
            // skipping it keeps us out of the Win32 path entirely.
            "--no-win32".into(),
            // Latest line complete on write, so the tailer never sees a line
            // without its terminating CR.
            "--no-force-cr".into(),
            "--verbose-kernel".into(),
            // Clock time with milliseconds: the format the analyzer's timestamp
            // parsing expects (GUI `/t` equivalent).
            "--clock-ms".into(),
            "--no-banner".into(),
            "--log".into(),
            log.to_string(),
        ],
        // NB: we deliberately do NOT pass `/g` (Capture Global Win32 / session 0).
        // That switch makes DebugView the global `OutputDebugString` reader, which
        // forces every session-0 process (services) to synchronize on the DBWIN
        // protocol and wait for our hidden, file-logging instance to drain each
        // call — throttling user-mode debuggers/services (e.g. socket-based test
        // harnesses) and hanging them. Kernel capture (`/k`) uses the Dbgv.sys
        // driver and is unaffected by it.
        DbgViewFlavor::Gui => vec![
            "/t".into(),
            "/f".into(),
            "/v".into(),
            "/k".into(),
            "/l".into(),
            log.to_string(),
        ],
    }
}

/// Pause/resume helper for a local CLI capture. Returns `None` for the GUI
/// build, which has no runtime control channel: its pause stays "stop reading
/// the log", the only thing a GUI instance allows.
#[cfg(target_os = "windows")]
fn cli_pause_command(dbgview: &str, paused: bool) -> Option<Vec<&'static str>> {
    if detect_flavor(dbgview) != DbgViewFlavor::Cli {
        return None;
    }
    Some(if paused {
        vec!["--pause", "--no-banner"]
    } else {
        vec!["--resume", "--no-banner"]
    })
}

/// Argument string for the remote scheduled task, which takes one quoted
/// command line rather than an array. `log` is emitted verbatim, so the caller
/// must have already escaped it for the surrounding PowerShell string.
#[cfg(target_os = "windows")]
fn remote_argument_line(flavor: DbgViewFlavor, log: &str) -> String {
    match flavor {
        DbgViewFlavor::Cli => format!(
            "--capture --kernel --no-win32 --no-force-cr --verbose-kernel --clock-ms --no-banner --log \"{log}\""
        ),
        DbgViewFlavor::Gui => format!("/t /f /v /k /l \"{log}\""),
    }
}

/// Build the elevated PowerShell watcher: it accepts the EULA, kills any stale
/// DbgView, launches DbgView with kernel capture logging to `log`, then waits
/// for `stop` to appear (written by the app) before terminating DbgView.
#[cfg(target_os = "windows")]
fn build_watcher_script(dbgview: &str, log: &Path, stop: &Path) -> String {
    let esc = |s: &str| s.replace('\'', "''");
    let flavor = detect_flavor(dbgview);
    let args = cli_argument_list(flavor, &log.to_string_lossy())
        .iter()
        .map(|a| format!("'{}'", esc(a)))
        .collect::<Vec<_>>()
        .join(",");

    // The CLI exits on its own `--stop`; the GUI needs a process kill. Either
    // way a sweep follows, since a GUI instance is never asked politely and a
    // stale instance from an aborted run must not survive into the next one.
    // The CLI gets a bounded grace period first: killing it mid-flush would drop
    // the last lines of the log the tailer may still be reading.
    let shutdown = if flavor == DbgViewFlavor::Cli {
        format!(
            "& '{dbg}' --stop --no-banner | Out-Null\n\
             $deadline = (Get-Date).AddSeconds(3)\n\
             while ((Get-Date) -lt $deadline -and (Get-Process 'DbgViewCli' -ErrorAction SilentlyContinue)) {{ Start-Sleep -Milliseconds 100 }}\n\
             Get-Process Dbgview* | Stop-Process -Force\n",
            dbg = esc(dbgview),
        )
    } else {
        "Get-Process Dbgview* | Stop-Process -Force\n".to_string()
    };

    // `-WindowStyle Hidden` on the capture launch: DbgViewCli is a console app,
    // so without it a console window pops up and stays up for the whole
    // capture. The GUI build draws its own window and ignores nothing here.
    let hidden = if flavor == DbgViewFlavor::Cli { "-WindowStyle Hidden " } else { "" };

    format!(
        "$ErrorActionPreference='SilentlyContinue'\n\
         reg add \"HKCU\\Software\\Sysinternals\\DebugView\" /v EulaAccepted /t REG_DWORD /d 1 /f | Out-Null\n\
         Get-Process Dbgview* | Stop-Process -Force\n\
         Start-Process {hidden}-FilePath '{dbg}' -ArgumentList {args}\n\
         while (-not (Test-Path -LiteralPath '{stop}')) {{ Start-Sleep -Milliseconds 300 }}\n\
         {shutdown}\
         Remove-Item -LiteralPath '{stop}' -Force\n",
        hidden = hidden,
        dbg = esc(dbgview),
        args = args,
        shutdown = shutdown,
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

/// Pause/resume a remote capture at the source. Opens its own short-lived SSH
/// session rather than sharing the tailer's, so a pause never has to wait on a
/// blocking `Get-Content -Wait` channel. Returns Ok(false) when the target runs
/// the GUI build, which has no runtime control channel.
fn remote_set_paused(cfg: &SshConfig, dbgview_path: &str, paused: bool) -> Result<bool, String> {
    if detect_flavor(dbgview_path) != DbgViewFlavor::Cli {
        return Ok(false);
    }
    let flag = if paused { "--pause" } else { "--resume" };
    let script = format!("& '{}' {flag} --no-banner", ps_escape(dbgview_path));
    let sess = remote::connect(cfg)?;
    remote::run_ps(&sess, &script)?;
    Ok(true)
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
    paused: Arc<AtomicBool>,
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

        // Remove any scheduled tasks left behind by older/aborted capture
        // sessions (name changed across runs, so stale tasks from before this
        // fix are still named `LogAnalyzer_stream-<n>`), then clear DbgView so
        // the new capture starts from a single instance.
        let sweep = format!(
            "$ErrorActionPreference='SilentlyContinue'\n\
             Get-ScheduledTask -TaskName 'LogAnalyzer_*' -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false\n\
             Get-Process Dbgview* -ErrorAction SilentlyContinue | Stop-Process -Force",
        );
        let _ = remote::run_ps(&sess, &sweep);

        // The scheduled task runs whichever build the target path points at, so
        // its argument line is chosen by the same filename sniff used locally.
        let flavor = detect_flavor(&dbgview_path);
        let setup = format!(
            "$ErrorActionPreference='SilentlyContinue'\n\
             reg add \"HKCU\\Software\\Sysinternals\\DebugView\" /v EulaAccepted /t REG_DWORD /d 1 /f | Out-Null\n\
             Remove-Item -LiteralPath '{log}' -Force\n\
             New-Item -ItemType File -Path '{log}' -Force | Out-Null\n\
             Unregister-ScheduledTask -TaskName '{task}' -Confirm:$false\n\
             $a = New-ScheduledTaskAction -Execute '{dbg}' -Argument '{args}'\n\
             $p = New-ScheduledTaskPrincipal -UserId '{user}' -RunLevel Highest -LogonType Password\n\
             $t = New-ScheduledTask -Action $a -Principal $p\n\
             Register-ScheduledTask -TaskName '{task}' -InputObject $t -User '{user}' -Password '{pass}' -Force | Out-Null\n\
             Start-ScheduledTask -TaskName '{task}'\n",
            log = ps_escape(&log),
            args = ps_escape(&remote_argument_line(flavor, &log)),
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

        // Pause is applied at the source: this thread owns the SSH session and
        // is the only one allowed to touch it, so the frontend's request is
        // handed over here. `announced` tracks the last state pushed to the
        // target, so the control command is issued once per transition.
        let mut announced: Option<bool> = None;
        // Set when a paused capture resumes: the first loop iteration past the
        // pause throws away everything buffered during it (see below).
        let mut drain_until_quiet = false;

        while !stop.load(Ordering::Relaxed) {
            let want_paused = paused.load(Ordering::Relaxed);

            // Resuming means "from now on": everything the target wrote while we
            // were paused is still queued in the SSH channel, so throw it away
            // rather than replaying the paused stretch into the ring. Drain
            // BEFORE sending --resume, so the first lines of the resumed capture
            // are not discarded along with the backlog.
            if !want_paused && drain_until_quiet {
                drain_until_quiet = false;
                carry.clear();
                loop {
                    match ch.read(&mut buf) {
                        // Ok(0) is EOF on a non-blocking channel; no data is
                        // reported as WouldBlock below.
                        Ok(0) => break,
                        Ok(_) => continue,
                        Err(ref e) if e.kind() == ErrorKind::WouldBlock => break,
                        Err(_) => break,
                    }
                }
            }

            if announced != Some(want_paused) {
                let sent = match remote_set_paused(&cfg, &dbgview_path, want_paused) {
                    Ok(supported) => supported,
                    Err(e) => {
                        // Report but keep tailing: a failed pause must not kill
                        // a capture that is otherwise running fine.
                        eprintln!("Remote pause request failed: {}", e);
                        false
                    }
                };
                if sent {
                    announced = Some(want_paused);
                } else {
                    // GUI target: no control channel, so fall back to the old
                    // behaviour of just not reading.
                    announced = None;
                }
            }

            // While paused, don't drain the SSH stream: leaving the backlog in
            // the channel keeps the ring frozen at the paused view.
            if want_paused {
                drain_until_quiet = true;
                std::thread::sleep(Duration::from_millis(POLL_MS / 8));
                continue;
            }
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

        // Cleanup: stop DbgView and remove the task/log on the target. The CLI
        // flushes its log on `--stop`, so it is asked first; the process sweep
        // afterwards covers the GUI build and any instance that ignored us.
        sess.set_blocking(true);
        let stop_capture = if detect_flavor(&dbgview_path) == DbgViewFlavor::Cli {
            // Bounded grace period so the CLI can flush its log before the sweep.
            format!(
                "& '{dbg}' --stop --no-banner | Out-Null\n\
                 $deadline = (Get-Date).AddSeconds(3)\n\
                 while ((Get-Date) -lt $deadline -and (Get-Process 'DbgViewCli' -ErrorAction SilentlyContinue)) {{ Start-Sleep -Milliseconds 100 }}\n",
                dbg = ps_escape(&dbgview_path),
            )
        } else {
            String::new()
        };
        let cleanup = format!(
            "$ErrorActionPreference='SilentlyContinue'\n\
             {stop_capture}\
             Get-Process Dbgview* | Stop-Process -Force\n\
             Unregister-ScheduledTask -TaskName '{task}' -Confirm:$false\n\
             Remove-Item -LiteralPath '{log}' -Force\n",
            stop_capture = stop_capture,
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
    let paused = Arc::new(AtomicBool::new(false));
    let dbgview_exe = config.dbgview_path.clone();
    let handle = spawn_ssh_dbgview(
        app,
        source_id.clone(),
        cfg,
        config.dbgview_path,
        Arc::clone(&engine),
        Arc::clone(&stop),
        Arc::clone(&paused),
    );

    let mut sources = state.sources.write().map_err(|e| e.to_string())?;
    sources.insert(
        source_id.clone(),
        LiveSource {
            engine,
            stop,
            paused,
            handle: Some(handle),
            stop_file: None,
            // Remote capture pauses at the source over SSH (see
            // `set_stream_paused`), so the log stays empty while paused.
            dbgview_exe: Some(dbgview_exe),
            resume_seek: Arc::new(AtomicBool::new(false)),
            cleanup_files: Vec::new(),
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
        let cleanup_files = vec![log.clone(), ps1.clone()];

        std::fs::write(&ps1, build_watcher_script(&dbgview_path, &log, &stop))
            .map_err(|e| e.to_string())?;

        launch_elevated_watcher(&ps1)?;

        let engine = Arc::new(Mutex::new(LiveEngine::new(RING_CAP)));
        let stop_flag = Arc::new(AtomicBool::new(false));
        let paused = Arc::new(AtomicBool::new(false));
        let resume_seek = Arc::new(AtomicBool::new(false));
        let handle = spawn_file_tail(
            app,
            source_id.clone(),
            log.to_string_lossy().to_string(),
            Arc::clone(&engine),
            Arc::clone(&stop_flag),
            Arc::clone(&paused),
            Some(Arc::clone(&resume_seek)),
        );

        let mut sources = state.sources.write().map_err(|e| e.to_string())?;
        sources.insert(
            source_id.clone(),
            LiveSource {
                engine,
                stop: stop_flag,
                paused,
                handle: Some(handle),
                stop_file: Some(stop),
                dbgview_exe: Some(dbgview_path),
                resume_seek,
                cleanup_files,
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

/// Pause / resume a live source's producer (see `LiveSource::paused`). Pausing
/// is per-source, so only the source currently on screen freezes.
#[tauri::command]
pub fn set_stream_paused(
    state: tauri::State<'_, StreamState>,
    source_id: String,
    paused: bool,
) -> Result<(), String> {
    let sources = state.sources.read().map_err(|e| e.to_string())?;
    let src = sources
        .get(&source_id)
        .ok_or_else(|| "Stream not found".to_string())?;

    // CLI captures can stop capturing outright: `--pause` halts output at the
    // source, so nothing accumulates in the log file and resuming picks up from
    // the current moment. Do this BEFORE flagging the producer, so no lines
    // written between the two are read late.
    // Best-effort: if the CLI's control channel rejects a non-elevated caller
    // the capture simply keeps running, and the resume seek below still gives
    // the user "start from now" — only the wasted disk writes differ.
    #[cfg(target_os = "windows")]
    if let Some(exe) = &src.dbgview_exe {
        if let Some(args) = cli_pause_command(exe, paused) {
            use std::os::windows::process::CommandExt;
            const CREATE_NO_WINDOW: u32 = 0x0800_0000;
            match std::process::Command::new(exe)
                .args(&args)
                .creation_flags(CREATE_NO_WINDOW)
                .status()
            {
                Ok(s) if !s.success() => {
                    eprintln!("DbgViewCli {} returned {:?}", args[0], s.code());
                }
                Err(e) => eprintln!("DbgViewCli {} failed: {}", args[0], e),
                _ => {}
            }
        }
    }

    // Resume skips the paused stretch: flag the tailer to jump to the current
    // end of the file rather than replaying everything written while frozen.
    if !paused {
        src.resume_seek.store(true, Ordering::Relaxed);
    }
    src.paused.store(paused, Ordering::Relaxed);
    Ok(())
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

/// Write log lines to `path`, one per line with a normalized `\n` terminator.
/// Shared by the live (`save_stream`) and static (`save_log`) save paths.
pub fn write_lines(path: &str, lines: &[String]) -> Result<usize, String> {
    use std::io::{BufWriter, Write};
    let file = File::create(path).map_err(|e| e.to_string())?;
    let mut w = BufWriter::new(file);
    for line in lines {
        let trimmed = line.trim_end_matches(['\r', '\n']);
        writeln!(w, "{}", trimmed).map_err(|e| e.to_string())?;
    }
    w.flush().map_err(|e| e.to_string())?;
    Ok(lines.len())
}

/// Save a live source's complete retained buffer to a file. Always writes the
/// whole buffer (capture export must not be filtered by the current view).
/// Returns the line count written.
#[tauri::command]
pub fn save_stream(
    state: tauri::State<'_, StreamState>,
    source_id: String,
    path: String,
) -> Result<usize, String> {
    let lines = state.with_engine(&source_id, |eng| eng.dump())?;
    write_lines(&path, &lines)
}
