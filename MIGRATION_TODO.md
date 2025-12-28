# LogAnalyzer Flet Migration TODO List

## High-Level Overarching TODOs:

- [x] **Replace Tkinter UI Elements with Flet Equivalents**: Base layout, sidebar, log view, timeline, status bar.
- [x] **Adapt Tkinter Event Bindings to Flet Handlers**: `on_keyboard_event`, `on_scroll`, `on_pan_update`, `on_secondary_tap`.
- [x] **Thread Management**: Using `asyncio.to_thread` for Rust engine and native dialogs.
- [x] **Configuration Management**: `app_config.json` load/save and window geometry persistence.
- [ ] **Windows-Specific APIs**: Reimplement `ctypes` for advanced window effects if needed (currently using Flet native).
- [ ] **Multi-Log Management**: Adapt merging logic for multiple concurrent log files.
- [x] **Error Handling & User Feedback**: `SnackBar` and status bar messages implemented.

---

## Detailed Function/Feature Migration TODOs:

### 1. Helper Functions
- [ ] `is_true(value)` / `fix_color` / `hex_to_rgb`: Partially implemented or inlined.
- [ ] `bool_to_tat` / `color_to_tat`: Pending (for Filter File I/O).
- [x] `adjust_color_for_theme`: Handled by `toggle_theme` logic.

### 2. `Filter` Class
- [x] Basic class with `enabled`, `is_regex`, `is_exclude`.
- [x] Added `hit_count` support.
- [ ] `to_dict` method for persistence.

### 3. `LogFileState` Class
- [x] Basic state in `LogAnalyzerApp`.
- [ ] Full migration of attributes (tags, found timestamps, etc.).

### 4. `LogEngine` (Rust)
- [x] Core Rust engine integration.
- [x] High-performance `filter` method with Exclude/Regex support.
- [ ] Global `search` method integration.

### 5. `LogAnalyzerApp` Initialization
- [x] **Config Management**: Load/Save `app_config.json`.
- [x] **Window Settings**: Remember size, position, and maximized state.
- [ ] **Application Icon**: Apply custom icon.
- [x] **UI Theming**: Dark/Light mode toggle with consistent UI colors.
- [x] **Rust Engine Setup**: Error handling for missing extension.
- [x] **Filter State**: Real-time filtering and status update.
- [ ] **Multi-Log State**: `loaded_log_files` management.
- [x] **Timeline State**: Drawing and interaction logic.
- [x] **View State**: Virtual scroll with fixed row height (20px).

### 6. UI Layout (`build_ui`)
- [x] **Top Menu Bar**: Custom implementation (File, View) replacing AppBar.
    - [x] `File`: Open, Recent Files, Exit.
    - [ ] `File`: Load/Save Filters (.tat).
    - [x] `View`: Toggle Sidebar, Toggle Dark Mode.
    - [x] `View`: Find (Ctrl+F), Go to Line.
- [ ] **Welcome Message**: Initial screen polish matching loganalyzer.py.
- [ ] **Drag & Drop**: Support loading files by dragging from OS (Experimental).
- [x] **Status Bar**: Live status and line count display.
- [ ] **Filter System Improvement**:
    - [x] Basic Filter List (Enabled, Text, Hits).
    - [x] Filter Editor Dialog: Pattern, Type, Color customization.
    - [x] Double-click to edit filter.
    - [x] Filter Context Menu (Move to top/bottom).
    - [ ] Smart Color Adjustment: Adapt colors for dark/light mode (matching loganalyzer.py).
    - [ ] Import/Export .tat (TextAnalysisTool) files.
    - [ ] Toggle "Show Filtered Only" mode.
- [x] **Sidebar (Filter List)**:
    - [x] Scrollable list of filters.
    - [x] Controls: Checkbox, Text, Regex Toggle, Exclude Toggle, Hit Count, Delete.
- [x] **Log View (Virtual Scroll)**:
    - [x] Pre-allocated rows (200) for performance.
    - [x] Precise height calculation based on 20px rows.
    - [x] Right-click context menu (Copy line).
    - [x] Advanced Row Selection: Single, Multi (Ctrl), and Range (Shift) selection with highlighting.
- [x] **Timeline View**:
    - [x] Heatmap drawing based on filter colors.
    - [x] Viewport indicator (Thumb) following scroll.
    - [x] Click/Drag interaction to navigate log.
- [ ] **Notes View Panel**: Pending implementation.

### 7. Functional Methods
- [x] **Theming**: `toggle_theme` with full UI color sync.
- [x] **File I/O**: `load_file` with Rust engine and Recent Files support.
- [x] **Workaround**: Native Tkinter dialog for FilePicker stability in Flet 1.0 Beta.
- [x] **Filter Logic**: `apply_filters` with async Rust call and UI refresh.
- [x] **Navigation**: Keyboard (Arrows, PgUp/Dn, Home/End) and Mouse Wheel.
- [x] **Scrollbar**: Custom vertical scrollbar with drag/tap support.
- [x] **Search**: `show_find_bar`, `find_next`, `find_previous`.
- [ ] **Notes System**: `add_note`, `remove_note`, `refresh_notes_view`.
- [ ] **Filter Persistence**: Import/Export `.tat` and `.json` files.
- [ ] **Multi-Log**: Build merged view from multiple sources.