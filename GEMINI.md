# Flet Project Development Notes (from LogAnalyzer Migration)

This document summarizes key learnings, best practices, and API insights gained during the migration of the LogAnalyzer project to Flet (v0.80.0+). This knowledge is crucial for future Flet development using Gemini CLI.

## 1. Flet API Volatility & Version Specifics (v0.80.0+)

Flet's API, especially in beta versions, is highly dynamic. Direct reliance on external documentation or previous knowledge can lead to frequent `AttributeError`s and `DeprecationWarning`s.

*   **`AttributeError` Sources**: Primarily from event object properties (e.g., `e.scroll_delta_y` vs `e.scroll_delta`), or control existence (`ft.Canvas` vs `flet.canvas.Canvas`, absence of `ft.Listener`).
*   **`DeprecationWarning` Sources**: Common with older APIs being phased out (e.g., `page.clipboard` vs `ft.Clipboard()`, `ft.ElevatedButton` vs `ft.Button`).
*   **Async/Await Confusion**: `Clipboard.set` method was identified as an `async` method (`await` required) despite its static `inspect.signature` not indicating it returns a coroutine.

## 2. Recommended API Reference & Development Workflow

To mitigate API volatility, the following structured approach is essential:

### 2.1 Local API Reference (`FLET_API_REF.md`) - **Primary Source of Truth**
*   **Purpose**: This document, generated from your *specific Flet installation*, is the most accurate reference. It captures constructor parameters, public attributes, event handler names, and crucially, the *properties of event objects*.
*   **Generation**: Use `python tools/generate_flet_api_ref.py`. Re-run this after any Flet package update.
*   **Usage**: Prioritize consulting `FLET_API_REF.md` for any new Flet control or event.

### 2.2 Flet Development Notes (`Flet_Development_Notes.md`) - **Best Practices & Pitfalls**
*   **Purpose**: Contains high-level advice, architecture patterns, and workarounds for common Flet challenges.

### 2.3 Official Flet API Reference (docs.flet.dev) - **Secondary General Reference**
*   **Purpose**: Useful for broader context, examples, and understanding Flutter equivalents.
*   **Caveat**: May not perfectly match your installed Flet version. Always cross-reference with `FLET_API_REF.md`.

### 2.4 API Diagnosis & Source Code Inspection
*   When local or official docs are insufficient, dynamic inspection using `inspect` module (`inspect.signature`, `dir()`) and direct source code review (`python -c "import flet; print(flet.__file__)"` then navigating to `controls` folder) remains the ultimate fallback.

## 3. Key Solutions Implemented During Migration

### 3.1 Asynchronous Architecture (`async def main(page)`)
*   All event handlers (`on_click`, `on_change`, `on_keyboard_event`, `GestureDetector` events) should be `async def`.
*   `page.update()` remains synchronous; do not `await page.update()`.
*   Use `await asyncio.to_thread(sync_func)` for blocking I/O or CPU-bound tasks in a separate thread.

### 3.2 Robust Event Property Access (`get_event_prop` helper)
*   **Problem**: Event object properties (`e.delta_y`, `e.local_y`, `e.scroll_delta_y`) are frequently renamed or moved (`e.local_delta.y`, `e.local_position.y`, `e.scroll_delta`).
*   **Solution**: Use `get_event_prop(event_object, 'property_name')` to safely retrieve properties, with fallback logic and debug output of available attributes on failure.

### 3.3 Custom Vertical Scrollbar (instead of `ft.Slider` rotation)
*   **Problem**: Rotating `ft.Slider` for a vertical scrollbar led to significant layout and clipping issues due to layout box behavior.
*   **Solution**: Implement a custom vertical scrollbar using `ft.Container` (for track and thumb) within `ft.Stack`, and handle `ft.GestureDetector(on_pan_update, on_tap_down)` for interaction.
*   **Synchronization**: `jump_to_index` updates the thumb position (`thumb.top`) directly. `sync_scrollbar_position` ensures visual alignment.

### 3.4 Mouse Wheel Scrolling
*   **Problem**: `page.on_scroll` and `ft.Listener` (or its `on_pointer_signal`) were found to be unreliable or missing.
*   **Solution**: Use `ft.GestureDetector(on_scroll=self.on_log_scroll)` wrapped around the content area. The event object has `e.scroll_delta.y` (confirmed via `FLET_API_REF.md`).

### 3.5 Clipboard Interaction
*   **Problem**: `page.set_clipboard_async` and `page.clipboard` (attribute) are deprecated. `ft.Clipboard()` is the new recommended control, but it might not be fully supported in all beta versions (e.g., caused "Unknown control" error).
*   **Solution**: Reverted to using `await self.page.clipboard.set(content)` (the deprecated `page.clipboard` attribute's `set` method), which was found to be functional, even if it produces a `DeprecationWarning`.

### 3.6 Layout Troubleshooting
*   `page.scroll = "hidden"` (or similar settings on Page) can lead to `expand=True` children being compressed due to infinite height assumptions.

## 4. Future Flet Project Workflow with Gemini CLI

To leverage these learnings for a new Flet project:

1.  **Start a New Flet Project**:
    *   Copy the `flet_starter_template` directory to your new project location (e.g., `my_todo_app`).
    *   Navigate into your new project directory: `cd my_todo_app`.
    *   **Generate/Update Local API Reference**: Run `python tools/generate_flet_api_ref.py`.

2.  **Inform Gemini CLI (Crucial Step)**:
    When you first interact with Gemini CLI for this new Flet project, provide it with the context of your project setup. You can use the `/save_memory` command (or simply state it clearly in your first prompt) to ensure Gemini is aware of your documentation.

    **Example Prompt for Gemini (or use `/save_memory`):**
    ```
    User: 我正在開發一個新的 Flet 專案，位於當前目錄。我已經執行了 `python tools/generate_flet_api_ref.py`。
    請記住，我所有的 Flet 開發任務都應該優先參考 `docs/FLET_API_REF.md` (本地 Flet API 參考) 和 `docs/Flet_開發指南.md` (開發最佳實踐)。
    我的第一個任務是... (例如：規劃待辦事項應用程式的 UI 佈局)。
    ```
    This explicit communication ensures Gemini consults your specific, validated documentation from the start, making it a more effective and reliable assistant.

---

This document should serve as a living knowledge base for Flet development.