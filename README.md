# 🔍 Log Analyzer V2.2

> A professional, high-performance log analysis tool powered by Qt and Rust.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square)
![PySide6](https://img.shields.io/badge/UI-PySide6-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-success?style=flat-square)

**Log Analyzer V2.2** builds upon the robust architecture of V2.0, focusing on refined modularity, customizable user preferences, and a polished visual experience. It addresses the common issue of lag and unresponsiveness when opening massive log files by utilizing a custom **Virtual Viewport** rendering engine and a high-performance **Rust core**.

---

## ✨ Key Features

### 🚀 Next-Gen Performance
- **Virtual Viewport**: Smoothly scroll through 100M+ lines with zero lag.
- **Rust-Powered Core**: Sub-second filtering and loading powered by Rust and `rayon`.
- **Zero-Copy Architecture**: Minimal memory footprint even with massive datasets.

### 🖥️ Modern & Flexible UI
- **Preferences System**: Comprehensive settings dialog for customizing fonts, scaling, and line spacing.
- **Dockable Panels**: Fully customizable workspace with movable and stackable "Filters" and "Notes" panels.
- **Activity Bar**: VS Code-inspired sidebar for quick navigation with dynamic **Notification Badges**.
- **Scrollbar Heatmap**: A visual minimap on the scrollbar track to identify search result distribution at a glance.
- **Professional Theming**: Polished Dark and Light modes with consistent styling across all dialogs and menus.

### 🔍 Intelligent Analysis
- **Smart Context Persistence**: Seamlessly maintains scroll position and selection context when switching between Full and Filtered views.
- **Smart Search**: Floating search overlay with history, regex support, and instant navigation (F2/F3).
- **Interactive Status Bar**: Quick-actions for toggling view modes and jumping to specific line numbers.
- **Integrated Notes**: Seamlessly annotate log lines with auto-persistence to sidecar files.

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.8+**
- **PySide6** (`pip install PySide6`)
- **Rust Toolchain** (only required if building from source)

### Running the Application

**GUI Mode:**
```bash
python loganalyzer.py
```

**Command Line (CLI):**
Log Analyzer supports robust CLI arguments for automation:
```bash
# Open a single log file
python loganalyzer.py app.log

# Open multiple log files (wildcards supported)
python loganalyzer.py logs/*.log

# Load a specific filter set on startup
python loganalyzer.py app.log -f my_filters.tat
```

---

## 📖 Documentation

For a comprehensive guide on all features, keyboard shortcuts, and advanced configuration, please consult the full documentation:

👉 **[Read the Complete User Manual](Doc/Log_Analyzer_Docs_EN.md)**

---

## 📦 Version History

- **v2.2**: UX refinements, Smart Context Persistence, and scroll stability improvements.
- **v2.1**: Introduced Preferences Dialog, Theme Manager, and MVC refactoring.
- **v2.0**: Major transition to Qt (PySide6). Introduced Virtual Viewport, Docking UI, Scrollbar Heatmap, Activity Bar Badges, and a completely redesigned UX.
- **v1.7**: Multi-Log Management and Merged View.
- **v1.6**: Introduction of the Rust Core Engine.

*(See [Release Notes](Doc/Log_Analyzer_Docs_EN.md#4-release-notes) for full history)*