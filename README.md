# Log Analyzer V3.0 (Tauri Release)

Log Analyzer is a lightweight, ultra-high-performance diagnostic log viewer, filtering, and annotation tool. Originally built on PySide6 (Qt) and modernized under a Vite + React + Rust (Tauri v2) architecture, this release delivers seamless handling of massive log files (100M+ lines) with fluid scrolling and instant search indexes.

---

## 🚀 Key Features

*   **Virtual Rendering Viewport**: Renders only the visible subset of lines, enabling zero-lag scroll interactions through multi-gigabyte log files.
*   **Highlight & Exclude Filters**: 
    *   Highlight keywords with customizable text presets and automatic contrast adjustment for dark/light themes.
    *   Filter-out noise by excluding matching logs dynamically in Filter Mode.
    *   Reorder filters seamlessly using a custom mouse-drag event handler.
*   **Annotated Notes Persistence**: 
    *   Double-click to create highlight filters, or press `C` to bind notes to specific lines.
    *   Notes are saved in a simple JSON-based `.note` file next to the log path.
*   **Cascading Menus & Recent History**: 
    *   Open recent file paths from a cascading list in the File dropdown, persisted in local storage.
    *   Quickly save notes, import/export filters, and jump to lines.
*   **Modern Titlebar & Window Controls**: Uses native OS capability drag regions on a gorgeous frameless dashboard with stacked toasts and modal dialogs.

---

## 🛠️ Getting Started

### Prerequisites

*   **Node.js**: v18 or later
*   **Rust**: Stable rustc compiler (Cargo)

### Installation

1. Install npm dependencies:
   ```bash
   npm install
   ```

2. Run in Development Mode:
   ```bash
   npm run tauri dev
   ```

3. Build production binaries:
   ```bash
   npm run tauri build
   ```

---

## ⌨️ Global Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + O` | Open Log File |
| `Ctrl + S` | Quick Save Notes |
| `Ctrl + G` | Go to Line |
| `Ctrl + F` | Toggle Search Box |
| `Ctrl + H` | Toggle Show Filtered Mode |
| `F3` / `F2` | Search Next / Prev Match |
| `Ctrl + Right` / `Left` | Navigate Filter Hits |
| `C` | Add/Edit Note |
| `Delete` | Remove Note |
| `H` | View Keyboard Shortcuts dialog |
