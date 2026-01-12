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
  - [4. Release Notes](#4-release-notes)
    - [Version 2.0 (2026-01-12)](#version-20-2026-01-12)

---

## 1. Introduction

**Log Analyzer V2.0** represents a complete architectural overhaul, transitioning from the legacy Tkinter framework to the modern, industrial-grade **Qt (PySide6)** ecosystem. 

Designed for high-performance log analysis, V2.0 introduces a **Virtual Viewport** rendering engine capable of displaying millions of log lines with zero lag, a fully customizable **Docking UI**, and a refined user experience powered by a high-speed Rust filtering core.

## 2. Key Features

### 🚀 Next-Gen Performance

*   **Virtual Viewport**: A custom-built rendering engine that renders *only* the lines currently visible on screen. This allows the application to scroll through files with 100+ million lines as smoothly as a small text file.
*   **Rust-Powered Core**: Retains the high-performance Rust backend (`log_engine_rs`) for multi-threaded file loading and regular expression filtering.

### 🖥️ Modern & Flexible UI

*   **Activity Bar**: A VS Code-inspired vertical bar for quick access to **Log List**, **Filters**, and **Notes**. Includes **Notification Badges** that display the count of enabled filters and notes for the current file.
*   **Docking System**: Fully dockable panels for Filters and Notes. You can pin them to any edge, tab them together, or float them as separate windows. 
    *   *Note: On Linux, a simplified fixed-layout mode is used to ensure maximum stability.*
*   **Professional Theming**: Polished **Dark Mode** and **Light Mode** with consistent styling across all components, including a custom frameless title bar.
*   **Distinct Line Gutter**: A dedicated line number area with its own background color, visually separated from the content for better readability.

### 📊 Advanced Visualization

*   **Scrollbar Minimap (Heatmap)**: The vertical scrollbar track now displays color-coded markers (orange/yellow) indicating the distribution of search results across the entire file.
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
| **Double-Click** (Log) | Create Filter from selected text |
| **C** | Add / Edit Note for selected line |
| **Esc** | Close Search Bar / Dialogs |

## 4. Release Notes

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