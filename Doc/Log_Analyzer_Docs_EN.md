# Log Analyzer V2.5 User Manual

## Table of Contents

- [Log Analyzer V2.5 User Manual](#log-analyzer-v25-user-manual)
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
    - [Version 2.5 (2026-04-21)](#version-25-2026-04-21)
    - [Version 2.4 (2026-03-17)](#version-24-2026-03-17)
    - [Version 2.3 (2026-03-12)](#version-23-2026-03-12)
    - [Version 2.2 (2026-01-29)](#version-22-2026-01-29)
    - [Version 2.1 (2026-01-15)](#version-21-2026-01-15)
    - [Version 2.0 (2026-01-12)](#version-20-2026-01-12)

---

## 1. Introduction

**Log Analyzer V2.5** focuses on stability and expanded compatibility. This version introduces **Intelligent Viewport Preservation**, which maintains your precise visual focus during complex filtering operations. Additionally, the core engine has been upgraded to support **UTF-16** encodings, making it a truly universal tool for enterprise-grade log analysis.

Designed for professional engineering workflows, it bridges the gap between massive scale and surgical precision.

## 2. Key Features

### 🚀 Next-Gen Performance

*   **Virtual Viewport**: A custom-built rendering engine that renders *only* the lines currently visible on screen. This allows the application to scroll through files with 100+ million lines as smoothly as a small text file.
*   **Rust-Powered Core**: Retains the high-performance Rust backend (`log_engine_rs`) for multi-threaded file loading and regular expression filtering.
*   **Universal Encoding**: Native support for UTF-16 (LE/BE) and UTF-8, ensuring consistent performance across diverse log formats.

### 🖥️ Modern & Flexible UI

*   **Activity Bar**: A VS Code-inspired vertical bar for quick access to **Log List**, **Filters**, and **Notes**. Includes **Notification Badges** that display the count of enabled filters and notes for the current file.
*   **Intelligent Viewport Preservation**: When toggling between Full and Filtered views, the application locks the focused line's relative position on screen, preventing "jump disorientation."
*   **Global Selection Tracking**: Unlike standard list views, selection state is now preserved globally. You can select multiple lines, scroll away to a different part of the file, and your selection remains intact.
*   **Area-Aware Docking**: Intelligent mutual exclusivity for docks. Panels in the same area (like Filters and Notes) swap automatically to maximize space, while floating panels remain independent.
*   **Refined Visuals**: Professional SVG iconography and layered Dark/Light modes provide a high-contrast, professional aesthetic.
*   **Customization**: A **Preferences Dialog** allows you to adjust UI/Editor fonts and spacing.

### 📊 Advanced Visualization

*   **Scrollbar Minimap (Heatmap)**: The vertical scrollbar track displays color-coded markers indicating the distribution of search results across the entire file.
*   **Jump Flash Feedback**: A subtle blue fade-out animation highlights the target line after a search jump or "Go to Line" operation.
*   **Zooming**: Quickly adjust the log view font size using **Ctrl + Wheel**.

### 🔍 Intelligent Search & Navigation

*   **Persistent Multi-Selection**: Select lines across different parts of the log. The application remembers every selected line even as you scroll through the virtual viewport.
*   **Cross-Viewport Copying**: Pressing `Ctrl + C` now copies *all* globally selected lines, regardless of whether they are currently visible on screen.
*   **Physical Top-Line Alignment**: Uses physical coordinate mapping (`indexAt`) to ensure 1:1 view reconstruction when switching modes.
*   **Floating Search Overlay**: A modern, non-intrusive search panel with history support.
*   **Smart "Go to Line"**: In Filtered View, entering a raw line number that is currently hidden will automatically trigger a switch to Full View.

### 📝 Comprehensive Notes System

*   **Integrated Workflow**: Press `C` on any line to add/edit a note.
*   **Visual Highlights**: Lines with notes are highlighted with a distinct background.
*   **Persistence**: Notes are saved to `.note` files and reloaded automatically.

## 3. User Guide

### Activity Bar (Far Left)
*   **File List**: Manage multiple loaded log files.
*   **Filters**: Add, edit, or reorder filter rules.
*   **Notes**: View and navigate all notes in the current file.
*   **Badges**: Dynamic counters for active filters and notes.

### Status Bar (Bottom)
*   **Left Section**: Displays current view mode. Click to toggle.
*   **Middle Section**: Displays line counts. Click to trigger "Go to Line".
*   **Right Section**: Displays current line position and file encoding.

### Notification System (Toasts)
*   **Stacking**: Multiple notifications stack from the bottom.
*   **Contextual Coloring**: Success (Green), Warning (Yellow), Info (Standard).

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
| **Esc** | Close Search Bar / Clear Selection |

### Preferences

Access via the **Settings (Gear)** icon at the bottom of the Activity Bar.

*   **General**: Theme toggle and reset defaults.
*   **Editor**: Monospaced font selection, size, line spacing, and line number toggle.
*   **UI**: UI font family and scaling for high-DPI displays.

## 4. Release Notes

### Version 2.5 (2026-04-21)

**Stability & Compatibility**
*   **Intelligent Viewport Preservation**: Implemented a sophisticated focus-locking mechanism that maintains the current anchor line's position during filter changes.
*   **UTF-16 Engine Support**: The high-performance Rust core now natively handles UTF-16 log files, including automatic detection of endianness.
*   **Maximized Window Fixes**: Resolved issues where the frameless window would occasionally freeze or overflow the desktop area when maximized on Windows.
*   **Search Engine Optimization**: Refined memory allocation in the Rust extension for faster filtering of massive datasets.

### Version 2.4 (2026-03-17)

**Selection & Interaction Reliability**
*   **Multi-Selection Persistence**: Fixed an issue where multi-selections were lost during mouse wheel scrolling. Selection states are now tracked globally.
*   **Cross-Viewport Copying**: Enhanced the `Copy` operation (`Ctrl+C`) to include all globally selected lines, even those scrolled out of the current view.
*   **Selection Memory per File**: The application now remembers the exact selection state for each loaded log file when switching between them in the sidebar.
*   **Escape to Clear**: Pressing `Esc` now clears the current selection in addition to closing the search bar, providing a quick way to reset the view state.

### Version 2.3 (2026-03-12)

**Visual Continuity & Locking**
*   **Selection Anchor Preservation**: The selected line now maintains its exact relative vertical position on the screen when toggling between Full and Filtered views.
*   **Physical Coordinate Alignment**: Switched to a physical coordinate-based anchoring system (`indexAt`) to ensure 1:1 view reconstruction.

**Enhanced Navigation UX**
*   **Jump Flash Feedback**: Added a blue fade-out animation to the target line when performing search jumps or "Go to Line" operations.
*   **Turbo Boundary Navigation**: Holding Up/Down keys at the viewport edges now scrolls 3x faster.

**Scrolling & Performance**
*   **Native Scroll Sync**: Mouse wheel scrolling now respects the operating system's "lines per notch" setting.
*   **Viewport Stability**: Optimized buffer management to eliminate the "bounce-back" effect during rapid scrolling.

### Version 2.2 (2026-01-29)

**UX & Navigation**
*   **Smart Context Persistence**: Significantly improved behavior when switching between "Full Log" and "Filtered View" (Ctrl+H).
*   **Scroll Stability**: Fixed jitter issues during slow scrolling.

### Version 2.1 (2026-01-15)

**Structural Refactoring**
*   **MVC Architecture**: Decoupled business logic from the UI using dedicated controllers.
*   **Centralized Theming**: Introduced `ThemeManager` for consistent styling across the application.

**New Features**
*   **Preferences System**: Comprehensive settings for UI scaling and editor appearance.
*   **Zooming Support**: Added `Ctrl + Wheel` for quick font scaling.

### Version 2.0 (2026-01-12)

**Major Architecture Overhaul**
*   **Qt (PySide6) Transition**: Completely rebuilt the UI for superior stability and native performance.
*   **Virtual Viewport**: Zero-lag rendering for massive files (100M+ lines).
*   **Modern UI Components**: Floating search overlay, activity bar badges, and interactive status bar.
