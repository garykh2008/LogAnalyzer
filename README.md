# 🔍 Log Analyzer

> A high-performance, multi-threaded log analysis tool designed for developers and system administrators.

![Python](https://img.shields.io/badge/Python-3.6%2B-blue?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-success?style=flat-square)

**Log Analyzer** addresses the common issue of lag and unresponsiveness found in traditional text editors when opening large log files. It provides a robust suite of tools for filtering, searching, and visualizing log data, powered by a custom Rust engine for sub-second performance even with massive datasets.

---

## ✨ Key Features

### 🚀 Extreme Performance
- **Rust-Powered Core**: Utilizing a custom `log_engine_rs` extension and `rayon` for parallel processing.
- **Multi-threaded**: Background processing ensures the UI never freezes, even when loading 1GB+ files.
- **Zero-Copy Loading**: Optimized memory management for handling tens of millions of lines.

### 🔍 Advanced Analysis
- **Powerful Filtering**: Support for Include (positive) and Exclude (negative) filters, Regex patterns, and instant toggling.
- **Multi-Log Merging**: Seamlessly load and merge multiple log files into a single, time-sorted view.
- **Interactive Timeline**: A density heatmap timeline to visualize event clusters and quickly navigate through time.
- **Smart Search**: Find history, regex support, and cross-file searching capabilities.

### 🛠️ Developer Friendly
- **Integrated Notes**: Annotate specific lines and export findings to Text or JSON.
- **TAT Support**: Fully compatible with `TextAnalysisTool.NET` filter files (`.tat`).
- **Modern UI**: Dark mode support, intuitive sidebar, and customizable syntax highlighting.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.6 or higher
- Tkinter (usually included with Python)
- *Optional*: `tkinterdnd2` for drag-and-drop support.

### Running the Application

**GUI Mode:**
Simply run the main script to launch the interface:
```bash
python loganalyzer.py
```

**Command Line (CLI):**
Log Analyzer supports robust CLI arguments for automation and quick access:

```bash
# Open a single log file
python loganalyzer.py app.log

# Open multiple log files (supports wildcards)
python loganalyzer.py logs/*.log

# Load a specific filter set on startup
python loganalyzer.py app.log -f my_filters.tat

# Load a list of files from a text file
python loganalyzer.py @file_list.txt
```

---

## 📖 Documentation

For a comprehensive guide on all features, keyboard shortcuts, and advanced configuration, please consult the full documentation:

👉 **[Read the Complete User Manual](Doc/Log_Analyzer_Docs_EN.md)**

---

## 📦 Version History

- **v1.7**: Multi-Log Management, Merged View, and Enhanced Search.
- **v1.6**: Introduction of the Rust Core Engine.
- **v1.5**: Performance overhaul and Zero-Copy loading.
- **v1.4**: Interactive Event Timeline and Dark Mode.

*(See [Release Notes](Doc/Log_Analyzer_Docs_EN.md#5-release-notes) for full history)*