# 🔍 Log Analyzer V2.5

> A professional, high-performance log analysis tool powered by Qt and Rust.

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square)
![PySide6](https://img.shields.io/badge/UI-PySide6-green?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-success?style=flat-square)

**Log Analyzer V2.5** introduces **Intelligent Viewport Preservation** and broadens encoding support with native **UTF-16** handling. This version ensures a seamless analysis experience by maintaining visual focus during filtering transitions and resolving critical UI stability issues on high-resolution displays.

---

## ✨ Key Features

### 🚀 Next-Gen Performance
- **Virtual Viewport**: Smoothly scroll through 100M+ lines with zero lag.
- **Rust-Powered Core**: Sub-second filtering and loading powered by Rust and `rayon`.
- **UTF-16 Support**: Native support for UTF-16 encoded logs (LE/BE) within the high-performance engine.
- **Ultra-Stable Viewport**: Optimized buffer management to eliminate scrolling jitter and "bounce-back" effects.

### 🖥️ Modern & Flexible UI
- **Intelligent Viewport Preservation**: Focus remains locked on the current line during filter toggles, preventing jump disorientation.
- **Global Selection Tracking**: Selections are preserved even when lines scroll out of the viewport.
- **Selection Anchor Locking**: Maintains the exact vertical position of your selected line when toggling view modes.
- **Professional SVG Icons**: Theme-aware iconography system for a consistent look across Dark and Light modes.
- **Windows 11 Visuals**: Refined UI with rounded corners and modern dialog styling.

### 🔍 Intelligent Analysis
- **Cross-Viewport Copying**: `Ctrl+C` now copies all globally selected lines, regardless of visibility.
- **Selection Memory**: Remembers selection states independently for every loaded log file.
- **Jump Flash Feedback**: Visual confirmation highlighting the target line after search or line jumps.
- **Physical Coordinate Sync**: Precision 1:1 view reconstruction using physical screen coordinates.
- **Native Scroll Speed**: Mouse wheel behavior now synchronizes with system-level scroll settings.

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

- **v2.5**: Intelligent Viewport Preservation, UTF-16 encoding support, and maximized window stability fixes.
- **v2.4**: Multi-Selection persistence during scroll, Cross-Viewport copying, and Selection memory per file.
- **v2.3**: View continuity locking, Jump Flash feedback, and Native scroll sync.
- **v2.2**: UX refinements, Smart Context Persistence, and scroll stability improvements.
- **v2.1**: Introduced Preferences Dialog, Theme Manager, and MVC refactoring.
- **v2.0**: Major transition to Qt (PySide6). Introduced Virtual Viewport, Docking UI, and completely redesigned UX.

*(See [Release Notes](Doc/Log_Analyzer_Docs_EN.md#4-release-notes) for full history)*
