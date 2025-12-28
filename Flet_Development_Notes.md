# Flet 開發實戰經驗筆記 (Windows 平台)

## 1. Flet 1.0 Beta (0.80.0+) API 規範與變遷
Flet 0.80.0 引進了大量架構變動，以下是確保無警告且穩定執行的關鍵：

*   **啟動方式**：使用 `ft.run(main)` 取代舊有的 `ft.app(target=main)`。
*   **大寫列舉 (Enums)**：全面使用大寫開頭的常量（如 `ft.Icons`, `ft.Colors`, `ft.FontWeight`）。
*   **分頁重構 (重要)**：0.80.0 移除了 `ft.Tab` 的 `content` 參數。現在必須採用「三位一體」架構：
    *   `ft.Tabs`：控制器，需指定 `length` 與 `content`。
    *   `ft.TabBar`：導航條，放置 `ft.Tab` 標籤。
    *   `ft.TabBarView`：內容區，放置分頁內容。
    *   *佈局提示*：`TabBarView` 必須設定 `expand=True` 且放在有邊界的容器內，否則會觸發 "height is unbounded" 錯誤。

## 2. API 診斷與原始碼審查流程
當遇到 `TypeError: ... got an unexpected keyword argument` 或官方文件與環境不符時，應依序執行以下步驟：

1.  **反射檢查 (Inspection)**：
    ```python
    import flet as ft
    import inspect
    print(inspect.signature(ft.Tabs.__init__)) # 檢查建構子參數
    print(dir(ft.Tabs)) # 檢查可用屬性
    ```
2.  **定位原始碼**：
    `python -c "import flet; print(flet.__file__)"`
3.  **直接審查原始碼**：
    進入 `flet/controls/material/` 等目錄讀取 `.py` 檔案。這是獲取 100% 正確 API 用法的最終手段（0.80.0 的 `tabs.py` 清楚記錄了所有參數變動）。

## 3. 核心技術：解決 UI 凍結與同步問題
在 0.80.0 桌面模式下，背景執行緒會失去主動推送 UI 更新的能力。

*   **解決方案：非同步 (Async/Await)**：使用 `async def main(page)`。
*   **更新陷阱**：在 0.80.0 中，**`page.update()` 依然是同步函數**。
    *   ✅ 正確：`page.update()`
    *   ❌ 錯誤：`await page.update()` (會導致 `TypeError`)
*   **阻塞任務**：使用 `await asyncio.to_thread(func)` 處理 `subprocess` 或檔案 IO，確保 UI 響應。

## 4. Windows 系統交互 (檔案選取與焦點置頂)
由於 **Flet 1.0 Beta 尚未原生支援外部檔案拖入**（`on_drop` 僅限內部），因此需採用 **PowerShell 混合模式**。

### PowerShell 混合選取器技巧：
*   **獲取本地路徑**：呼叫 `System.Windows.Forms.OpenFileDialog`。
*   **強行置頂 (Foreground)**：
    *   建立隱藏的 `TopMost` Form。
    *   在彈出前模擬 `Alt` 鍵 (`SendWait('%')`) 繞過焦點鎖定。
*   **LogAnalyzer 啟動**：使用 `Start-Process` 並搭配陣列傳參 `@(arg1, arg2...)` 處理空格路徑。

## 5. 設定持久化 (INI Config)
*   **路徑處理**：存入 INI 時 `wrap` 雙引號，讀取時 `strip('"')`，確保跨環境路徑一致性。
*   **持久化狀態**：Checkbox 狀態與路徑應在變更後立即更新 INI。
