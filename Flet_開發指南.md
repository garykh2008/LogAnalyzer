# Flet 開發指南 (基於 Flet 1.0 Beta - 0.80.0+)

本指南旨在為使用 Gemini CLI 進行 Flet 專案開發提供一套標準化的方法和最佳實踐，以避免常見的 API 兼容性問題和提高開發效率。

---

## 1. 專案初始化與結構

本範本提供了一個推薦的 Flet 專案結構：

```
your_flet_project/
├── docs/
│   ├── FLET_API_REF.md           # 本地 Flet 版本生成的 API 參考
│   ├── Flet_Development_Notes.md # 開發經驗筆記
│   └── Flet_開發指南.md            # 本文件
├── tools/
│   └── generate_flet_api_ref.py  # 用於更新 FLET_API_REF.md
├── my_app.py                     # 你的主應用程式檔案
└── README.md
```

**初始化新專案：**
1.  複製 `flet_starter_template` 目錄。
2.  進入新目錄，運行 `python tools/generate_flet_api_ref.py` 以確保 `FLET_API_REF.md` 反映當前 Flet 環境。

---

## 2. API 查詢與驗證流程 (核心原則)

Flet Beta 版本的 API 變動頻繁，嚴格遵循以下流程至關重要：

1.  **優先查閱本地 `FLET_API_REF.md`**：
    *   這是最準確的 API 來源，它反映了你當前安裝的 Flet 版本。
    *   查詢控制項的 Constructor Parameters、Public Attributes、Events 及其 Event Object Details。
    *   **示例**：要了解 `ft.GestureDetector` 的 `on_scroll` 事件，先查 `FLET_API_REF.md` 中 `GestureDetector` 下的 `on_scroll` 事件，然後再查 `Event Object Details` 中的 `ScrollEvent`。

2.  **參考官方 API 文件 (`https://docs.flet.dev/api-reference/`)**：
    *   作為第二參考來源，它通常提供更詳細的範例和說明。
    *   **注意**：官方文件可能與你的本地版本存在輕微差異，最終以本地 `FLET_API_REF.md` 為準。

3.  **使用 `inspect` 進行即時診斷**：
    當遇到 `AttributeError` 或 API 行為不明時，直接在 Python 腳本中運行 `inspect` 進行動態檢查。
    ```python
    import flet as ft
    import inspect
    print(inspect.signature(ft.SomeControl))
    print(dir(ft.SomeControl))
    ```
    對於事件物件，可以在事件處理函數中加入 `print(dir(e))` 來查看實際屬性。

4.  **避免使用 Deprecated API**：
    如果 `FLET_API_REF.md` 或控制台輸出顯示 `DeprecationWarning`，應優先使用建議的替代方案。

---

## 3. 核心開發最佳實踐

### 3.1 非同步 (Async/Await)

*   **啟動**：主函數 `main` 必須是 `async def main(page: ft.Page)`。
*   **執行**：使用 `ft.run(main)` (推薦用於腳本) 或 `ft.app(target=main)` (推薦用於打包應用)。
*   **事件處理**：所有綁定到控制項的事件處理函數 (`on_click`, `on_change` 等) 都應該是 `async def`。
*   **長時間任務**：對於可能阻塞 UI 的任務（如檔案讀寫、網路請求），使用 `await asyncio.to_thread(sync_function, *args)` 來在單獨的執行緒中運行同步代碼。
*   **UI 更新**：
    *   `page.update()` **不需要** `await`。
    *   `await asyncio.sleep(0)` 可以在需要時讓出 CPU，允許 Flet 刷新 UI。

### 3.2 佈局 (Layout)

*   **`expand=True`**：確保父容器有明確的尺寸，否則 `expand=True` 的子元素可能無法正確佈局。
*   **`page.scroll`**：避免在 `page` 上設定 `scroll` 模式，特別是 `hidden`，它可能會干擾 `expand=True` 的行為，導致「height is unbounded」錯誤或壓縮佈局。
*   **`Alignment` 常數**：使用 `ft.Alignment(x, y)` 替代 `ft.alignment.TOP_LEFT` 等舊常數。

### 3.3 事件處理

*   **事件屬性**：始終透過 `e.屬性` 存取。如果不明確，先查 `FLET_API_REF.md` 的 Event Object Details。
*   **`get_event_prop` 輔助函數**：在關鍵的事件處理器中，可以繼續使用我們之前開發的 `get_event_prop` 函數來保護對事件屬性的存取，並提供除錯資訊。

### 3.4 自定義捲軸 (Custom Scrollbar)

*   對於虛擬列表，由於原生捲軸無效，手動建立 `ft.Container` (Track) 和 `ft.Container` (Thumb) 並使用 `ft.GestureDetector` (on_pan_update, on_tap_down) 處理交互是標準做法。
*   `on_scroll` (用於 `GestureDetector`)：這是捕捉滑鼠滾輪事件的推薦方法，傳遞的事件物件是 `ScrollEvent`，其滾動量為 `e.scroll_delta.y` (或 `e.scroll_delta` 如果它是 float)。

---

## 4. Rust 擴充整合

*   確保 `log_engine_rs.pyd` 在 Python 的 `sys.path` 中可被找到。
*   如果 Rust 函式是同步且耗時的，考慮使用 `await asyncio.to_thread(sync_rust_function, *args)` 來避免阻塞 UI。

---

## 5. 持久化設定

*   使用 Python 標準庫或 `inifile` 模組來保存用戶設定、過濾器列表、視窗大小等。

---

希望這份指南能幫助你在未來的 Flet 專案中更加順利！
