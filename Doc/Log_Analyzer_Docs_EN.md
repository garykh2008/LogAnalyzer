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
      - [Help](#help)
    - [Shortcuts \& Operations](#shortcuts--operations)
  - [4. Release Notes](#4-release-notes)
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

* **JIT Dynamic Compilation Filtering Engine**: Utilizes Dynamic Code Generation technology to "unroll" complex filtering rules into highly efficient Python code, eliminating loop overhead.

  * *Performance Benchmark*: Applying 81 filtering rules to an 800MB / 10 million line test file takes approximately **30 seconds**.

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

* **Open Log**: Open a log file (.log, .txt, *.*).

* **Load Filters**: Import filter rule files in `.tat` or `.xml` format.

* **Save Filters**: Save current filter rules to the file (overwrites the current file).

* **Save Filters As**: Save current filter rules as a new file.

* **Exit**: Close the application.

#### Filter

* **Add Filter**: Open the dialog to add a new filter rule.

* **Show Filtered Only (Ctrl+H)**:

  * **Checked**: Displays only lines that match the filter rules.

  * **Unchecked**: Displays all original log lines, but keeps keyword highlighting (Raw Mode).

#### Help

* **Documentation**: Opens this user manual.
* **About**: Displays application version information.

### Shortcuts & Operations

* **Double-click Log Content**: Selects text and quickly adds it as a new Filter.

* **Double-click Filter List**: Edits the selected filter rule.

* **Space**: Toggles the Enable/Disable status of the selected filter in the list.

* **Delete**: Removes the selected filter.

* **Ctrl + H**: Toggles between "Show Filtered Only" and "Show All".

* **Ctrl + Scroll Wheel**: Adjusts the font size.

* **Ctrl + Left/Right Arrow**: Jumps to the previous/next match in the filtered results.

## 4. Release Notes

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