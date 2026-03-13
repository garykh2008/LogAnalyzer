# Log Analyzer V2.3 User Manual

## Table of Contents

- [Log Analyzer V2.3 User Manual](#log-analyzer-v23-user-manual)
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
    - [Version 2.3 (2026-03-12)](#version-23-2026-03-12)
    - [Version 2.2 (2026-01-29)](#version-22-2026-01-29)
    - [Version 2.1 (2026-01-15)](#version-21-2026-01-15)
    - [Version 2.0 (2026-01-12)](#version-20-2026-01-12)

---

## 1. Introduction

**Log Analyzer V2.3** represents a major leap in user experience and visual continuity. Building on the robust Qt architecture of V2.0, this version focuses on "Zero-Context Loss" navigation and professional-grade UI refinements.

Designed for high-performance log analysis, it ensures that your visual focus remains locked, your navigation feels native, and your workspace stays clean and efficient across Windows and Linux environments.

## 2. Key Features

### 🚀 Next-Gen Performance

*   **Virtual Viewport**: A custom-built rendering engine that renders *only* the lines currently visible on screen. This allows the application to scroll through files with 100+ million lines as smoothly as a small text file.
*   **Rust-Powered Core**: Retains the high-performance Rust backend (`log_engine_rs`) for multi-threaded file loading and regular expression filtering.

### 🖥️ Modern & Flexible UI

*   **Activity Bar**: A VS Code-inspired vertical bar for quick access to **Log List**, **Filters**, and **Notes**. Includes **Notification Badges** that display the count of enabled filters and notes for the current file.
*   **Selection Anchor Preservation**: When toggling between Full and Filtered views, the application now locks the selected line's relative position on screen, preventing "jump disorientation."
*   **Area-Aware Docking**: Intelligent mutual exclusivity for docks. Panels in the same area (like Filters and Notes) swap automatically to maximize space, while floating panels remain independent.
*   **Refined Visuals**: 
    *   **Flat Menu Design**: Modern, frameless menus with rounded corners and optimized spacing.
    *   **Professional SVG Iconography**: A complete set of professional SVG assets that dynamically adapt to your chosen theme (Dark/Light).
    *   **Layered Theming**: Polished Dark/Light modes with better contrast and visual hierarchy.
*   **Customization**: A new **Preferences Dialog** allows you to adjust UI font sizes, editor fonts, and line spacing to suit your display setup.

### 📊 Advanced Visualization

*   **Scrollbar Minimap (Heatmap)**: The vertical scrollbar track now displays color-coded markers (orange/yellow) indicating the distribution of search results across the entire file.
*   **Jump Flash Feedback**: A subtle blue fade-out animation highlights the target line after a search jump (F2/F3) or "Go to Line" operation, ensuring instant visual confirmation.
*   **Zooming**: Quickly adjust the log view font size using **Ctrl + Wheel**.

### 🔍 Intelligent Search & Navigation

*   **Physical Top-Line Alignment**: Uses physical coordinate mapping (`indexAt`) to ensure 1:1 view reconstruction when switching modes, eliminating numerical drift in massive files.
*   **Floating Search Overlay**: A modern, non-intrusive search panel with shadows and animations.
*   **Search History**: Access previous search queries by clicking the input box or pressing the **Down** arrow key.
*   **Smart "Go to Line"**: In Filtered View, you can still enter **raw line numbers**. If the target line is hidden by filters, the app will automatically switch back to Full View to reach the destination.
*   **Native Scroll Sync**: Mouse wheel behavior now automatically respects the system's "lines per notch" settings for a truly native feel.

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
| **Ctrl + H** | Toggle "Show Filtered Only" (Maintains Selection Anchor) |
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

### Version 2.3 (2026-03-12)

**Visual Continuity & Locking**
*   **Selection Anchor Preservation**: The selected line now maintains its exact relative vertical position on the screen when toggling between Full and Filtered views.
*   **Physical Coordinate Alignment**: Switched to a physical coordinate-based anchoring system (`indexAt`) to ensure 1:1 view reconstruction, eliminating calculation drifts in massive log files.

**Enhanced Navigation UX**
*   **Jump Flash Feedback**: Added a blue fade-out animation to the target line when performing search jumps (F2/F3) or "Go to Line" operations.
*   **Turbo Boundary Navigation**: Holding Up/Down keys at the viewport edges now scrolls 3x faster for smoother traversal through long files.

**Scrolling & Performance**
*   **Native Scroll Sync**: Mouse wheel scrolling now respects the operating system's "lines per notch" setting.
*   **Viewport Stability**: Eliminated the "bounce-back" effect during rapid scrolling by optimizing buffer management and coordinate mapping.

**UI/UX Polishing**
*   **Professional Asset Migration**: Introduced a complete set of high-quality SVG icons with dynamic theme-aware recoloring.
*   **Windows 11 Aesthetics**: Applied rounded corners to all dialogs and improved tool-tip styling.
*   **Smart Dock Management**: Implemented area-aware dock exclusivity on Windows, allowing panels like Filters and Notes to intelligently swap spaces.

**Cross-Platform Fixes**
*   Comprehensive fixes for Linux UI issues, including ghosting, residue panels, and window exposure problems.
*   Fixed an issue where copied text contained extra newline characters.

### Version 2.2 (2026-01-29)

**UX & Navigation**
*   **Smart Context Persistence**: Significantly improved behavior when switching between "Full Log" and "Filtered View" (Ctrl+H).
    *   The application now seamlessly maintains your scroll position and selection context.
    *   If the currently selected line is hidden by active filters, the view automatically adjusts to show the nearest visible context, preventing you from losing your place.
*   **Scroll Stability**: Fixed jitter issues where the view could snap unexpectedly during slow scrolling or when selecting lines near the viewport edges.

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
