# Flet 1.0 Beta (0.80.0+) 開發實戰指南

本指南整合了 Flet 1.0 Beta 的官方規範與 **LogAnalyzer 遷移專案** 中的實戰經驗，旨在解決 API 不穩定、效能瓶頸及佈局衝突等核心問題。

---

## 1. API 規範與診斷流程

### 1.1 核心規範
*   **啟動方式**：使用 `ft.run(main)`。
*   **列舉常數**：全面大寫（如 `ft.Icons.ADD`, `ft.Colors.BLUE`, `ft.FontWeight.BOLD`）。
*   **對齊方式**：直接實例化 `ft.Alignment(-1, 0)` 或使用 `ft.MainAxisAlignment`。
*   **非同步化**：事件處理器必須是 `async def`。注意 `focus()` 在此版本也是 `async`。

### 1.2 診斷三部曲
當遇到 `AttributeError` 或行為不明時，嚴格執行：
1.  **查閱本地 `FLET_API_REF.md`**：反映當前環境最真實的簽名。
2.  **動態反射檢查**：
    ```python
    print(inspect.signature(control.__init__))
    print(dir(event_object))
    ```
3.  **源碼審查**：`python -c "import flet; print(flet.__file__)"` 進入目錄查看 `.py` 實作。

---

## 2. 效能優化：Render Loop 模式

### 2.1 捲動延遲問題
高頻事件（如 `on_scroll`）若直接呼叫 `page.update()`，會導致 Python 與 Client 之間的通訊塞車，造成畫面「久久才更新」。

### 2.2 解決方案：30 FPS 渲染迴圈
不要在事件中更新 UI，只更新資料狀態，由背景迴圈統一渲染。
```python
async def render_loop(self):
    while True:
        if self.needs_render or self.current_idx != self.target_idx:
            self.update_ui_logic() # 更新屬性
            self.page.update()     # 統一傳送變更
            self.needs_render = False
        await asyncio.sleep(0.033) # 限制在 30 FPS
```

---

## 3. 焦點管理：Focus Trap 技術

### 3.1 焦點被搶奪現象
側邊欄（Sidebar）若包含 `Checkbox` 或 `ListView`，按下方向鍵時焦點會自動落在列表上，導致全域鍵盤導覽失效。

### 3.2 解決方案：隱形焦點陷阱
在頁面中加入一個 0x0 像素、不可見但具備焦點能力的 `TextField`。
```python
self.focus_trap = ft.TextField(width=0, height=0, opacity=0)
# 在任何側邊欄互動後強行奪回焦點
await self.focus_trap.focus()
```

---

## 4. 佈局與渲染攻堅

### 4.1 虛擬列表高度精確化
*   **問題**：動態計算文字高度會產生累積誤差，導致 Resize 後底部被裁切。
*   **解決**：將每一行包在固定高度（如 `height=20`）的 `ft.Container` 中。
*   **公式**：`LINES_PER_PAGE = int(available_height / 20)`。

### 4.2 解決「顏色改不動」的緩存問題
*   **現象**：修改 `Container.bgcolor` 並 `update()` 後畫面無反應。
*   **解決：組件重建 (Component Reconstruction)**。
    ```python
    # 重新建立一個實例並替換 controls 列表中的對象
    new_comp = create_component(new_color)
    self.page.controls[0].controls[0] = new_comp
    self.page.update()
    ```

---

## 5. 智慧色彩與主題 (Smart Contrast)

### 5.1 亮度偵測
為了確保搜尋高亮在不同背景下清晰，需計算背景亮度。
```python
def get_luminance(hex_str):
    rgb = hex_to_rgb(hex_str)
    return (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255.0
```
*   **Luminance > 0.6**：使用深色高亮（藍底白字）。
*   **Luminance < 0.6**：使用淺色高亮（黃底黑字）。

### 5.2 主題切換清單
切換 Dark/Light Mode 時應同步更新：
*   所有自定義容器的 `bgcolor`。
*   `MenuBar` 的 `style.bgcolor`。
*   Windows 原生標題列 (`ctypes` 同步)。
*   重新繪製 `Canvas` 內容。

---

## 6. 混合模式 (Mixed Mode)

### 6.1 處理 Beta 版 Bug
若 Flet 原生 `FilePicker` 在目前環境報出 `Unknown control`，應果斷切換至 **Tkinter 備案**：
```python
def pick_file_sync():
    root = tk.Tk(); root.withdraw()
    path = filedialog.askopenfilename()
    root.destroy(); return path

# 務必使用 to_thread 避免阻塞事件循環
path = await asyncio.to_thread(pick_file_sync)
```

---

## 7. 持久化與資料處理
*   **TAT 檔案解析**：支援 XML 格式，需處理標籤大小寫不一及屬性名稱變體（`exclude` vs `excluding`）。
*   **配置儲存**：在 `on_window_event` 的 `close` 事件中自動呼叫 `save_config()`。
