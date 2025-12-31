# LogAnalyzer Flet Migration TODO List

## High-Level Overarching TODOs:

- [x] **Replace Tkinter UI Elements with Flet Equivalents**: Base layout, sidebar, log view, timeline, status bar.
- [x] **Adapt Tkinter Event Bindings to Flet Handlers**: `on_keyboard_event`, `on_scroll`, `on_pan_update`, `on_secondary_tap`.
- [x] **Thread Management**: Using `asyncio.to_thread` for Rust engine and native dialogs.
- [x] **Configuration Management**: `app_config.json` load/save and window geometry persistence.
- [x] **Performance Optimization**: Phase 10 Turbo Mode implemented with Rust Batch Fetch.
- [ ] **Multi-Log Management**: Adapt merging logic for multiple concurrent log files and Merged View.
- [ ] **Notes System**: Reimplement the note-taking infrastructure (storage, markers, export).

---

## Detailed Function/Feature Migration TODOs:

### 1. Helper Functions
- [x] `is_true(value)` / `fix_color` / `hex_to_rgb`: Inlined or implemented.
- [x] `adjust_color_for_theme`: Handled by `toggle_theme` logic and smart color adjustment.
- [x] `bool_to_tat` / `color_to_tat`: Implemented within `Filter.to_tat_xml` for file I/O.

### 2. `Filter` Class
- [x] Basic class with `enabled`, `is_regex`, `is_exclude`, `is_event`.
- [x] Added `hit_count` support.
- [x] `to_tat_xml` method for persistence (.tat).

### 3. `LogFileState` Class
- [x] Basic state in `LogAnalyzerApp`.
- [ ] Full migration of attributes (tags, found timestamps, source mapping for merged view).

### 4. `LogEngine` (Rust)
- [x] Core Rust engine integration.
- [x] High-performance `filter` method.
- [x] `search` method integration.
- [x] **Turbo**: `get_lines_batch` with log level pre-detection.

### 5. `LogAnalyzerApp` Initialization
- [x] **Config Management**: Load/Save `app_config.json`.
- [x] **Window Settings**: Remember size, position, and maximized state.
- [ ] **Application Icon**: Apply `loganalyzer.ico`.
- [x] **UI Theming**: Dark/Light mode toggle with Turbo-safe updates.
- [x] **Rust Engine Setup**: Error handling for missing extension.
- [x] **Filter State**: Real-time filtering and status update.
- [ ] **Multi-Log State**: `loaded_log_files` dictionary and sorting logic.
- [x] **Timeline State**: Layered rendering (Heatmap/Indicator).
- [x] **View State**: Virtual scroll with Phase 10 Flat Pool.

### 6. UI Layout (`build_ui`)
- [x] **Top Menu Bar**: Custom MenuBar implementation.
    - [x] `File`: Open, Recent Files, Exit.
    - [x] `File`: Load/Save Filters (.tat).
    - [x] `View`: Toggle Sidebar (Ctrl+B), Position (Left/Right/Bottom).
    - [x] `View`: Toggle Dark Mode.
    - [x] `View`: Find (Ctrl+F).
    - [ ] `View`: Go to Line (Ctrl+G).
- [x] **Welcome Message**: Initial screen matching loganalyzer.py.
- [ ] **Drag & Drop**: Implement OS-level file drop.
- [x] **Status Bar**: Live status (Showing/Total) with persistent counts.
- [x] **Notification System**: Custom Theme-aware Toast Overlay (replaces SnackBar).
- [x] **Filter System Improvement**:
    - [x] Filter Editor Dialog with Color Grid and Readability Adjustment.
    - [x] Double-click to edit, Secondary tap for context menu.
    - [x] Toggle "Show Filtered Only" mode (Ctrl+H).
    - [x] Compact UI: Tight spacing and reduced button sizes.
    - [x] Drag & Drop Reordering.
- [ ] **Notes View Panel**: Add a toggleable bottom/side panel to list all notes.
- [ ] **Minimap / Search Markers**: Vertical bar next to scrollbar showing match positions.

### 7. Functional Methods
- [x] **Theming**: `toggle_theme` with deep recursion for Sidebar components.
- [x] **File I/O**: `load_file` with Rust engine and Recent Files support.
- [x] **Filter Logic**: `apply_filters` with async Rust call.
- [x] **Navigation**: Turbo scrolling with acceleration and Clamping.
- [x] **Scrollbar**: Custom vertical scrollbar with drag/tap support.
- [x] **Search**: Find Bar with Match Case, Wrap Around, and F2/F3 navigation.
- [ ] **Notes Logic**:
    - [ ] Add/Edit Note dialog ('c' key or context menu).
    - [ ] Note indicators in Log View (background color change).
    - [ ] Export notes to `.note` (JSON) and `.txt`.
    - [ ] Automatic discovery of `.note` files when loading logs.
- [ ] **Multi-Log Merging**:
    - [ ] Interleave multiple logs by timestamp.
    - [ ] Source file identification in Log View.
- [ ] **Help & Docs**:
    - [ ] Keyboard Shortcuts dialog.
    - [x] Documentation HTML viewer.
    - [x] About dialog.
