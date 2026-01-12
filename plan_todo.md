# LogAnalyzer Qt 現代化改進計畫 (plan_todo.md)

本文件列出了提升 LogAnalyzer 使用者體驗 (UX) 與視覺美感 (UI) 的具體改進項目。

---

## 🟢 階段一：視覺一致性與基礎 UX (優先處理)

### 1. 對話框現代化 (Modern Dialogs)
- [x] **建立 `ModernDialog` 基底類別**：
    - [x] 支援 `Qt.FramelessWindowHint` 無邊框模式。
    - [x] 整合與主視窗一致的 `CustomTitleBar` (標題、關閉按鈕、拖曳功能)。
    - [x] 實現深淺色主題自動切換。
- [x] **重構現有對話框**：
    - [x] `FilterDialog`：套用 `ModernDialog` 架構。
    - [x] `GoToLineDialog`：套用 `ModernDialog` 架構。
    - [x] `ShortcutDialog` / `AboutDialog`：統一視覺風格。
- [x] **主視窗模態遮罩 (Dimmer)**：
    - [x] 在彈出對話框時，將主視窗背景變暗，強化焦點感。

### 2. 搜尋功能優化 (Search Overlay)
- [ ] **懸浮搜尋列 (Floating Search Bar)**：
    - [ ] 將搜尋列改為懸浮在日誌檢視區右上角，不再推擠內容佈局。
    - [ ] 加入圓角、陰影與微小的淡入淡出動畫。
- [ ] **快速捷徑優化**：
    - [ ] 在搜尋列顯示時，按下 `Esc` 僅關閉搜尋列而不清除目前的選取項。

---

## 🟡 階段二：功能性視覺增強 (進階)

### 3. Scrollbar 熱點圖 (Heatmap/Minimap)
- [ ] **搜尋結果可視化**：
    - [ ] 在垂直捲軸背景或旁邊，繪製搜尋匹配項的色塊分佈。
- [ ] **過濾器命中心跳圖**：
    - [ ] (選配) 在捲軸區域顯示不同顏色過濾條件的命中分佈。

### 4. 狀態列與互動性 (Interactive Status Bar)
- [ ] **點擊導向**：
    - [ ] 點擊「總行數」區域 -> 直接開啟 `Go To Line`。
    - [ ] 點擊「過濾器狀態」 -> 快速切換 `Show Filtered Only`。
- [ ] **繁忙指示 (Loading Spinner)**：
    - [ ] 在 Rust 背景處理大檔案或複雜過濾時，顯示小型的動畫指示器。

### 5. 通知系統升級 (Toast Stacking)
- [x] **訊息堆疊**：支援同時顯示多條通知（例如連續儲存多個檔案時）。
- [x] **狀態視覺化**：為 Info, Success, Warning, Error 加入不同的邊框色或圖示。

---

## 🔵 階段三：深度分析與細節優化

### 6. 日誌渲染增強 (Advanced Delegates)
- [ ] **語法高亮 (Structural Highlighting)**：
    - [ ] 自動偵測並高亮 `key=value` 或 `{"json": true}` 結構。
- [x] **行號區塊互動**：
    - [x] 調整行號區塊背景色，使其與內容區有細微區分（參考 VS Code 裝訂線）。
    - [x] 支援點擊行號區域選取整行。

### 7. Activity Bar 精緻化
- [ ] **通知徽章 (Badges)**：
    - [ ] 在 Filter 圖標上顯示目前啟用的過濾器數量。
    - [ ] 在 Notes 圖標上顯示目前檔案的筆記總數。

---

## 📝 備註
- 修改時應嚴格遵守 `apply_theme` 的色彩定義。
- 優先確保效能，特別是在處理百萬行等級的 Log 時，UI 渲染不可造成卡頓。
