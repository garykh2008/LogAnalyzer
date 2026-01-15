# Log Analyzer V2.0 User Manual

## Table of Contents

- [Log Analyzer V2.0 User Manual](#log-analyzer-v20-user-manual)
  - [1. Introduction](#1-introduction)
  - [2. Key Features](#2-key-features)
    - [🚀 Next-Gen Performance](#-next-gen-performance)
    - [🖥️ Modern \& Flexible UI](#️-modern--flexible-ui)
    - [📊 Advanced Visualization](#-advanced-visualization)
    - [🔍 Intelligent Search \& Navigation](#-intelligent-search--navigation)
    - [📝 Comprehensive Notes System](#-comprehensive-notes-system)
  - [3. User Guide](#3-user-guide)
    - [Activity Bar (Far Left)](#activity-bar-far-left)
    - [Status Bar (Bottom)](#status-bar-bottom)
    - [Notification System (Toasts)](#notification-system-toasts)
    - [Shortcuts](#shortcuts)
    - [Preferences](#preferences)
  - [4. Release Notes](#4-release-notes)
    - [Version 2.1 (2026-01-15)](#version-21-2026-01-15)
    - [Version 2.0 (2026-01-12)](#version-20-2026-01-12)

---

## 1. Introduction

**Log Analyzer V2.1** builds upon the robust Qt architecture of V2.0, focusing on refined modularity, customizable user preferences, and a polished visual experience.

Designed for high-performance log analysis, it continues to leverage the **Virtual Viewport** and Rust-powered filtering while introducing a centralized **Theme Manager** and a dedicated **Preferences** system.

## 2. Key Features

### 🚀 Next-Gen Performance

*   **Virtual Viewport**: A custom-built rendering engine that renders *only* the lines currently visible on screen. This allows the application to scroll through files with 100+ million lines as smoothly as a small text file.
*   **Rust-Powered Core**: Retains the high-performance Rust backend (`log_engine_rs`) for multi-threaded file loading and regular expression filtering.

### 🖥️ Modern & Flexible UI

*   **Activity Bar**: A VS Code-inspired vertical bar for quick access to **Log List**, **Filters**, and **Notes**. Includes **Notification Badges** that display the count of enabled filters and notes for the current file.
*   **Docking System**: Fully dockable panels for Filters and Notes. You can pin them to any edge, tab them together, or float them as separate windows. 
    *   *Note: On Linux, a simplified fixed-layout mode is used to ensure maximum stability.*
*   **Refined Visuals**: 
    *   **Flat Menu Design**: Modern, frameless menus with rounded corners and optimized spacing.
    *   **Layered Theming**: Polished Dark/Light modes with better contrast and visual hierarchy.
*   **Customization**: A new **Preferences Dialog** allows you to adjust UI font sizes, editor fonts, and line spacing to suit your display setup.

### 📊 Advanced Visualization

*   **Scrollbar Minimap (Heatmap)**: The vertical scrollbar track now displays color-coded markers (orange/yellow) indicating the distribution of search results across the entire file.
*   **Zooming**: Quickly adjust the log view font size using **Ctrl + Wheel**.
*   **Density View**: Provides a high-level overview of where matches are concentrated, allowing you to jump to interesting sections instantly.

### 🔍 Intelligent Search & Navigation

*   **Floating Search Overlay**: A modern, non-intrusive search panel with shadows and animations.
*   **Search History**: Access previous search queries by clicking the input box or pressing the **Down** arrow key.
*   **Interactive Status Bar**: 
    *   Click the **Line Count** to open the "Go to Line" dialog.
    *   Click the **View Mode** label to toggle "Show Filtered Only" instantly.
*   **Smart "Go to Line"**: In Filtered View, you can still enter **raw line numbers**. If the target line is hidden by filters, the app will automatically switch back to Full View to reach the destination.

### 📝 Comprehensive Notes System

*   **Integrated Workflow**: Press `C` on any line to add/edit a note.
*   **Visual Highlights**: Lines with notes are highlighted with a distinct background.
*   **Persistence**: Notes are saved to `.note` files and reloaded automatically.

## 3. User Guide

### Activity Bar (Far Left)
*   **File List**: Manage multiple loaded log files.
*   **Filters**: Add, edit, or reorder filter rules (`.tat` format supported).
*   **Notes**: View and navigate all notes in the current file.
*   **Badges**: Look for the small blue circles on icons—they indicate your active filter count and total notes.

### Status Bar (Bottom)
*   **Left Section**: Displays the current view mode (Full vs. Filtered). Click to toggle.
*   **Middle Section**: Displays line counts. Click to trigger "Go to Line".
*   **Busy Indicator**: A rotating spinner appears here during heavy Rust operations (loading/filtering).

### Notification System (Toasts)
*   **Stacking**: Multiple notifications can now appear simultaneously, stacking from the bottom.
*   **Contextual Coloring**: 
    *   **Success (Green)**: File loaded, settings saved.
    *   **Warning (Yellow)**: Search wrap-around, hidden lines.
    *   **Info (Standard)**: Copied text, mode toggled.

### Shortcuts

| Key Combination | Action |
| :--- | :--- |
| **Ctrl + O** | Open Log File(s) |
| **Ctrl + F** | Open Search Bar |
| **Ctrl + G** | Go to Line |
| **F3 / F2** | Find Next / Previous |
| **Ctrl + H** | Toggle "Show Filtered Only" |
| **Ctrl + Shift + L** | Toggle Log Files Panel |
| **Ctrl + Shift + F** | Toggle Filters Panel |
| **Ctrl + Shift + N** | Toggle Notes Panel |
| **Ctrl + Left/Right** | Navigate Filter Hits (Selected Filter) |
| **Ctrl + Wheel** | Zoom Log View In / Out |
| **Double-Click** (Log) | Create Filter from selected text |
| **C** | Add / Edit Note for selected line |
| **Esc** | Close Search Bar / Dialogs |

### Preferences

Access via the **Settings (Gear)** icon at the bottom of the Activity Bar.

*   **General**: 
    *   **Theme**: Toggle between Dark and Light modes.
    *   **Reset to Defaults**: Restore all application settings to their original state.
*   **Editor**:
    *   **Font**: Select your preferred monospaced font for log viewing.
    *   **Font Size**: Set the base font size.
    *   **Line Spacing**: Adjust the vertical density of log lines.
    *   **Show Line Numbers**: Toggle the gutter display.
*   **UI**:
    *   **Font Family**: Customize the font used for menus, dialogs, and sidebars.
    *   **Font Size**: Scale the entire application UI for better readability on high-DPI screens.

## 4. Release Notes

### Version 2.1 (2026-01-15)

**Structural Refactoring**
*   **MVC Architecture**: Successfully decoupled business logic from the UI by extracting dedicated controllers (`LogController`, `FilterController`, `SearchController`), significantly improving code maintainability.
*   **Centralized Theming**: Introduced `ThemeManager` to unify color palettes and QSS generation, facilitating easier theme adjustments and consistent styling across all dialogs.

**New Features**
*   **Preferences System**: A comprehensive settings dialog allowing users to customize:
    *   **UI Scalability**: Dynamic adjustment of UI font size and family.
    *   **Editor Appearance**: Configurable line spacing and editor fonts.
    *   **System Controls**: "Reset to Defaults" functionality.
*   **Zooming Support**: Added `Ctrl + Wheel` shortcut for quick font size scaling in the Log View.

**UI/UX Polish**
*   **Modern Menu Design**: Completely redesigned menus with a flat, frameless aesthetic, rounded corners, and optimized spacing for a cleaner look.
*   **Interactive Status Bar**: Transformed the status bar into a functional command center with clickable sections for View Mode and Line Jump.
*   **Visual Refinements**: Enhanced dark/light mode palettes with better contrast and layered backgrounds.

### Version 2.0 (2026-01-12)

**Major Architecture Overhaul**
*   **Qt (PySide6) Transition**: Completely rebuilt the UI for superior stability and native performance.
*   **Unified Entry Point**: Added `loganalyzer.py` at the root for easier execution.

**New Visual Features**
*   **Scrollbar Minimap**: Visual distribution of search results.
*   **Floating Search Overlay**: Redesigned with shadows, rounded corners, and history support.
*   **Activity Bar Badges**: Dynamic counters for active filters and notes.
*   **Enhanced Status Bar**: Now interactive with clickable quick-actions.
*   **Advanced Toast System**: Stacking notifications with status visualization.

**Stability & UX**
*   **Virtual Viewport**: Zero-lag rendering for massive files.
*   **Cross-Platform Optimization**: Tailored Docker and Windowing behavior for Windows and Linux (Wayland/X11).
*   **Gutter Background**: Distinct visual styling for the line number area.