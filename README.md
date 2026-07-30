# Log Analyzer V3.0 (Tauri Release)

Log Analyzer is a lightweight, ultra-high-performance diagnostic log viewer, filtering, and annotation tool. Built on Vite + React + Rust (Tauri v2), it delivers seamless handling of massive log files (100M+ lines) with fluid scrolling and instant search.

---

## Features

*   **Virtual Rendering Viewport**: Renders only the visible subset of lines, enabling zero-lag scrolling through multi-gigabyte log files.
*   **Multi-encoding Support**: Auto-detects file encoding (UTF-8, UTF-16, GBK, Big5, Shift_JIS, EUC-JP, Windows-1252) via BOM and content sampling — no manual encoding selection needed.
*   **Highlight & Exclude Filters**:
    *   Highlight keywords with customizable text/background colors and automatic contrast adjustment for dark/light themes.
    *   Filter out noise by excluding matching lines dynamically in Filter Mode.
    *   Reorder filters with drag-and-drop in the sidebar.
    *   Import/export filters in `.tat` format (Text Analysis Tool compatible).
*   **Search**: Regex and case-sensitive/plain-text search with F3/F2 navigation. Search results are automatically filtered to match the current Filter Mode.
*   **Annotated Notes**:
    *   Press `C` to bind notes to specific lines.
    *   Notes are saved in a JSON-based `.note` file next to the log path.
    *   Export notes to a plain-text summary file.
*   **Multi-file Tabs**: Open multiple log files simultaneously and switch between them via the sidebar file list.
*   **Clipboard & Drag-and-Drop**: Paste text (Ctrl+V) to instantly open clipboard content as a new tab, or drag-and-drop log files onto the window.
*   **Recent Files & Cascading Menus**: Open recent paths from the File menu, persisted in local storage.
*   **Frameless Titlebar**: Custom-drawn titlebar with native drag regions, matching the OS window chrome.

---

## Getting Started

### Prerequisites

*   **Node.js**: v18 or later
*   **Rust**: Stable toolchain (via rustup)

### Installation

1. Install dependencies:
   ```bash
   npm install
   ```

2. Development mode:
   ```bash
   npm run tauri dev
   ```

3. Production build:
   ```bash
   npm run tauri build
   ```

   Binaries are output to `src-tauri/target/release/bundle/`.

---

## Keyboard Shortcuts

| Shortcut | Action |
| :--- | :--- |
| `Ctrl + O` | Open Log File |
| `Ctrl + S` | Save Notes |
| `Ctrl + G` | Go to Line |
| `Ctrl + F` | Toggle Search Box |
| `Ctrl + H` | Toggle Filter Mode |
| `Ctrl + V` | Paste Clipboard as New Tab |
| `Ctrl + C` | Copy Selected Lines |
| `Ctrl + Shift + L` | Toggle Log Files Panel |
| `Ctrl + Shift + F` | Toggle Filters Panel |
| `Ctrl + Shift + N` | Toggle Notes Panel |
| `F3` / `F2` | Search Next / Previous Match |
| `Ctrl + Right` / `Left` | Navigate Filter Hits |
| `C` | Add/Edit Note |
| `Delete` | Remove Note |
| `H` | Keyboard Shortcuts Dialog |
| `Arrow Up` / `Down` | Navigate Lines |
| `Page Up` / `Page Down` | Page Navigation |
| `Home` / `End` | Jump to Top / Bottom |

---

## Architecture

*   **Frontend**: React 19 + TypeScript, Zustand for state management, Tailwind CSS v4 for styling
*   **Backend**: Rust with Tauri v2, Rayon for parallel search/filter, memmap2 for zero-copy file access
*   **Packaging**: Single-file installer (Windows NSIS) or portable archive via `npm run tauri build`

---

## License

© 2026 LogAnalyzer Team. All rights reserved.
