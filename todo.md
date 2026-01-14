# LogAnalyzer Development Plan (V2.1 Refactoring & Enhancement)

## Phase 1: Architecture & Style Foundation (Completed)
- [x] **Establish Theme Manager**:
    - [x] Create `log_analyzer/theme_manager.py`.
    - [x] Centralize color palettes (Light/Dark) definitions.
    - [x] Extract inline QSS from `ui.py` to centralized templates.
    - [x] Refactor `MainWindow.apply_theme` to use `ThemeManager`.
    - [x] Standardize fonts (Inter SemiBold for UI, Consolas for Logs).
- [x] **Decouple NotesManager**:
    - [x] Remove `main_window` dependency from `NotesManager`.
    - [x] Implement Signals/Slots for Note updates.

## Phase 2: Visual Polishing (Completed)
- [x] **Palette Refinement**:
    - [x] Implement layered Dark Mode (L-frame with #181818, Sidebar #252526).
    - [x] Define semantic Accent Colors (VS Code Blue #007ACC).
- [x] **UI Component Enhancements**:
    - [x] **Status Bar**: Convert to interactive sections (Ln X, Count, Encoding).
    - [x] **Micro-interactions**: Add Hover/Pressed states to all buttons.
    - [x] **Animations**: Smooth Quintic transitions for Toast notifications.

## Phase 3: Core Architecture Refactoring (In Progress)
- [x] **Split MainWindow (God Class)**:
    - [x] Extract `LogController` (File management, Core Search logic).
    - [x] Extract `FilterController` (Filter management, Engine interaction, Caching).
    - [x] Extract `SearchController` (History, UI Navigation state).
    - [ ] Extract `UI Components` (LogWorkspace, SidebarPanels) to reduce `ui.py` size.

## Phase 4: New Features (Upcoming)
- [ ] **Live Monitoring (Tail -f)**:
    - [ ] Update Rust engine to support partial reads/updates.
    - [ ] Add FileWatcher in Python.
- [ ] **Multi-Tab Workspace**:
    - [ ] Refactor central view into a `LogWorkspace` widget.
    - [ ] Implement `QTabWidget` container.
- [ ] **Timeline View**:
    - [ ] Create histogram visualization for log density/errors.