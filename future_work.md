# LogAnalyzer Future Work

These features and refactoring tasks are deferred for future development cycles.

## Architecture Refactoring
- [ ] **Extract UI Components**:
    - [ ] Extract `LogWorkspace` (List View container).
    - [ ] Extract `SidebarPanels` (Log List, Filter Dock) to reduce `ui.py` size.

## New Features
- [ ] **Live Monitoring (Tail -f)**:
    - [ ] Update Rust engine to support partial reads/updates.
    - [ ] Add FileWatcher in Python.
- [ ] **Multi-Tab Workspace**:
    - [ ] Refactor central view into a `LogWorkspace` widget.
    - [ ] Implement `QTabWidget` container.
- [ ] **Timeline View**:
    - [ ] Create histogram visualization for log density/errors.
