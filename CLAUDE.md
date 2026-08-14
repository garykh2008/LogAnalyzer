# LogAnalyzer — AI Onboarding

High-performance diagnostic **log viewer** (Tauri desktop app, Windows-first).
Opens huge log files, filters/highlights by keyword/regex, and streams live logs
(including Windows **kernel** debug output via DebugView). Inspired by
TextAnalysisTool.NET.

## Stack

- **Frontend**: React 19 + TypeScript + Vite + Tailwind v4. State in **Zustand**
  (`src/store.ts`, with `persist` for prefs). Icons: `lucide-react`.
- **Backend**: **Rust** via **Tauri v2** (`src-tauri/`). Log parsing uses `memmap2`,
  `rayon`, `regex`, `encoding_rs`. Remote capture uses `ssh2`.
- IPC: frontend calls Rust `#[tauri::command]`s via `invoke(...)`; Rust pushes
  live updates via `app.emit("stream-appended", ...)` listened to in `App.tsx`.

## Build / run / check

```bash
npm install
npm run tauri dev     # run the desktop app (dev)
npm run build         # tsc + vite build (frontend)
npx tsc --noEmit      # frontend typecheck (fast; do this after FE edits)
cd src-tauri && cargo check   # backend typecheck (do this after Rust edits)
```

Always run `tsc --noEmit` and/or `cargo check` after edits — both are fast. There
are no automated tests; verification is manual in `tauri dev`. GUI/UAC/SSH flows
can't be verified headlessly — ask the user to test those.

## Layout

- `src/App.tsx` — shell: titlebar menus, status bar, all modals (Settings, Search,
  Notes, **Remote connect**), global keyboard shortcuts, Tauri event listeners.
- `src/store.ts` — **single source of truth**. All state + actions. Read this first.
- `src/components/LogViewport.tsx` — virtualized log view (fixed row height, fetches
  only the visible window). Renders both static files and live sources.
- `src/components/SidebarPanels.tsx` — Files / Filters / Notes panels + filter editor modal.
- `src/components/SearchOverlay.tsx` — find overlay.
- `src/utils/color.ts` — `adjustColorForTheme()` (dark-mode contrast adjustment).
- `src-tauri/src/lib.rs` — `AppState`, command registration (`invoke_handler!`), CLI arg handling.
- `src-tauri/src/engine.rs` — `LogEngine`: immutable mmap snapshot of a file; `filter()`, `search()`.
- `src-tauri/src/stream.rs` — `LiveEngine` + streaming (file tail, local/remote DbgView). See below.
- `src-tauri/src/remote.rs` — `ssh2` client (connect, PowerShell `-EncodedCommand` runner).
- `scripts/setup-remote-target.bat` — one-shot target prep for remote capture.

## Core concepts (read before touching viewport/filters)

- **Two source kinds**: *static* files (`load_log`/`get_lines`/`filter_log`, keyed by
  filepath) and *live* streams (`start_file_tail` / `start_dbgview_local` /
  `start_dbgview_remote`, keyed by a synthetic `sourceId` like `stream-3`). `activeFile`
  holds either a filepath or a sourceId; `liveSources[activeFile]` tells them apart.
  **Any command that touches line content must branch on the source kind**: e.g.
  `copySelection` / `saveLog` route to `get_stream_lines` / `save_stream` for live
  sources and `get_lines` / `save_log` for static ones — using the wrong one against a
  sourceId fails with "Log file not loaded".
- **`filteredIndices`** = "the display index list for the current view, or `null` for
  identity (show every line)". The viewport maps display slot → raw/absolute line
  through it. It is set whenever lines are hidden: **Filtered View** (`showFilteredOnly`)
  OR **any enabled exclude filter**.
- **Tag codes & palette**: each line gets a `u8` code — `0` = no match, `1` = excluded,
  `2 + i` = matched the i-th enabled filter. `filterPalette[code]` gives its colors.
  Visibility: filtered view shows `code >= 2` (relaxed to `code == 0` when there are no
  highlight filters); full view shows `code != 1`. **Exclude hides matched lines in BOTH
  modes** (matches real TextAnalysisTool.NET). Static and live share this contract.
- **Live engine** (`stream.rs`): a `VecDeque` **ring buffer** (cap 500k) with **absolute
  line numbers** (`first_abs`), so selections survive front-eviction. A poll-seek tail
  thread (~80ms) reads new bytes, classifies incrementally, and emits a `StreamDelta`
  `{ total, firstAbs, bufferLen, dropped, filteredAdded, filteredTrimmed }`. The frontend
  fetches the visible window via `get_stream_lines` / `get_stream_codes`, and maintains
  its `filteredIndices` incrementally from the delta.
- **Live capture is decoupled**: every source (file tail, local DbgView `/k`, remote
  SSH DbgView) is just a producer of lines into a `LiveEngine`. DbgView runs elevated
  (local: single UAC via a PowerShell watcher + stop-file; remote: a Highest-privilege
  scheduled task over SSH). Live streaming is an **opt-in** feature (`enableLiveStream`).

## Gotchas

- **WebView2 repaint**: reused React DOM nodes may not repaint inline-style-only changes.
  Log rows are keyed `` `${itemIndex}-${code}` `` so a recolor forces a remount. Keep the
  key base on a value that's always unique and non-NaN (`itemIndex`), not `rawIdx`.
- **Absolute vs display indices**: live rows use `firstAbs + slot` (or `filteredIndices`);
  guard against out-of-range `rawIdx` (transient during mode switches → NaN line numbers).
- **Pause** freezes the active live view by stashing deltas in `livePending`; **resume**
  flushes and re-syncs `filteredIndices`. **Clear** wipes the ring buffer and resets the list.
- Secrets: SSH **password is never persisted** (host/user/port/path are).

## Conventions

- Match surrounding style. Commit only when asked; branch off `main` if needed.
- After Rust edits run `cargo check`; after TS edits run `npx tsc --noEmit`.
- Don't commit `.claude/worktrees/*` noise — stage explicit files.
