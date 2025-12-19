# Log Analyzer User Manual

## Table of Contents

- [Log Analyzer User Manual](#log-analyzer-user-manual)
  - [Table of Contents](#table-of-contents)
  - [1. Introduction](#1-introduction)
  - [2. Key Features](#2-key-features)
    - [🚀 High Performance](#-high-performance)
    - [🔍 Powerful Filtering System](#-powerful-filtering-system)
    - [📂 File \& Compatibility](#-file--compatibility)
    - [🖥️ Intuitive UI](#️-intuitive-ui)
  - [3. User Guide](#3-user-guide)
    - [Menu Bar](#menu-bar)
      - [File](#file)
      - [Filter](#filter)
      - [View](#view)
      - [Notes](#notes)
      - [Help](#help)
    - [Shortcuts \& Operations](#shortcuts--operations)
  - [4. Release Notes](#4-release-notes)
    - [Version 1.6 (2025-12-19)](#version-16-2025-12-19)
      - [⚡ Core Engine Update](#-core-engine-update)
    - [Version 1.5 (2025-12-18)](#version-15-2025-12-18)
      - [⚡ Rust-Powered Core Engine](#-rust-powered-core-engine)
      - [🎨 UI \& UX Improvements](#-ui--ux-improvements)
    - [Version 1.4 (2025-12-08)](#version-14-2025-12-08)
      - [🎨 UI \& Navigation Enhancements](#-ui--navigation-enhancements)
      - [✨ Interactive Graphical Event Timeline](#-interactive-graphical-event-timeline)
    - [Version 1.3 (2025-12-02)](#version-13-2025-12-02)
      - [✨ Comprehensive Notes System](#-comprehensive-notes-system)
      - [🎨 UI \& User Experience Overhaul](#-ui--user-experience-overhaul)
    - [Version 1.2 (2025-11-28)](#version-12-2025-11-28)
      - [✨ New Features](#-new-features)
    - [Version 1.1 (2025-11-28)](#version-11-2025-11-28)
      - [⚡ Performance \& Logic](#-performance--logic)
      - [🛠 Fixes \& Changes](#-fixes--changes)
    - [Version 1.0 (2025-11-27)](#version-10-2025-11-27)
      - [✨ New Features](#-new-features-1)
      - [⚡ Performance Improvements](#-performance-improvements)
      - [🐛 Bug Fixes](#-bug-fixes)
  - [5. System Requirements](#5-system-requirements)

---

## 1. Introduction

**Log Analyzer** is a high-performance log analysis tool designed specifically for developers and system administrators. It addresses the common issue of lag and unresponsiveness found in traditional text editors when opening large log files, providing powerful features for filtering, searching, and syntax highlighting.

Version 1.1 introduces a multi-threaded architecture and JIT (Just-In-Time) dynamic compilation technology, ensuring a smooth interface and rapid filtering operations even when handling log files that are hundreds of MBs in size or contain tens of millions of lines.

## 2. Key Features

### 🚀 High Performance

* **Multi-threading Architecture**: File reading and filtering operations are performed in the background, ensuring the main window (UI) always remains responsive and eliminating "Not Responding" scenarios.

    * **Rust-Powered Core Engine**: The core filtering logic is powered by a custom Rust extension (`log_engine_rs`), replacing the legacy Python implementation.

      * **Parallel Processing**: Utilizes the `rayon` library to leverage all CPU cores, enabling sub-second filtering speeds even for massive log files (e.g., 1GB+).

### 🔍 Powerful Filtering System

* **Include & Exclude**: Supports positive filtering (showing only lines containing keywords) and negative exclusion (hiding lines containing keywords).

* **Regular Expressions (Regex)**: Supports Python standard regular expressions for complex pattern matching.

* **Custom Color Highlighting**: Each filter rule can have custom foreground and background colors, making critical information stand out.

* **Instant Toggle**: Specific filters can be checked/unchecked at any time with immediate view updates.

### 📂 File & Compatibility

* **TAT Format Support**: Fully compatible with `TextAnalysisTool.NET`'s `.tat` file format, allowing for seamless import/export of existing filter rules.

* **JSON Support**: Built-in functionality for importing/exporting filter rules in JSON format (Advanced feature).

### 🖥️ Intuitive UI

* **Progress Bar**: A status bar at the bottom provides real-time visual feedback on loading and filtering progress.

* **Detailed Statistics**: The status bar displays current Load Time, Filter Time, and displayed line count statistics.

* **Drag-and-Drop Sorting**: Filter priority can be adjusted simply by dragging the filter list items.

## 3. User Guide

### Menu Bar

#### File

* **Open Log...**: Open a log file (.log, .txt, *.*).

* **Open Recent**: Provides a list of the last 10 opened files for quick access. Includes an option to clear the list.

* **Load Filters**: Import filter rule files in `.tat` or `.xml` format.

* **Save Filters**: Save current filter rules to the file (overwrites the current file).

* **Save Filters As**: Save current filter rules as a new file.

* **Exit**: Close the application.

#### Filter

* **Add Filter**: Open the dialog to add a new filter rule.

* **Show Filtered Only (Ctrl+H)**:

  * **Checked**: Displays only lines that match the filter rules.

  * **Unchecked**: Displays all original log lines, but keeps keyword highlighting (Raw Mode).

#### View

*   **Find... (Ctrl+F)**: Opens a search bar at the top of the log view to find text within the entire log file.

*   **Go to Line... (Ctrl+G)**: Opens a dialog to jump directly to a specific line number.

*   **Dark Mode**: Toggles a persistent, application-wide dark theme for improved viewing in low-light environments.

*   **Show Timeline**: Opens a new window displaying a graphical timeline of events.
    *   This option is only enabled if the loaded log file contains recognizable timestamps.
    *   Events are filters that have been marked with the **"As Event"** property. The color of the event point on the timeline corresponds to the filter's background color.
    *   Hovering over an event point shows its timestamp, line number, and content; clicking it jumps to that line in the log view.

#### Notes

*   **Show Notes**: Toggles the visibility of the Notes View panel.

*   **Show in Separate Window**: When "Show Notes" is active, this toggles the Notes View between being docked in the main window or appearing as a separate, floating window.

*   **Save Notes to Text file**: Exports all current notes to a human-readable `.txt` file, formatted as `Line <Tab> Timestamp <Tab> Note Content`.


#### Help

* **Keyboard Shortcuts**: Displays a window with a summary of all keyboard shortcuts.
* **Documentation**: Opens this user manual.
* **About**: Displays application version information.

### Shortcuts & Operations

* **Double-click Log Content**: Selects text and quickly adds it as a new Filter.

*   **`c` key on Log View**: After selecting a line, press `c` to quickly add or edit a note for that line.

* **Double-click Filter List**: Edits the selected filter rule.

* **Space**: Toggles the Enable/Disable status of the selected filter in the list.

* **Delete**: Removes the selected filter.

* **Ctrl + H**: Toggles between "Show Filtered Only" and "Show All".

* **Ctrl + Scroll Wheel**: Adjusts the font size.

* **Ctrl + Left/Right Arrow**: Jumps to the previous/next match in the filtered results.

## 4. Release Notes

### Version 1.6 (2025-12-19)

#### ⚡ Core Engine Update

*   **Rust Engine Mandatory**: The legacy Python filtering fallback has been removed. The application now strictly relies on the high-performance Rust core (`log_engine_rs`) for all file loading and filtering operations.
*   **Streamlined Architecture**: This change reduces code complexity and ensures that all users benefit from the multi-threaded, zero-copy performance optimizations introduced in V1.5.
*   **Dependency Update**: The Rust toolchain is now a required dependency for building the application from source.

### Version 1.5 (2025-12-18)

#### ⚡ Rust-Powered Core Engine

This release introduces a groundbreaking performance upgrade by integrating a
Rust-based core engine.

*   **Extreme Performance**: Replaced the core file loading and filtering logic
    with a custom Rust extension (`log_engine_rs`).
*   **Parallel Processing**: Utilizes the `rayon` library to leverage all CPU
    cores for filtering, reducing processing time for large files (e.g., 1GB+)
    from seconds/minutes to sub-second speeds.
*   **Zero-Copy Loading**: Optimized memory usage by keeping log data in the
    Rust backend, significantly reducing Python memory overhead.
*   **Seamless Integration**: The application automatically detects the Rust
    extension and falls back to the standard Python implementation if not found.

#### 🎨 UI & UX Improvements

*   **Unified Typography**: Standardized the application font to **Consolas**
    (Size 12) for a consistent, developer-friendly look across all widgets.
*   **Global Scaling**: The Zoom function (`Ctrl + Scroll`) now scales the
    Notes View and other UI elements in sync with the Log View.
*   **Large File Support**: The line number area now dynamically adjusts its
    width to correctly display line numbers for files exceeding 10 million lines.
*   **Improved Dialogs**: Adjusted the "Keyboard Shortcuts" window size to
    prevent text truncation.

### Version 1.4 (2025-12-08)

#### 🎨 UI & Navigation Enhancements

*   **Full Dark Mode**: A new "View" -> "Dark Mode" option toggles a persistent, application-wide dark theme. The theme covers all elements, including the main window, dialogs, timeline, and notes view, for a comfortable experience in low-light environments.
*   **Recent Files Menu**: The "File" menu now includes an "Open Recent" list, providing one-click access to the last 10 opened log files.
*   **Find (Ctrl+F)**: A powerful new find bar appears at the top of the log view, allowing full-text search across the *entire* log file (not just the visible portion).
    *   Features include "Next (F3)" / "Previous (Shift+F3)", case sensitivity, and wrap-around search.
    *   The found line is automatically centered and set as the new focus line for a seamless workflow.
    *   The status bar provides clear feedback when a search completes.
*   **Go to Line (Ctrl+G)**: A new dialog allows you to instantly jump to any specific line number within the current view (filtered or full).

#### ✨ Interactive Graphical Event Timeline

This release introduces a major new feature: a graphical, interactive timeline to visualize log events over time. This allows users to quickly identify event clusters, correlations, and anomalies.

*   **New Timeline Window**: A new "View" -> "Show Timeline" menu option opens a resizable window that plots events based on their timestamps.
*   **Interactive Navigation**:
    *   **Zoom**: Use the mouse wheel to zoom in and out, centered on the cursor's position.
    *   **Pan**: Click and drag to pan the timeline horizontally.
*   **Event Configuration & Management**:
    *   The "Add/Edit Filter" dialog now includes an **"As Event"** checkbox.
    *   A new "Event" column in the filter list provides at-a-glance status (✓).
    *   Quickly toggle a filter's event status via the right-click context menu.
*   **Smart Tooltips & Interaction**:
    *   Hovering over an event point displays a sleek, dark-themed tooltip with the precise timestamp (including milliseconds), line number, and filter text.
    *   The tooltip intelligently repositions itself to avoid being clipped by the window edges.
    *   Clicking an event point jumps directly to that line in the main log view.
*   **Live Updates & Persistence**:
    *   The timeline window automatically refreshes when filters are modified or event statuses are changed.
    *   The "As Event" setting is now saved in the `.tat` filter file, ensuring persistence across sessions while maintaining compatibility with `TextAnalysisTool.NET`.

### Version 1.3 (2025-12-02)

#### ✨ Comprehensive Notes System

This release introduces a powerful notes system, allowing users to annotate, save, and share their findings directly within the application.

*   **Integrated Note View**: A new "Notes" panel can be docked to the right of the log view, allowing for simultaneous analysis and note-taking.
*   **Flexible Layout**: The Notes View can be toggled between a docked panel and a separate floating window via the "Notes" menu to suit any workflow.
*   **Automatic Save/Load**: Notes can be exported to a `.note` (JSON) file, which is automatically named after the log file. When reloading the same log, the application will detect the note file and ask to import it, preserving your work across sessions.
*   **Plain Text Export**: Added an option to "Save Notes to Text file," exporting notes in a clean, readable `.txt` format.
*   **Timestamp Extraction**: The Notes View automatically extracts and displays the timestamp from the corresponding log line, providing crucial context.
*   **Quick-Add Shortcut**: In the log view, simply select a line and press the `c` key to instantly add or edit a note.

#### 🎨 UI & User Experience Overhaul

This release brings a modernized look and feel to the application with a complete UI refresh.

*   **Modernized UI Theme**:
    *   Adopted the **'clam'** theme for a cleaner, more professional appearance.
    *   Replaced standard Tkinter widgets with **ttk widgets** (Buttons, Labels, Scrollbars, Frames) for better consistency and style.
    *   Updated the default font to **Segoe UI** for improved readability on Windows.

*   **Enhanced Filter Dialog**:
    *   Refactored the "Add/Edit Filter" dialog to use modern widgets.
    *   Improved layout and spacing for better usability.
    *   Added a **Cancel** button and made the dialog **modal** to prevent state issues.

---

### Version 1.2 (2025-11-28)

**✨ New Feature Update**

This release introduces a major usability feature for a more intuitive workflow.

#### ✨ New Features

*   **Drag and Drop to Open**: Users can now drag a log file (`.log`, `.txt`, etc.) directly onto the application window to open it.

---

### Version 1.1 (2025-11-28)

**🚀 Performance & Stability Update**

This release focuses on optimizing user interaction speed and fixing regression bugs found in v1.0.

#### ⚡ Performance & Logic

* **Instant View Switching**: The "Show Filtered Only" (`Ctrl+H`) toggle is now instantaneous. View generation is decoupled from data processing, eliminating lag when switching modes.

* **Smart Filter Toggling**:
    * **Disabling** a filter now triggers an instant view refresh without rescanning the file.
    * **Re-enabling** a previously calculated filter uses cached data for instant display.

* **Incremental Scanning**: Enabling a new filter now only scans lines that haven't been matched by existing filters, significantly reducing processing time for large files.

#### 🛠 Fixes & Changes

* **Default Behavior**: "Show Filtered Only" is now **Disabled** by default to provide a full context view upon loading.

* **Bug Fix**: Restored missing mouse wheel scrolling and zoom (`Ctrl + Wheel`) functionality that was affected in the previous threading refactor.

* **Bug Fix**: Resolved `AttributeError` related to scrollbar event handling.

---

### Version 1.0 (2025-11-27)

**🎉 First Official Release!**

This version marks a significant milestone for Log Analyzer, focusing on a complete overhaul of the user experience and extreme optimization of core performance.

#### ✨ New Features

* **New Menu Bar Design**: Refactored the crowded toolbar into standard File / Filter / Help menus for a cleaner interface.

* **About Dialog**: Added a window to display version information.

* **Improved Progress Feedback**: Added a bottom Progress Bar to provide clear visual feedback when processing large files.

#### ⚡ Performance Improvements

* **Multi-threaded Architecture Refactor**:

  * Moved file I/O and filtering operations to a background Worker Thread.

  * Resolved the issue of the window "freezing" (Not Responding) when processing large files.

* **JIT Loop Unrolling Optimization**:

  * Deeply optimized the filter calculation logic.

  * Eliminated loop iteration overhead by dynamically generating Python code.

  * **Performance Boost**: Reduced filtering time for 10 million log lines from **74 seconds** to **30 seconds**.

#### 🐛 Bug Fixes

* Fixed a crash (`tag "current_line" isn't defined`) that could occur when clicking the window before a file was loaded or filters initialized.

* Fixed an issue where the Status Bar would fail to display Load Time / Filter Time in certain scenarios.

* Removed trailing whitespace from the source code (Code Cleanup).

## 5. System Requirements

* **OS**: Windows / macOS / Linux

* **Runtime**: Python 3.6+

* **Dependencies**: Tkinter (Usually included with Python installation)