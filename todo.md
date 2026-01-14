# LogAnalyzer Development Plan (V2.1 Refactoring & Enhancement)

## Phase 1: Architecture & Style Foundation (Current Priority)
- [x] **Establish Theme Manager**:
    - [x] Create `log_analyzer/theme_manager.py`.
    - [x] Centralize color palettes (Light/Dark) definitions.
    - [x] Extract inline QSS from `ui.py` to centralized templates.
    - [x] Refactor `MainWindow.apply_theme` to use `ThemeManager`.
    - [ ] Standardize fonts (Inter for UI, JetBrains Mono/Consolas for Logs).
- [ ] **Decouple NotesManager**:
    - [ ] Remove `main_window` dependency from `NotesManager`.
    - [ ] Implement Signals/Slots for Note updates.

## Phase 2: Visual Polishing
- [ ] **Palette Refinement**:
    - [ ] Implement layered Dark Mode (avoiding pure black #000000).
    - [ ] Define semantic Accent Colors (e.g., VS Code Blue #007ACC).
- [ ] **UI Component Enhancements**:
    - [ ] **Status Bar**: Convert to interactive sections (Line/Col, Encoding, Engine Status).
    - [ ] **Micro-interactions**: Add Hover/Pressed states to buttons.
    - [ ] **Animations**: Smooth transitions for Toast and Sidebar.

## Phase 3: Core Architecture Refactoring
- [ ] **Split MainWindow (God Class)**:
    - [ ] Extract `LogController` (File loading, Search, Engine interaction).
    - [ ] Extract `FilterController` (Filter logic independent of UI).
    - [ ] Extract `SearchController` (History, Navigation logic).

## Phase 4: New Features
- [ ] **Live Monitoring (Tail -f)**:
    - [ ] Update Rust engine to support partial reads/updates.
    - [ ] Add FileWatcher in Python.
- [ ] **Multi-Tab Workspace**:
    - [ ] Refactor central view into a `LogWorkspace` widget.
    - [ ] Implement `QTabWidget` container.
- [ ] **Timeline View**:
    - [ ] Create histogram visualization for log density/errors.
