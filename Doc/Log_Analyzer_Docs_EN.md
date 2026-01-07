# Log Analyzer V2.0 User Manual

## Table of Contents

- [Log Analyzer V2.0 User Manual](#log-analyzer-v20-user-manual)
  - [Table of Contents](#table-of-contents)
  - [1. Introduction](#1-introduction)
  - [2. Key Features](#2-key-features)
    - [🚀 Next-Gen Performance](#-next-gen-performance)
    - [🖥️ Modern \& Flexible UI](#️-modern--flexible-ui)
    - [🔍 Enhanced Search \& Navigation](#-enhanced-search--navigation)
    - [📝 Comprehensive Notes System](#-comprehensive-notes-system)
  - [3. User Guide](#3-user-guide)
    - [Menu Bar](#menu-bar)
      - [File](#file)
      - [View](#view)
      - [Filter (Dock)](#filter-dock)
      - [Notes (Dock)](#notes-dock)
      - [Help](#help)
    - [Shortcuts](#shortcuts)
  - [4. Release Notes](#4-release-notes)
    - [Version 2.0 (2026-01-07)](#version-20-2026-01-07)
      - [Major Architecture Overhaul](#major-architecture-overhaul)
      - [Key Improvements](#key-improvements)
      - [New Features \& Enhancements](#new-features--enhancements)

---

## 1. Introduction

**Log Analyzer V2.0** represents a complete architectural overhaul, transitioning from the legacy Tkinter framework to the modern, industrial-grade **Qt (PySide6)** ecosystem. 

Designed for developers and system administrators who demand speed and flexibility, V2.0 introduces a **Virtual Viewport** rendering engine capable of displaying millions of log lines with zero lag, a fully customizable **Docking UI**, and a refined user experience that retains the powerful Rust-based filtering core of previous versions.

## 2. Key Features

### 🚀 Next-Gen Performance

*   **Virtual Viewport**: A custom-built rendering engine that renders *only* the lines currently visible on screen. This allows the application to scroll through files with 100+ million lines as smoothly as a small text file, with minimal memory footprint for UI elements.
*   **Rust-Powered Core**: Retains the high-performance Rust backend (`log_engine_rs`) for multi-threaded file loading and regular expression filtering.

### 🖥️ Modern & Flexible UI

*   **Docking System**: The **Filters** and **Notes** panels are now fully dockable. You can:
    *   Pin them to the Left, Right, or Bottom of the window.
    *   Tab them together to save space.
    *   Float them as separate windows for multi-monitor setups.
*   **Professional Theming**: Features a polished **Dark Mode** (default) and **Light Mode**, with consistent styling across all dialogs, scrollbars, and menus.
*   **Dynamic Line Numbers**: Integrated line number display that automatically adjusts its width based on the total line count.

### 🔍 Enhanced Search & Navigation

*   **Modern Search Bar**: A sleek, floating search bar (`Ctrl+F`) with toggle buttons for **Match Case (Aa)** and **Wrap Around (W)**.
*   **Global Navigation**: 
    *   **F3 / F2**: Jump to the Next / Previous search match instantly, even if it's millions of lines away.
    *   **Ctrl + Left / Right**: Jump to the Previous / Next line that matches the *currently selected filter*.

### 📝 Comprehensive Notes System

*   **Integrated Workflow**: Press `C` on any line to instantly add or edit a note.
*   **Visual Highlights**: Lines with notes are visually highlighted with a distinct background color.
*   **Persistence**: Notes are automatically saved to sidecar `.note` (JSON) files and automatically reloaded when you open the log again.
*   **Export**: Generate a readable text report of all your notes via the "Export Notes to Text..." menu.

## 3. User Guide

### Menu Bar

#### File
*   **Open Log... (Ctrl+O)**: Open a single log file.
*   **Open Recent**: Quickly access recently opened files.
*   **Load / Save Filters**: Import or export your filter rules (`.tat` format).
*   **Exit (Ctrl+Q)**: Close the application.

#### View
*   **Toggle Notes**: Show or hide the Notes docking panel.
*   **Export Notes to Text...**: Save all current notes to a `.txt` file.
*   **Show Filtered Only (Ctrl+H)**: Toggle between showing all lines (with highlights) and showing only lines that match enabled filters.
*   **Toggle Dark/Light Mode**: Switch the application theme.
*   **Find... (Ctrl+F)**: Open the search bar.

#### Filter (Dock)
*   **Management**: Add, Edit, or Remove filters.
*   **Drag & Drop**: Reorder filters by dragging them.
*   **Checkboxes**: Enable/Disable specific filters instantly.

#### Notes (Dock)
*   **List View**: Displays all notes associated with the current file, including line number and timestamp.
*   **Navigation**: Double-click a note in the list to jump to that line in the log.
*   **Save Button**: Manually save notes to disk (auto-save is also performed on exit).

#### Help
*   **Keyboard Shortcuts**: View a list of available hotkeys.
*   **About**: Version and developer information.

### Shortcuts

| Key Combination | Action |
| :--- | :--- |
| **Ctrl + O** | Open Log File |
| **Ctrl + F** | Open Find Bar |
| **F3 / F2** | Find Next / Previous |
| **Ctrl + H** | Toggle "Show Filtered Only" |
| **Ctrl + B** | Toggle Sidebar (if applicable) |
| **Ctrl + Left/Right** | Navigate Filter Hits |
| **Double-Click** (Log) | Create Filter from selected text |
| **C** | Add / Edit Note for selected line |
| **Space** (Filter List) | Toggle Filter Enabled/Disabled |
| **Delete** (Filter List) | Remove Filter |

## 4. Release Notes

### Version 2.0 (2026-01-07)

#### Major Architecture Overhaul
*   **Qt (PySide6) Rewrite**: The application UI has been completely rewritten from Tkinter to Qt, offering a native, robust, and scalable interface.
*   **Virtual Viewport Implementation**: Solved the performance bottleneck of rendering large lists. The UI now handles massive logs with zero lag.

#### Key Improvements
*   **Docking UI**: Filters and Notes are now movable, dockable panels, allowing for a personalized workspace layout.
*   **Search Upgrade**: A completely redesigned search experience with modern toggle buttons, instant case-sensitivity updates, and reliable navigation across massive files.
*   **Virtual Viewport**: The core rendering engine ensures stable performance regardless of file size.

#### New Features & Enhancements
*   **Notes System**: Fully ported with enhancements like JSON persistence, auto-loading, and text export.
*   **Modern Theme**: A polished dark/light theme consistent across all dialogs.
