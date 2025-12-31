import flet as ft
import flet.canvas as cv # Import canvas module explicitly
import os
import sys
import time
import asyncio
import json
import re
import warnings
import threading
import tkinter as tk
from tkinter import filedialog

# 隱藏 Flet 1.0 的過期警告
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Add current directory to sys.path to ensure we can load the Rust module
sys.path.append(os.getcwd())

# ... (Previous imports and helper functions remain)

# --- Rust Extension Import ---
# 確保能從當前目錄載入 Rust pyd/so
sys.path.append(os.getcwd())

class ThemeColors:
    """Centralized color definitions for the application."""
    # Dark Mode - High Contrast Layering
    DARK = {
        "sidebar_bg": "#1E1E1E",     
        "log_bg": "#000000",         
        "top_bar_bg": "#333333",     
        "text": "#E0E0E0",           
        "scroll_track": "#000000",
        "scroll_thumb": "#444444",
        "divider": "#333333",
        "input_bg": "#333333",
        "selection_bg": "#264F78",
        "line_error": "#F44336",
        "line_warn": "#FFEB3B",
        "line_info": "#2196F3",
        "line_default": "#E0E0E0",
        "status_bg": "#005A9E",      # 專業深藍
        "status_text": "#FFFFFF",    # 白色文字
        "search_bg": "#2D2D2D",
    }
    
    # Light Mode - Paper & Ink Contrast
    LIGHT = {
        "sidebar_bg": "#F5F5F5",     
        "log_bg": "#FFFFFF",         
        "top_bar_bg": "#E0E0E0",     
        "text": "#202124",
        "scroll_track": "#FFFFFF",
        "scroll_thumb": "#CCCCCC",
        "divider": "#D0D0D0",
        "input_bg": "#F1F3F4",
        "selection_bg": "#E8F0FE",
        "line_error": "#D93025",
        "line_warn": "#F9AB00",
        "line_info": "#1A73E8",
        "line_default": "#202124",
        "status_bg": "#E1F5FE",      # 極淺藍色
        "status_text": "#005A9E",    # 深藍色文字
        "search_bg": "#F1F3F4",
    }
    
    @staticmethod
    def get(mode):
        # Handle ThemeMode Enum or string
        m = str(mode).split(".")[-1].lower()
        return ThemeColors.DARK if m == "dark" else ThemeColors.LIGHT

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    if not hex_str: return (0, 0, 0)
    if len(hex_str) == 3: hex_str = "".join(c*2 for c in hex_str)
    try:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    except: return (0, 0, 0)

def get_luminance(hex_str):
    rgb = hex_to_rgb(hex_str)
    return (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255.0

def adjust_color_for_theme(hex_color, is_background, is_dark_mode):
    """
    Dynamically adjusts filter colors for Dark Mode to prevent jarring contrast.
    Ported from loganalyzer.py.
    """
    if not hex_color: return hex_color
    hex_color = hex_color.strip().lower()
    if not hex_color.startswith("#"): hex_color = "#" + hex_color

    if not is_dark_mode:
        return hex_color

    # 1. Handle Defaults
    if is_background and (hex_color == "#ffffff" or hex_color == "#fff"):
        return "#1e1e1e" # Match dark theme bg
    if not is_background and (hex_color == "#000000" or hex_color == "#000"):
        return "#d4d4d4" # Match dark theme text

    # 2. Smart Adjustment based on Luminance
    rgb = hex_to_rgb(hex_color)
    lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255.0

    if is_background and lum > 0.4: # Too bright for dark mode bg
        return '#{:02x}{:02x}{:02x}'.format(*tuple(int(c * 0.25) for c in rgb))
    if not is_background and lum < 0.5: # Too dark for dark mode text
        return '#{:02x}{:02x}{:02x}'.format(*tuple(int(c + (255 - c) * 0.6) for c in rgb))

    return hex_color

def get_event_prop(event, prop_name, default=None):
    """
    Safely access event properties with fallback and debug info.
    Helps resolve API differences between Flet versions.
    """
    # 1. Direct access
    if hasattr(event, prop_name):
        return getattr(event, prop_name)
    
    # 2. Common Aliases / Fallbacks for 0.80.0+
    aliases = {
        'delta_y': ['delta', 'scroll_delta', 'local_delta'], # Added local_delta
        'local_y': ['local_position'],       # local_position is Offset
        'global_y': ['global_position']
    }
    
    if prop_name in aliases:
        for alias in aliases[prop_name]:
            if hasattr(event, alias):
                val = getattr(event, alias)
                # Handle Offset objects (local_position, etc.)
                if prop_name.endswith('_y') and hasattr(val, 'y'):
                    return val.y
                if prop_name.endswith('_x') and hasattr(val, 'x'):
                    return val.x
                # If expecting a scalar but got scalar (e.g. scroll_delta)
                return val

    # 3. Last Resort: Inspect and Debug
    
    return default

class MockLogEngine:
    """Fallback engine when Rust extension is missing."""
    def __init__(self, path):
        self.path = path
        # 模擬讀取
        self._lines = 1000 # 假裝有 1000 行
        
    def line_count(self):
        return self._lines
        
    def get_line(self, idx):
        return f"Mock Line #{idx} from {os.path.basename(self.path)}"

    def filter(self, filters):
        # filters: List of (text, is_regex, is_exclude, is_event, original_index)
        
        # 簡單模擬：如果 filter text 是 "error"，就只回傳偶數行
        # 回傳格式: (line_tags_codes, filtered_indices, hit_counts, timeline_events)
        
        filtered_indices = []
        line_tags = [0] * self._lines
        hit_counts = [0] * len(filters)
        
        # 模擬一個簡單的過濾邏輯
        has_active_filters = len(filters) > 0
        
        for i in range(self._lines):
            # 這裡簡單全通過，除非有 filter 且內容包含 "error" (模擬)
            # 為了方便測試，我們假設如果沒有 filter 就全顯示
            # 如果有 filter，我們隨機過濾一些
            if not has_active_filters:
                filtered_indices.append(i)
            else:
                # 模擬：只要有 filter，就只顯示 1/3 的行數
                if i % 3 == 0:
                    filtered_indices.append(i)
                    line_tags[i] = 2 # 模擬匹配第一個 filter
                    hit_counts[0] += 1
        
        return (line_tags, filtered_indices, hit_counts, [])

try:
    import log_engine_rs
    # Assign the imported class to a new variable for consistent access
    _REAL_LOG_ENGINE = log_engine_rs.LogEngine
    HAS_RUST = True
    print("Rust Extension Loaded Successfully.")
except ImportError as e:
    _REAL_LOG_ENGINE = MockLogEngine # Fallback
    HAS_RUST = False
    print(f"Failed to load Rust Extension: {e}. Using Mock Engine.")

class Filter:
    def __init__(self, text, fore_color="#000000", back_color="#FFFFFF", enabled=True, is_regex=False, is_exclude=False, is_event=False):
        self.text = text
        self.fore_color = fore_color
        self.back_color = back_color
        self.enabled = enabled
        self.is_regex = is_regex
        self.is_exclude = is_exclude
        self.is_event = is_event
        self.hit_count = 0

    def to_tat_xml(self):
        """Converts filter to TextAnalysisTool XML format."""
        # Simple XML fragment generation
        en = 'y' if self.enabled else 'n'
        reg = 'y' if self.is_regex else 'n'
        exc = 'y' if self.is_exclude else 'n'
        # Remove '#' for TAT color format
        fg = self.fore_color.lstrip('#')
        bg = self.back_color.lstrip('#')
        
        return f'<Filter enabled="{en}" regex="{reg}" exclude="{exc}" foreColor="{fg}" backColor="{bg}">{self.text}</Filter>'


class LogAnalyzerApp:
    def __init__(self, page: ft.Page):
        self.page = page
        
        # --- Flet 1.0+ Window Event Interception ---
        # 1. 使用新版 API 設定攔截
        self.page.window.prevent_close = True
        
        # 2. 綁定事件監聽器 (處理器會在稍後定義)
        self.page.window.on_event = self._on_native_window_event
        
        # 3. 立即強制更新以鎖定屬性
        self.page.update()
        
        # 1. 基礎屬性初始化
        self._init_state_variables()
        
        # 2. 設定載入與視窗預熱 (防閃爍的核心)
        self._init_settings()
        
        # 3. 建立 UI 元件
        self.build_ui()
        
        # 4. 啟動背景任務與事件綁定
        self._init_background_services()
        
        # 5. 準備就緒，揭開視窗
        self.page.window_visible = True
        self.page.update()

    def _init_state_variables(self):
        """初始化 App 內部所有狀態變數。"""
        self.page.title = "LogAnalyzer (Flet Edition)"
        self.page.theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE)
        self.page.dark_theme = ft.Theme(color_scheme_seed=ft.Colors.BLUE)
        self.page.padding = 0
        self.page.spacing = 0
        
        # App 引擎與路徑
        self.log_engine = None
        self.file_path = None
        
        # 滾動與渲染控制
        self.is_programmatic_scroll = False
        self.last_slider_update = 0
        self.last_render_time = 0
        self.target_start_index = 0
        self.needs_render = False
        self.is_updating = False
        
        # 過濾器狀態
        self.filters = []
        self.filters_dirty = False
        self.current_tat_path = None
        self.filtered_indices = None
        self.line_tags_codes = None
        self.show_only_filtered = False
        
        # 搜尋與選擇狀態
        self.search_results = []
        self.current_search_idx = -1
        self.search_query = ""
        self.search_case_sensitive = False
        self.search_wrap = True
        self.selected_indices = set()
        self.selection_anchor = -1
        self.ctrl_pressed = False
        self.shift_pressed = False
        
        # 系統標記
        self.is_closing = False
        self.is_picking_file = False

    def _init_settings(self):
        """載入設定檔並立即套用視窗初始化外觀。"""
        # A. 決定設定檔絕對路徑
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            try:
                base_dir = os.path.dirname(os.path.abspath(__file__))
            except:
                base_dir = os.path.abspath(".")
        
        self.config_file = os.path.join(base_dir, "app_config.json")
        
        # B. 完整預設值（確保即使 config 損壞也能運作）
        self.default_config = {
            "last_log_dir": os.path.expanduser("~"),
            "last_filter_dir": os.path.expanduser("~"),
            "font_size": 12,
            "theme_mode": "dark",
            "recent_files": [],
            "window_maximized": False,
            "main_window_geometry": "1200x800+100+100",
            "note_view_visible": False,
            "sidebar_visible": False,
            "sidebar_position": "left",
            "sash_main_y": 360
        }
        self.config = self.default_config.copy()
        self.load_config()
        
        # C. 立即同步視窗標題與基礎屬性
        self.page.title = "LogAnalyzer (Flet Edition)"
        tm = self.config.get("theme_mode", "dark")
        self.page.theme_mode = ft.ThemeMode.DARK if tm == "dark" else ft.ThemeMode.LIGHT
        self.page.bgcolor = "#252526" if tm == "dark" else "#ffffff"
        
        # 套用視窗幾何與標題列同步
        self.apply_window_geometry()

    def _init_background_services(self):
        """啟動與管理所有背景服務。"""
        # A. 啟動執行緒級別的物理喚醒 (解決 Windows asyncio 睡眠問題)
        try:
            loop = asyncio.get_running_loop()
            def _wakeup_serv():
                while not self.is_closing:
                    try:
                        # 強制喚醒事件迴圈處理掛起的 Pipe/Socket 信號
                        loop.call_soon_threadsafe(lambda: None)
                        time.sleep(0.1)
                    except: break
            
            threading.Thread(target=_wakeup_serv, daemon=True).start()
        except Exception:
            pass

        # B. 啟動協程級別心跳 (主動通訊確保視窗信號 flush)
        async def _heartbeat_serv():
            while not self.is_closing:
                try:
                    # 讀取視窗寬度強制進行一次 IPC 通訊，解決信號積壓
                    _ = self.page.window_width
                    await asyncio.sleep(0.5)
                except: break
        
        asyncio.create_task(_heartbeat_serv())
        asyncio.create_task(self.render_loop())
        
    async def _on_native_window_event(self, e):
        """處理底層視窗事件 (Flet 1.0+ API)。"""
        # 檢查事件類型是否為關閉請求
        # e.type 可能是 Enum 物件，轉為字串比較最安全
        if "close" in str(e.type).lower():
            # 呼叫我們的統一關閉處理邏輯
            await self.handle_app_close(e)

    async def handle_app_close(self, e):
        """
        處理視窗關閉請求。
        檢查是否有未儲存的 Filters，若有則彈出 Flet 對話框詢問。
        """
        # 1. 忽略檔案選擇期間的訊號 (防止遞迴或誤判)
        if self.is_picking_file:
            return

        # 2. 檢查是否需要儲存
        if self.filters_dirty:
            await self.show_unsaved_changes_dialog()
        else:
            self.save_config()
            await self.page.window.destroy()

    async def show_unsaved_changes_dialog(self):
        # 定義對話框回調
        def close_dlg(e):
            self.dialog.open = False
            self.page.update()

        async def on_save(e):
            self.dialog.open = False
            self.page.update()
            # 嘗試儲存
            await self.save_tat_filters()
            # 如果儲存成功 (dirty flag 被清除)，則關閉程式
            if not self.filters_dirty:
                self.save_config()
                await self.page.window.destroy()

        async def on_dont_save(e):
            self.dialog.open = False
            self.page.update()
            # 不儲存直接關閉
            self.save_config()
            await self.page.window.destroy()

        self.dialog = ft.AlertDialog(
            title=ft.Text("Unsaved Changes"),
            content=ft.Text("Filters have been modified. Do you want to save changes?"),
            actions=[
                ft.TextButton("Save", on_click=on_save),
                ft.TextButton("Don't Save", on_click=on_dont_save),
                ft.TextButton("Cancel", on_click=close_dlg),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.show_dialog(self.dialog)

    def load_config(self):
        """強健地載入設定檔。"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.config.update(data)
            except Exception as e:
                print(f"Error loading config: {e}. Using defaults.")

    def save_config(self):
        # Update current geometry to config using Flet 1.0 window APIs
        try:
            # page.window_width/height are available in 1.0
            w = int(self.page.window_width)
            h = int(self.page.window_height)
            
            # Use window object properties safely
            x = int(self.page.window_left) if self.page.window_left is not None else 0
            y = int(self.page.window_top) if self.page.window_top is not None else 0
            
            self.config["main_window_geometry"] = f"{w}x{h}+{x}+{y}"
            
            # Save theme and directory states
            self.config["theme_mode"] = "dark" if self.page.theme_mode == ft.ThemeMode.DARK else "light"
            
            # window_maximized is no longer a direct Page attribute, 
            # we check the window property if available
            self.config["window_maximized"] = getattr(self.page, "window_maximized", False)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4)
                f.flush()
                os.fsync(f.fileno()) # Force write to disk
            # print(f"Config saved to {self.config_file}.")
        except Exception as e:
            print(f"Error saving config: {e}")

    def apply_window_geometry(self):
        geo = self.config.get("main_window_geometry", "1200x800+100+100")
        try:
            # Apply Theme Mode first
            target_mode = self.config.get("theme_mode", "dark")
            self.page.theme_mode = ft.ThemeMode.DARK if target_mode == "dark" else ft.ThemeMode.LIGHT
            
            # Sync Native Windows Title Bar
            if sys.platform == "win32":
                import ctypes
                try:
                    # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE
                    win_dark_value = 1 if self.page.theme_mode == ft.ThemeMode.DARK else 0
                    # Try to find our window - simpler approach for now
                    hwnd = ctypes.windll.user32.GetForegroundWindow()
                    if hwnd:
                        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(win_dark_value)), 4)
                except Exception: pass
            
            # Parse Tkinter/X11 geometry string: WxH+X+Y
            match = re.match(r"(\d+)x(\d+)\+(\d+)\+(\d+)", geo)
            if match:
                w, h, x, y = map(int, match.groups())
                self.page.window_width = w
                self.page.window_height = h
                self.page.window_left = x
                self.page.window_top = y
            
            if self.config.get("window_maximized", False):
                self.page.window_maximized = True
        except Exception as e:
            print(f"Error applying window geometry: {e}")

    async def on_window_event(self, e):
        pass

    def _get_colors(self):
        """獲取當前主題模式的顏色表。"""
        return ThemeColors.get(self.page.theme_mode)

    def _build_top_bar(self):
        """建立頂部選單列與標題。"""
        colors = self._get_colors()
        
        # 建立最近檔案子選單
        self.recent_files_submenu = ft.SubmenuButton(
            content=ft.Text("Recent Files"),
            controls=[] 
        )
        self.update_recent_files_menu()

        # 建立主選單列 - 背景與父容器保持一致
        self.menu_bar = ft.MenuBar(
            expand=True,
            style=ft.MenuStyle(
                bgcolor=colors["top_bar_bg"], # 與頂欄容器完全一致
                alignment=ft.Alignment(-1, -1),
                mouse_cursor=ft.MouseCursor.CLICK,
                shadow_color=ft.Colors.TRANSPARENT, # 移除選單自帶陰影
            ),
            controls=[
                ft.SubmenuButton(
                    content=ft.Text("File", weight=ft.FontWeight.W_500),
                    controls=[
                        ft.MenuItemButton(
                            content=ft.Text("Open File..."),
                            leading=ft.Icon(ft.Icons.FOLDER_OPEN, size=18),
                            on_click=self.on_open_file_click
                        ),
                        self.recent_files_submenu,
                        ft.MenuItemButton(
                            content=ft.Text("Load Filters"),
                            leading=ft.Icon(ft.Icons.FILE_OPEN_OUTLINED, size=18),
                            on_click=self.import_tat_filters
                        ),
                        ft.MenuItemButton(
                            content=ft.Text("Save Filters"),
                            leading=ft.Icon(ft.Icons.SAVE, size=18),
                            on_click=self.save_tat_filters
                        ),
                        ft.MenuItemButton(
                            content=ft.Text("Save Filters As..."),
                            leading=ft.Icon(ft.Icons.SAVE_AS, size=18),
                            on_click=self.save_tat_filters_as
                        ),
                        ft.MenuItemButton(
                            content=ft.Text("Exit"),
                            leading=ft.Icon(ft.Icons.EXIT_TO_APP, size=18),
                            on_click=self.exit_app
                        )
                    ]
                ),
                ft.SubmenuButton(
                    content=ft.Text("View", weight=ft.FontWeight.W_500),
                    controls=[
                        ft.MenuItemButton(
                            content=ft.Text("Toggle Sidebar"),
                            on_click=lambda _: self.toggle_sidebar()
                        ),
                        ft.MenuItemButton(
                            content=ft.Text("Toggle Dark/Light Mode"),
                            on_click=self.toggle_theme
                        ),
                        ft.SubmenuButton(
                            content=ft.Text("Sidebar Position"),
                            controls=[
                                ft.MenuItemButton(
                                    content=ft.Text("Left"),
                                    on_click=lambda _: self.change_sidebar_position("left")
                                ),
                                ft.MenuItemButton(
                                    content=ft.Text("Right"),
                                    on_click=lambda _: self.change_sidebar_position("right")
                                ),
                                ft.MenuItemButton(
                                    content=ft.Text("Bottom"),
                                    on_click=lambda _: self.change_sidebar_position("bottom")
                                ),
                            ]
                        ),
                        ft.MenuItemButton(
                            content=ft.Text("Show Filtered Only"),
                            leading=ft.Icon(ft.Icons.FILTER_ALT, size=18),
                            on_click=self.toggle_show_filtered
                        )
                    ]
                )
            ]
        )

        self.app_title_text = ft.Text("LogAnalyzer", weight=ft.FontWeight.BOLD, size=14, color=colors["text"])
        
        # 組裝頂部橫列
        self.top_bar_row = ft.Row([
            ft.Container(
                content=ft.Icon(ft.Icons.ANALYTICS, color=colors["text"], size=20), 
                padding=ft.padding.only(left=15, right=5)
            ),
            self.app_title_text,
            ft.Container(width=15), # 固定的視覺間隔
            self.menu_bar
        ], spacing=0, alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        # 返回封裝好的頂部容器
        return ft.Container(
            content=self.top_bar_row,
            bgcolor=colors["top_bar_bg"],
            padding=0,
            height=45,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=4,
                color=ft.Colors.with_opacity(0.4, ft.Colors.BLACK),
                offset=ft.Offset(0, 2) # 向下投影
            )
        )

    def _build_sidebar(self):
        """建立過濾器側邊欄，支援左/右/下位置。"""
        colors = self._get_colors()
        pos = self.config.get("sidebar_position", "left")
        
        # 根據位置決定寬高
        is_bottom = pos == "bottom"
        sidebar_width = 280 if not is_bottom else None
        sidebar_height = None if not is_bottom else 200

        self.filter_list_view = ft.ReorderableListView(
            expand=True, 
            spacing=2,
            padding=ft.padding.only(top=10),
            on_reorder=self.on_filter_reorder,
        )

        # 在底部模式下，Add Filter 按鈕可以跟標題排在同一行
        self.add_filter_btn = ft.ElevatedButton(
            content=ft.Row(
                [
                    ft.Icon(ft.Icons.ADD, size=16),
                    ft.Text("Add Filter", size=12),
                ],
                spacing=5,
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            height=30,
            on_click=self.on_add_filter_click,
            style=ft.ButtonStyle(
                bgcolor={
                    ft.ControlState.DEFAULT: ft.Colors.BLUE_700 if self.page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLUE_50,
                    ft.ControlState.HOVERED: ft.Colors.BLUE_600 if self.page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLUE_100,
                },
                color={
                    ft.ControlState.DEFAULT: ft.Colors.WHITE if self.page.theme_mode == ft.ThemeMode.DARK else ft.Colors.BLUE_700,
                },
                padding=ft.padding.symmetric(horizontal=10),
                shape=ft.RoundedRectangleBorder(radius=6)
            )
        )

        title_row = ft.Row([
            ft.Text("Filters", size=16, weight=ft.FontWeight.BOLD, color=colors["text"]),
            ft.VerticalDivider(width=10, color=ft.Colors.TRANSPARENT) if is_bottom else ft.Container(),
            self.add_filter_btn
        ], alignment=ft.MainAxisAlignment.START)

        return ft.Container(
            width=sidebar_width,
            height=sidebar_height,
            visible=self.config.get("sidebar_visible", False),
            bgcolor=colors["sidebar_bg"],
            padding=ft.padding.all(15),
            content=ft.Column([
                title_row,
                self.filter_list_view,
            ], spacing=10)
        )

    def _build_log_view(self):
        """建立 Log 顯示區域與自定義捲軸。"""
        colors = self._get_colors()
        
        # --- Log View (Virtual Scroll) 設定 ---
        self.ROW_HEIGHT = 20
        self.FONT_SIZE = 12
        self.LINE_HEIGHT_MULT = self.ROW_HEIGHT / self.FONT_SIZE 
        self.LINES_PER_PAGE = 20
        self.TEXT_POOL_SIZE = 50 
        
        self.text_pool = []
        for _ in range(self.TEXT_POOL_SIZE):
            t = ft.Text(
                value="", 
                font_family="Consolas, monospace",
                size=self.FONT_SIZE,
                no_wrap=True,
                color=colors["text"],
                visible=True,
            )
            c = ft.Container(
                content=t,
                height=self.ROW_HEIGHT,
                alignment=ft.Alignment(-1, 0),
                bgcolor=ft.Colors.TRANSPARENT,
                visible=True
            )
            self.text_pool.append(c)
            
        self.log_list_column = ft.Column(
            controls=self.text_pool,
            spacing=0,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            tight=True,
        )

        self.log_display_column = ft.Container(
            content=ft.GestureDetector(
                content=self.log_list_column,
                on_scroll=self.on_log_scroll,
                on_tap_down=self.on_log_area_tap,
                on_double_tap=self.on_log_area_double_tap,
                on_secondary_tap_down=self.on_log_area_secondary_tap,
                expand=True 
            ),
            expand=True,
            bgcolor=colors["log_bg"], 
        )
        
        # --- 自定義捲軸 ---
        self.scrollbar_width = 15
        self.scrollbar_thumb_height = 50 
        
        self.scrollbar_thumb = ft.Container(
            width=self.scrollbar_width,
            height=self.scrollbar_thumb_height,
            bgcolor=colors["scroll_thumb"],
            border_radius=5,
            top=0
        )
        
        self.scrollbar_track = ft.Container(
            width=self.scrollbar_width,
            bgcolor=colors["scroll_track"],
            expand=True,
        )
        
        self.scrollbar_stack = ft.Stack(
            controls=[
                self.scrollbar_track,
                self.scrollbar_thumb
            ],
            width=self.scrollbar_width,
            expand=True
        )
        
        self.scrollbar_container = ft.Container(
            content=ft.GestureDetector(
                content=self.scrollbar_stack,
                on_pan_update=self.on_scrollbar_drag,
                on_tap_down=self.on_scrollbar_tap
            ),
            width=self.scrollbar_width,
            bgcolor=colors["scroll_track"],
            alignment=ft.Alignment(-1, -1)
        )

        # Log 區域容器
        self.log_view_area = ft.Container(
            content=ft.Row(
                controls=[
                    self.log_display_column,
                    self.scrollbar_container
                ],
                spacing=0,
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            ),
            expand=True,
            visible=False 
        )

        # 初始歡迎畫面
        self.initial_content = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.Icons.ANALYTICS, size=80, color=ft.Colors.GREY_700),
                    ft.Text("LogAnalyzer", size=32, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_500),
                    ft.Text("Welcome to high-performance log analysis", size=16, color=ft.Colors.GREY_600),
                    ft.Container(height=20),
                    ft.Text("To get started:", size=14, color=ft.Colors.GREY_700),
                    ft.Row([
                        ft.Icon(ft.Icons.FOLDER_OPEN, size=16, color=ft.Colors.BLUE_400),
                        ft.Text("Go to File > Open File...", size=14, color=ft.Colors.GREY_600),
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    ft.Text("or", size=12, color=ft.Colors.GREY_700),
                    ft.Text("Drag & Drop Log File Here", size=14, color=ft.Colors.GREY_600),
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=colors["log_bg"],
            expand=True,
            visible=True
        )

        return ft.Column(
            controls=[
                self.initial_content,
                self.log_view_area
            ], 
            spacing=0,
            expand=True,
            alignment=ft.MainAxisAlignment.START,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )

    def _build_search_bar(self):
        """建立搜尋列（浮動在 Log 區域上方）。"""
        colors = self._get_colors()
        
        self.search_input = ft.TextField(
            label="Find",
            height=30,
            text_size=12,
            content_padding=5,
            width=200,
            on_submit=self.on_find_next,
            border_color=ft.Colors.BLUE
        )
        self.search_results_count = ft.Text(value="0/0", size=12, color=colors["text"])
        
        async def toggle_case(e):
            self.search_case_sensitive = not self.search_case_sensitive
            e.control.style = ft.ButtonStyle(color=ft.Colors.BLUE if self.search_case_sensitive else ft.Colors.GREY)
            e.control.update()
            self.search_query = "" # Force re-search
            await self.perform_search()

        async def toggle_wrap(e):
            self.search_wrap = not self.search_wrap
            e.control.style = ft.ButtonStyle(color=ft.Colors.BLUE if self.search_wrap else ft.Colors.GREY)
            e.control.update()

        self.search_bar = ft.Container(
            content=ft.Row([
                self.search_input,
                ft.IconButton(ft.Icons.ABC, tooltip="Match Case", icon_size=16, on_click=toggle_case, 
                              style=ft.ButtonStyle(color=ft.Colors.GREY)),
                ft.IconButton(ft.Icons.KEYBOARD_RETURN, tooltip="Wrap Around", icon_size=16, on_click=toggle_wrap,
                              style=ft.ButtonStyle(color=ft.Colors.BLUE)),
                # ft.VerticalDivider(width=1), # Removed divider
                ft.IconButton(ft.Icons.ARROW_UPWARD, icon_size=16, tooltip="Previous", on_click=self.on_find_prev),
                ft.IconButton(ft.Icons.ARROW_DOWNWARD, icon_size=16, tooltip="Next", on_click=self.on_find_next),
                self.search_results_count,
                ft.IconButton(ft.Icons.CLOSE, icon_size=16, on_click=self.hide_search_bar),
            ], spacing=5),
            bgcolor=colors["search_bg"],
            padding=5,
            border_radius=8, # Slightly larger radius
            shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK)), # Modern shadow instead of border
            visible=False, 
        )
        return self.search_bar

    def _build_status_bar(self):
        """建立底部狀態列。"""
        colors = self._get_colors()
        self.status_text = ft.Text("Ready", size=12, color=colors["status_text"])
        return ft.Container(
            height=25, # 稍微縮窄一點，更顯精緻
            bgcolor=colors["status_bg"],
            padding=ft.Padding.only(left=15, right=10),
            content=ft.Row([
                self.status_text,
            ], alignment=ft.MainAxisAlignment.START),
            alignment=ft.Alignment(-1, 0)
        )

    def build_ui(self, update_page=True):
        # --- Theme-Aware Colors ---
        colors = self._get_colors()
        
        # 同步更新頁面背景色
        self.page.bgcolor = colors["sidebar_bg"]
        
        # 1. 構建各個模組
        self.top_bar = self._build_top_bar()
        self.sidebar = self._build_sidebar()
        self.log_area_comp = self._build_log_view()
        self.search_bar_comp = self._build_search_bar()
        self.status_bar = self._build_status_bar()
        
        # 3. Main Layout Assembly
        # Wrap log area in a Stack to overlay the Search Bar
        self.log_stack = ft.Stack([
            self.log_area_comp,
            ft.Container(
                content=self.search_bar_comp,
                top=10, right=20 
            )
        ], expand=True)

        pos = self.config.get("sidebar_position", "left")
        
        if pos == "bottom":
            main_body = ft.Column(
                controls=[
                    self.log_stack,
                    self.sidebar, 
                ],
                expand=True, 
                spacing=0
            )
        elif pos == "right":
            main_body = ft.Row(
                controls=[
                    self.log_stack,
                    self.sidebar, 
                ],
                expand=True, 
                spacing=0
            )
        else: # left (default)
            main_body = ft.Row(
                controls=[
                    self.sidebar,
                    self.log_stack, 
                ],
                expand=True, 
                spacing=0
            )
        
        self.page.clean() # 確保更新時乾淨
        self.page.add(
            ft.Column([
                self.top_bar, 
                main_body,
                self.status_bar
            ], expand=True, spacing=0)
        )
        
        # 事件重新綁定
        self.page.on_keyboard_event = self.on_keyboard
        self.page.on_resize = self.on_resize
        
        if update_page:
            self.page.update()

    def update_ui_colors(self):
        """原地更新所有 UI 控件的顏色，而不重建 UI 結構。"""
        colors = self._get_colors()
        is_dark = self.page.theme_mode == ft.ThemeMode.DARK
        
        # 1. 頁面與基礎背景
        self.page.bgcolor = colors["sidebar_bg"]
        
        # 2. 頂部欄位
        if hasattr(self, "top_bar"):
            self.top_bar.bgcolor = colors["top_bar_bg"]
            # 更新頂欄陰影
            self.top_bar.shadow = ft.BoxShadow(
                spread_radius=1,
                blur_radius=4,
                color=ft.Colors.with_opacity(0.4 if is_dark else 0.2, ft.Colors.BLACK),
                offset=ft.Offset(0, 2)
            )
            
        if hasattr(self, "menu_bar"):
            self.menu_bar.style.bgcolor = colors["top_bar_bg"]
            
        if hasattr(self, "app_title_text"):
            self.app_title_text.color = colors["text"]
            
        if hasattr(self, "top_bar_row"):
            for control in self.top_bar_row.controls:
                if isinstance(control, ft.Container) and isinstance(control.content, ft.Icon):
                    control.content.color = colors["text"]

        # 3. 側邊欄
        if hasattr(self, "sidebar"):
            self.sidebar.bgcolor = colors["sidebar_bg"]
            if isinstance(self.sidebar.content, ft.Column):
                 for control in self.sidebar.content.controls:
                     if isinstance(control, ft.Text):
                         control.color = colors["text"]
                     elif isinstance(control, ft.Row):
                         for sub_control in control.controls:
                             if isinstance(sub_control, ft.Text):
                                 sub_control.color = colors["text"]
                                 sub_control.update() # Ensure visual update
            
            # Update Add Filter Button Style
            if hasattr(self, "add_filter_btn"):
                self.add_filter_btn.style = ft.ButtonStyle(
                    bgcolor={
                        ft.ControlState.DEFAULT: ft.Colors.BLUE_700 if is_dark else ft.Colors.BLUE_50,
                        ft.ControlState.HOVERED: ft.Colors.BLUE_600 if is_dark else ft.Colors.BLUE_100,
                    },
                    color={
                        ft.ControlState.DEFAULT: ft.Colors.WHITE if is_dark else ft.Colors.BLUE_700,
                    },
                    padding=ft.padding.symmetric(horizontal=10),
                    shape=ft.RoundedRectangleBorder(radius=6)
                )
                self.add_filter_btn.update()

        # 4. Log 區域
        if hasattr(self, "log_display_column"):
            self.log_display_column.bgcolor = colors["log_bg"]
        if hasattr(self, "initial_content"):
            self.initial_content.bgcolor = colors["log_bg"]

        # 5. 搜尋列
        if hasattr(self, "search_bar"):
            self.search_bar.bgcolor = colors["search_bg"]
            # Update shadow color for theme
            self.search_bar.shadow = ft.BoxShadow(
                blur_radius=10, 
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK if is_dark else ft.Colors.GREY_400)
            )
        if hasattr(self, "search_results_count"):
            self.search_results_count.color = colors["text"]
        
        # 7. 狀態列
        if hasattr(self, "status_bar"):
            self.status_bar.bgcolor = colors["status_bg"]
        if hasattr(self, "status_text"):
            self.status_text.color = colors["status_text"]

        # 8. 捲軸
        if hasattr(self, "scrollbar_track"):
            self.scrollbar_track.bgcolor = colors["scroll_track"]
        if hasattr(self, "scrollbar_container"):
            self.scrollbar_container.bgcolor = colors["scroll_track"]
        if hasattr(self, "scrollbar_thumb"):
            self.scrollbar_thumb.bgcolor = colors["scroll_thumb"]

    async def on_open_file_click(self, e):
        """開啟檔案對話框。"""
        await self._run_safe_async(self._perform_open_file_dialog(), "Opening File")

    async def _perform_open_file_dialog(self):
        import tkinter as tk
        from tkinter import filedialog
        
        def pick_file_sync():
            # 使用更穩定的方式啟動對話框
            # 某些環境下，不要頻繁建立與銷毀 root 更有助於穩定
            root = tk.Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            
            try:
                path = filedialog.askopenfilename(
                    title="Select Log File",
                    initialdir=self.config.get("last_log_dir", os.path.expanduser("~")),
                    filetypes=[("Log Files", "*.log;*.txt;*.tat"), ("All Files", "*.*")]
                )
            finally:
                # 關鍵：先取消 topmost 屬性，再延遲銷毀，
                # 讓 Windows 有時間平穩地切換焦點回 Flet 視窗
                root.attributes("-topmost", False)
                root.update()
                root.destroy()
            return path
            
        self.is_picking_file = True
        # 在開啟對話框前，先讓 Flet 處理完當前所有 UI 變更
        self.page.update() 
        
        file_path = await asyncio.to_thread(pick_file_sync)
        
        # 對話框關閉後，給予一小段緩衝時間，過濾掉隨之而來的錯誤 on_close 訊號
        await asyncio.sleep(0.5)
        self.is_picking_file = False
        
        if file_path:
            self.config["last_log_dir"] = os.path.dirname(file_path)
            await self.load_file(file_path)

    async def exit_app(self, e):
        self.save_config()
        await self.page.window_destroy()

    def update_recent_files_menu(self):
        recent = self.config.get("recent_files", [])
        self.recent_files_submenu.controls.clear()
        
        if not recent:
             self.recent_files_submenu.controls.append(
                 ft.MenuItemButton(content=ft.Text("No recent files"), disabled=True)
             )
        else:
            # Closure helper to capture path
            def create_click_handler(p):
                return lambda _: asyncio.create_task(self.load_file(p))

            for path in recent:
                self.recent_files_submenu.controls.append(
                    ft.MenuItemButton(
                        content=ft.Text(os.path.basename(path)),
                        leading=ft.Icon(ft.Icons.DESCRIPTION),
                        on_click=create_click_handler(path)
                    )
                )

    def add_to_recent_files(self, path):
        recent = self.config.get("recent_files", [])
        if path in recent:
            recent.remove(path)
        recent.insert(0, path)
        self.config["recent_files"] = recent[:10]
        self.update_recent_files_menu()
        self.save_config()
        if hasattr(self, "menu_bar"):
            self.menu_bar.update()

    async def import_tat_filters(self, e=None):
        """導入 TAT 過濾器檔案。"""
        await self._run_safe_async(self._perform_import_filters_logic(), "Importing Filters")

    async def _perform_import_filters_logic(self, filepath=None):
        path = filepath
        if not path:
            def ask_file():
                root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
                path = filedialog.askopenfilename(
                    title="Import TAT Filters",
                    initialdir=self.config.get("last_filter_dir", "."),
                    filetypes=[("TextAnalysisTool", "*.tat"), ("All Files", "*.*")])
                root.destroy(); return path
            self.is_picking_file = True
            path = await asyncio.to_thread(ask_file)
            self.is_picking_file = False
        
        if not path: return
        import xml.etree.ElementTree as ET
        tree = ET.parse(path)
        root = tree.getroot()
        new_filters = []
        for f_node in root.iter():
            if f_node.tag.lower() == 'filter':
                en = f_node.get('enabled', 'y').lower() == 'y'
                reg = f_node.get('regex', 'n').lower() == 'y'
                exc = (f_node.get('exclude', 'n').lower() == 'y') or (f_node.get('excluding', 'n').lower() == 'y')
                fg = f_node.get('foreColor', '000000')
                bg = f_node.get('backColor', 'ffffff')
                if not fg.startswith("#"): fg = "#" + fg
                if not bg.startswith("#"): bg = "#" + bg
                text = f_node.get('text')
                if text is None: text = f_node.text if f_node.text else ""
                new_filters.append(Filter(text, fg, bg, en, reg, exc))
        if new_filters:
            self.filters.extend(new_filters)
            await self.render_filters()
            await self._perform_filtering_logic()
            self.config["last_filter_dir"] = os.path.dirname(path)
            self.current_tat_path = path
            self.filters_dirty = False
            self.update_title()
            self.save_config()
            return f"Imported {len(new_filters)} filters"
        return "No filters found"

    async def save_tat_filters(self, e=None):
        """儲存過濾器。"""
        if not self.filters: return
        if self.current_tat_path:
            await self._run_safe_async(self._write_filters_to_file(self.current_tat_path), "Saving Filters")
        else:
            await self.save_tat_filters_as()

    async def save_tat_filters_as(self, e=None):
        """過濾器另存新檔。"""
        if not self.filters: return
        await self._run_safe_async(self._perform_save_as_logic(), "Saving Filters")

    async def _perform_save_as_logic(self):
        def ask_save():
            root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
            path = filedialog.asksaveasfilename(
                title="Save Filters As",
                defaultextension=".tat",
                initialdir=self.config.get("last_filter_dir", "."),
                filetypes=[("TextAnalysisTool", "*.tat")])
            root.destroy(); return path
        self.is_picking_file = True
        path = await asyncio.to_thread(ask_save)
        self.is_picking_file = False
        if path:
            await self._write_filters_to_file(path)

    async def _write_filters_to_file(self, path):
        """實體寫入過濾器檔案。"""
        xml_content = '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n<TextAnalysisTool.NET>\n'   
        for f in self.filters:
            xml_content += f"  {f.to_tat_xml()}\n"
        xml_content += "</TextAnalysisTool.NET>"
        with open(path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        self.config["last_filter_dir"] = os.path.dirname(path)
        self.current_tat_path = path
        self.filters_dirty = False
        self.update_title()
        self.save_config()
        return "Filters saved successfully"
        
    async def exit_app(self, e):
        # 這裡不直接銷毀，而是呼叫我們的關閉處理器，讓它可以檢查 unsaved changes
        await self.handle_app_close(e)

    def toggle_sidebar(self):
        self.sidebar.visible = not self.sidebar.visible
        self.config["sidebar_visible"] = self.sidebar.visible
        self.page.update()

    def change_sidebar_position(self, pos):
        """更改側邊欄位置並重建佈局。"""
        self.config["sidebar_position"] = pos
        self.save_config()
        # 重新建構 UI 以套用佈局變更
        self.build_ui()
        # 重建 UI 後需確保過濾器列表正確渲染
        asyncio.create_task(self.render_filters())

    def update_title(self):
        log_name = os.path.basename(self.file_path) if self.file_path else "No file loaded"
        filter_name = os.path.basename(self.current_tat_path) if self.current_tat_path else "No filter file"
        title_str = f"[{log_name}] - [{filter_name}] - LogAnalyzer"
        
        self.page.title = title_str
        # Optional: Update the visible title in the app bar if desired
        # self.app_title_text.value = "LogAnalyzer" # Keep simple or update? Keep simple for UI.
        self.page.update()

    async def toggle_theme(self, e):
        """切換深色/淺色模式並原地更新顏色，防止閃爍。"""
        import ctypes
        
        # 1. 切換主題狀態
        if self.page.theme_mode == ft.ThemeMode.DARK:
            self.page.theme_mode = ft.ThemeMode.LIGHT
            win_dark_value = 0 
        else:
            self.page.theme_mode = ft.ThemeMode.DARK
            win_dark_value = 1
            
        # 2. 同步 Windows 原生標題列
        if sys.platform == "win32":
            try:
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                if hwnd:
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(win_dark_value)), 4)
            except Exception: pass

        # 3. 原地更新顏色 (不重建 UI，不呼叫 clean/add)
        self.update_ui_colors()
        
        # 4. 更新內容顏色
        # A. 恢復過濾器標籤 (不論是否載入 log 都應更新顏色)
        await self.render_filters(update_page=False)
        self.filter_list_view.update() # 強制局部刷新以處理 ReorderableListView 的 key 變更
        
        if self.log_engine:
            # 更新 Log 每一行的顏色
            self.update_log_view()
            # 更新時間軸已移除 (Timeline removed)
        
        # 5. 保存設定並更新
        self.save_config()
        self.page.update()


    async def show_search_bar(self):
        self.search_bar.visible = True
        self.page.update() # First update to make it visible
        
        # Then focus
        try:
            await self.search_input.focus()
        except Exception:
            pass
            
        self.page.update() # Second update to ensure focus state is rendered

    async def hide_search_bar(self, e=None):
        self.search_bar.visible = False
        self.search_results = []
        self.current_search_idx = -1
        self.update_log_view()
        self.page.update()

    async def on_find_next(self, e=None):
        await self.perform_search(backward=False)

    async def on_find_prev(self, e=None):
        await self.perform_search(backward=True)

    async def perform_search(self, backward=False):
        if not self.log_engine: return
        
        query = self.search_input.value
        if not query:
            self.search_results = []
            self.current_search_idx = -1
            self.update_log_view()
            return

        # If query or case-sensitivity changed, perform a new global search
        if query != self.search_query:
            self.search_query = query
            # Call Rust engine search (returns list of raw indices)
            self.search_results = await asyncio.to_thread(
                self.log_engine.search, query, False, self.search_case_sensitive
            )
            self.current_search_idx = -1

        if not self.search_results:
            self.update_results_count("0/0")
            self.status_text.value = f"No results for '{query}'"
            self.page.update()
            return

        # Navigation logic with Wrap Around support
        old_idx = self.current_search_idx
        
        if backward:
            if self.current_search_idx <= 0:
                if self.search_wrap:
                    self.current_search_idx = len(self.search_results) - 1
                else:
                    self.status_text.value = "Reached Top"
                    self.page.update()
                    return
            else:
                self.current_search_idx -= 1
        else:
            if self.current_search_idx >= len(self.search_results) - 1:
                if self.search_wrap:
                    self.current_search_idx = 0
                else:
                    self.status_text.value = "Reached Bottom"
                    self.page.update()
                    return
            else:
                self.current_search_idx += 1

        self.update_results_count(f"{self.current_search_idx + 1}/{len(self.search_results)}")
        
        # Jump to the search result
        target_raw_idx = self.search_results[self.current_search_idx]
        
        # Sync selection with search result
        self.selected_indices = {target_raw_idx}
        self.selection_anchor = target_raw_idx
        
        # We need to find the filtered index corresponding to this raw index
        target_view_idx = self._get_view_index_from_raw(target_raw_idx)
        
        # If the search result is filtered out, we jump to the nearest visible line?
        # For now, if view_idx is None, we stay at current position but select it
        if target_view_idx is not None:
            self.jump_to_index(target_view_idx, update_slider=True)
        else:
            self.status_text.value = f"Result on line {target_raw_idx+1} is filtered out."
            self.page.update()

    def update_results_count(self, text):
        self.search_results_count.value = text
        self.page.update()

    async def on_log_scroll(self, e: ft.ScrollEvent):
        if not self.log_engine: return
        
        # Throttling handled by render_loop if we use target_start_index, 
        # but here we calculate new target.
        
        delta = e.scroll_delta.y
        
        # Dynamic acceleration
        # If delta is large (fast scroll), increase step
        # Standard mouse wheel is often ~100.
        base_step = 3
        if abs(delta) >= 100:
             step = int(abs(delta) / 10) # e.g. 100 -> 10 lines
        elif abs(delta) > 20:
             step = 5
        else:
             step = base_step
             
        step = max(1, step) # Minimum 1 line

        if delta > 0:
            new_idx = self.target_start_index + step
        elif delta < 0:
            new_idx = self.target_start_index - step
        else:
            return
            
        # Immediate Update Path for responsiveness
        target = int(new_idx)
        
        # Boundary Check (Clamping)
        total_items = len(self.filtered_indices) if self.filtered_indices is not None else (self.log_engine.line_count() if self.log_engine else 0)
        max_idx = max(0, total_items - self.LINES_PER_PAGE)
        
        target = max(0, min(target, max_idx))
        self.target_start_index = target
        
        if not self.is_updating:
            asyncio.create_task(self.immediate_render())

    async def immediate_render(self):
        if self.is_updating: return
        self.is_updating = True
        try:
            # Phase 9: Scoped Update only
            self.current_start_index = self.target_start_index
            self.update_log_view()
            self.sync_scrollbar_position()
            
            # Update specific controls only - DO NOT use page.update()
            self.log_list_column.update()
            self.scrollbar_stack.update()
        finally:
            self.is_updating = False
            # If target changed during the update, schedule next frame immediately
            if self.current_start_index != self.target_start_index:
                # Yield briefly to avoid event loop starvation
                await asyncio.sleep(0.001)
                asyncio.create_task(self.immediate_render())

    def update_log_view(self):
        """從 Engine 獲取當前視窗的數據並更新 UI"""
        if not self.log_engine: return
            
        is_dark = self.page.theme_mode == ft.ThemeMode.DARK
        
        # PRE-CALCULATE filter colors
        filter_color_cache = {}
        if self.filters:
            active_filters_objs = []
            for f in self.filters:
                if f.enabled and f.text:
                    active_filters_objs.append(f)
                    idx = len(active_filters_objs) - 1
                    filter_color_cache[idx] = (
                        adjust_color_for_theme(f.back_color, True, is_dark),
                        adjust_color_for_theme(f.fore_color, False, is_dark)
                    )

        search_query = self.search_input.value.lower() if (self.search_bar.visible and self.search_input.value) else None
        
        if self.show_only_filtered and self.filtered_indices is not None:
            total_items = len(self.filtered_indices)
        else:
            total_items = self.log_engine.line_count()

        # Turbo Rendering Path: Optimized for minimum Python overhead and IPC payload
        _get_lines_batch = getattr(self.log_engine, 'get_lines_batch', None)
        _filtered_indices = self.filtered_indices
        _show_filtered = self.show_only_filtered
        _current_start_index = self.current_start_index
        _selected_indices = self.selected_indices
        _line_tags_codes = self.line_tags_codes
        _text_pool = self.text_pool
        _lines_per_page = self.LINES_PER_PAGE
        
        search_active = bool(search_query)

        # 1. Prepare target indices for the current viewport
        target_indices = []
        for i in range(_lines_per_page):
            view_idx = _current_start_index + i
            if 0 <= view_idx < total_items:
                real_idx = _filtered_indices[view_idx] if (_show_filtered and _filtered_indices is not None) else view_idx
                target_indices.append(real_idx)
        
        # 2. Batch fetch text and log levels from Rust in a single IPC call
        batch_data = []
        if target_indices and _get_lines_batch:
            batch_data = _get_lines_batch(target_indices)

        # 3. Static style table - resolved to local variables for fast lookup
        c_default = "#d4d4d4" if is_dark else "#1e1e1e"
        c_error = "#ff6b6b"
        c_warn = "#ffd93d"
        c_info = "#4dabf7"
        c_select_bg = "#264f78" if is_dark else "#b3d7ff"
        c_trans = ft.Colors.TRANSPARENT
        
        # 4. Render Loop with Strict Dirty Checking to minimize JSON Patch size
        for i in range(self.TEXT_POOL_SIZE):
            row_container = _text_pool[i]
            text_control = row_container.content
            
            if i < len(batch_data):
                line_data, level_code = batch_data[i]
                real_idx = target_indices[i]
                
                # Colors logic
                if level_code == 1: base_color = c_error
                elif level_code == 2: base_color = c_warn
                elif level_code == 3: base_color = c_info
                else: base_color = c_default
                
                bg_color = None
                if _line_tags_codes is not None and real_idx < len(_line_tags_codes):
                    tag_code = _line_tags_codes[real_idx]
                    if tag_code >= 2: 
                        af_idx = tag_code - 2
                        if af_idx in filter_color_cache:
                            bg_color, base_color = filter_color_cache[af_idx]
                    elif tag_code == 1:
                        base_color = ft.Colors.GREY_500 if is_dark else ft.Colors.GREY_400
                
                if real_idx in _selected_indices:
                    bg_color = c_select_bg

                # Only touch Flet properties if they MUST change
                target_bg = bg_color if bg_color else c_trans
                if row_container.bgcolor != target_bg:
                    row_container.bgcolor = target_bg
                
                if not row_container.visible:
                    row_container.visible = True
                
                if text_control.color != base_color:
                    text_control.color = base_color

                if search_active and search_query in line_data.lower():
                    # Search Highlight Path
                    h_bg = ft.Colors.YELLOW
                    h_fg = ft.Colors.BLACK
                    if bg_color and get_luminance(bg_color) > 0.6:
                        h_bg = ft.Colors.BLUE_800
                        h_fg = ft.Colors.WHITE
                    
                    parts = re.split(f"({re.escape(search_query)})", line_data, flags=re.IGNORECASE)
                    text_control.value = "" 
                    text_control.spans = [
                        ft.TextSpan(p, style=ft.TextStyle(bgcolor=h_bg, color=h_fg, weight=ft.FontWeight.BOLD)) 
                        if p.lower() == search_query else ft.TextSpan(p, style=ft.TextStyle(color=base_color)) 
                        for p in parts
                    ]
                else:
                    # Optimized Path: Simple Text
                    if text_control.spans:
                        text_control.spans = [] 
                    
                    target_val = line_data if line_data.strip() else " "
                    if text_control.value != target_val:
                        text_control.value = target_val
            else:
                if row_container.visible:
                    row_container.visible = False
                    row_container.bgcolor = c_trans
                    text_control.value = ""



        
        # REMOVED page.update() here, it's now in the render_loop

    def jump_to_index(self, idx, update_slider=True, immediate=False):
        if not self.log_engine:
            return

        # Determine total items based on filter state
        if self.show_only_filtered and self.filtered_indices is not None:
            total_items = len(self.filtered_indices)
        else:
            total_items = self.log_engine.line_count()

        # 邊界檢查
        if idx < 0: idx = 0
        max_idx = max(0, total_items - self.LINES_PER_PAGE)
        if idx > max_idx: idx = max_idx
        
        self.target_start_index = idx
        
        if immediate:
            # Snap immediately
            asyncio.create_task(self.immediate_render())

    async def on_slider_change(self, e):
        # Time-based debounce is still useful but less critical if we don't update slider
        if time.time() - self.last_slider_update < 0.1:
             # print("DEBUG: Ignored slider echo event")
             return
            
        if self.is_programmatic_scroll:
            return
            
        # Don't update slider because it's the source of truth right now
        self.jump_to_index(int(e.control.value), update_slider=False)

    async def on_keyboard(self, e: ft.KeyboardEvent):
        # Global Shortcuts (Work without log loaded)
        if e.ctrl and e.key.lower() == "b":
            self.toggle_sidebar()
            return

        if not self.log_engine:
            return

        # Determine total items
        total_items = len(self.filtered_indices) if self.filtered_indices is not None else self.log_engine.line_count()
        if total_items == 0: return

        # Clipboard Shortcuts
        if e.ctrl and e.key.lower() == "c":
            await self.copy_selected_lines()
            return

        # Search Shortcuts
        if e.ctrl and e.key.lower() == "f":
            await self.show_search_bar()
            return
        if e.ctrl and e.key.lower() == "h":
            await self.toggle_show_filtered()
            return
        if e.key == "Escape":
            await self.hide_search_bar()
            return
        if e.key == "F2":
            await self.perform_search(backward=True)
            return
        if e.key == "F3":
            await self.perform_search(backward=e.shift)
            return
        if e.key == "Enter" and self.search_bar.visible:
            await self.perform_search(backward=e.shift)
            return

        # --- Selection-based Navigation ---
        # Find current view index of the anchor
        current_view_idx = self._get_view_index_from_raw(self.selection_anchor)
        if current_view_idx is None: current_view_idx = 0
        
        new_view_idx = current_view_idx
        
        # Modifier for speed
        step = 1
        if e.ctrl: step = 10 # Faster scroll with Ctrl
        
        # Basic navigation
        if e.key in ["ArrowDown", "Arrow Down"]:
            new_view_idx = current_view_idx + step
        elif e.key in ["ArrowUp", "Arrow Up"]:
            new_view_idx = current_view_idx - step
        elif e.key in ["PageDown", "Page Down", "Next"]:
            new_view_idx = current_view_idx + self.LINES_PER_PAGE
        elif e.key in ["PageUp", "Page Up", "Prior"]:
            new_view_idx = current_view_idx - self.LINES_PER_PAGE
        elif e.key == "Home": 
            new_view_idx = 0
        elif e.key == "End": 
            new_view_idx = total_items - 1
        else:
            return

        # Clamp range
        new_view_idx = max(0, min(new_view_idx, total_items - 1))
        
        # Map back to raw index for selection
        if self.show_only_filtered and self.filtered_indices is not None:
            new_raw_idx = self.filtered_indices[new_view_idx]
        else:
            new_raw_idx = new_view_idx

        # Update Selection
        self.selected_indices = {new_raw_idx}
        self.selection_anchor = new_raw_idx
        
        # --- Sync Viewport (Scroll to follow selection) ---
        # We use immediate=True for keyboard to make it feel snappy
        if new_view_idx < self.target_start_index:
            # Scroll up to show the new line at the top
            self.jump_to_index(new_view_idx, immediate=True)
        elif new_view_idx >= self.target_start_index + self.LINES_PER_PAGE:
            # Scroll down to show the new line at the bottom
            self.jump_to_index(new_view_idx - self.LINES_PER_PAGE + 1, immediate=True)
        else:
            # Selection is within viewport, just redraw highlight
            self.needs_render = True
            self.update_log_view()
            self.page.update()



    async def on_page_scroll(self, e: ft.ScrollEvent):
        # Flet page scroll event
        # Only works if page is scrollable? No, usually works globally if handled.
        # Check if we should scroll the log
        if not self.log_engine:
            return
            
        # Adjust sensitivity
        step = 3
        
        # e.scroll_delta_y might be pixels, so we need to threshold it
        if e.scroll_delta_y > 0:
            new_idx = self.current_start_index + step
        elif e.scroll_delta_y < 0:
            new_idx = self.current_start_index - step
        else:
            return
            
        self.jump_to_index(int(new_idx), update_slider=True)



    async def on_resize(self, e):
        # Update scrollbar track height info
        if self.page.height:
            # Check if initial content is hidden
            is_initial = self.initial_content.visible
            status_h = self.status_bar.height if self.status_bar.height else 30
            menu_h = self.top_bar.height if self.top_bar.height else 40
            
            # Safe margin calculation
            self.scrollbar_track_height = self.page.height - status_h - menu_h
            
            # Dynamic LINES_PER_PAGE
            line_height = self.ROW_HEIGHT
            if self.scrollbar_track_height > 0:
                # Calculate exactly how many rows fit in the track
                new_lines_per_page = int((self.scrollbar_track_height - 10) / line_height)
                # Clamp to pool size
                new_lines_per_page = max(10, min(new_lines_per_page, self.TEXT_POOL_SIZE))
                
                if new_lines_per_page != self.LINES_PER_PAGE:
                    self.LINES_PER_PAGE = new_lines_per_page
                    self.update_log_view()

            # Re-sync thumb position
            self.sync_scrollbar_position()
            
        self.page.update()

    async def on_scrollbar_drag(self, e: ft.DragUpdateEvent):
        # Update thumb position visually
        delta = get_event_prop(e, 'delta_y', default=0)
        
        self.thumb_top += delta
        
        # Clamp position
        max_top = self.scrollbar_track_height - self.scrollbar_thumb_height
        if max_top < 0: max_top = 0
        
        self.thumb_top = max(0.0, min(self.thumb_top, max_top))
        self.scrollbar_thumb.top = self.thumb_top
        self.scrollbar_thumb.update() # Fast local update
        
        # Calculate index
        if max_top > 0:
            percentage = self.thumb_top / max_top
            
            # Total lines
            total_items = len(self.filtered_indices) if self.filtered_indices is not None else (self.log_engine.line_count() if self.log_engine else 0)
            max_idx = max(0, total_items - self.LINES_PER_PAGE)
            
            new_idx = int(percentage * max_idx)
            # Update target and trigger immediate render
            self.target_start_index = new_idx
            if not self.is_updating:
                asyncio.create_task(self.immediate_render())
    
    async def on_scrollbar_tap(self, e: ft.TapEvent):
        # Jump to position
        local_y = get_event_prop(e, 'local_y', default=0)
        
        click_y = local_y - (self.scrollbar_thumb_height / 2) # Center thumb on click
        
        max_top = self.scrollbar_track_height - self.scrollbar_thumb_height
        if max_top <= 0: return

        self.thumb_top = max(0.0, min(click_y, max_top))
        # self.scrollbar_thumb.top = self.thumb_top
        
        percentage = self.thumb_top / max_top
        total_items = len(self.filtered_indices) if self.filtered_indices is not None else (self.log_engine.line_count() if self.log_engine else 0)
        max_idx = max(0, total_items - self.LINES_PER_PAGE)
        new_idx = int(percentage * max_idx)
        
        self.jump_to_index(new_idx, update_slider=True, immediate=True) # immediate=True will trigger render

    def sync_scrollbar_position(self):
        if not self.log_engine: return
        
        total_items = len(self.filtered_indices) if self.filtered_indices is not None else self.log_engine.line_count()
        max_idx = max(0, total_items - self.LINES_PER_PAGE)
        if max_idx <= 0:
            self.thumb_top = 0
            self.scrollbar_thumb.top = 0
            return

        percentage = self.current_start_index / max_idx
        max_top = self.scrollbar_track_height - self.scrollbar_thumb_height
        if max_top < 0: max_top = 0
        
        self.thumb_top = percentage * max_top
        self.scrollbar_thumb.top = self.thumb_top
        # Explicitly update thumb to ensure visual sync if page.update misses it?
        # self.scrollbar_thumb.update()

    async def render_loop(self):
        """Background task that polls for index changes."""
        while True:
            try:
                # Still check for needs_render (for non-scroll updates like filters)
                if self.needs_render:
                    self.needs_render = False
                    await self.immediate_render()
                
                await asyncio.sleep(0.1) # Much slower heartbeat, scroll is handled immediately
            except Exception as e:
                print(f"Render Loop Error: {e}")
                await asyncio.sleep(1)



    async def on_slider_change(self, e):
        pass

    async def toggle_show_filtered(self, e=None):
        self.show_only_filtered = not self.show_only_filtered
        self.show_toast(f"Mode: {'Filtered Only' if self.show_only_filtered else 'Full View'}")
        self.current_start_index = 0 # Reset to top
        self.update_status_bar() # Update line counts in status bar
        self.update_log_view()
        self.sync_scrollbar_position()
        self.page.update()

    async def _run_safe_async(self, coro, status_msg=None):
        """
        通用的非同步任務執行器。
        提供統一的錯誤捕捉、Log 紀錄與 SnackBar 提示，防止 UI 崩潰。
        """
        if status_msg:
            self.status_text.value = f"{status_msg}..."
            self.page.update()
            
        try:
            result = await coro
            # If the coroutine returns a result message, show it as a Toast
            if isinstance(result, str) and status_msg:
                self.show_toast(result)
            
            # Clean up status bar if it's still showing the transient progress message
            # (Meaning the task didn't update the status bar itself, e.g. when no log is loaded)
            if status_msg and self.status_text.value == f"{status_msg}...":
                self.status_text.value = "Ready"
                self.status_text.update()
                
            return result
        except Exception as e:
            print(f"UNHANDLED ERROR: {e}", flush=True)
            import traceback
            traceback.print_exc()
            
            # 顯示錯誤提示給使用者
            self.show_toast(f"Error: {str(e)}", is_error=True)
            return None

    async def apply_filters(self):
        """執行過濾邏輯。"""
        if not self.log_engine:
            return

        # 使用安全執行器執行核心過濾任務
        await self._run_safe_async(self._perform_filtering_logic(), "Filtering")

    async def _perform_filtering_logic(self):
        """實際的過濾計算邏輯。"""
        # 前置條件檢查：必須有 log 檔案載入才能過濾
        if not self.log_engine:
            return
            
        # 收集啟用的 Filters
        active_filters = []
        active_map = [] 

        for i, f in enumerate(self.filters):
            f.hit_count = 0
            if f.enabled and f.text:
                active_filters.append((f.text, f.is_regex, f.is_exclude, f.is_event, i))
                active_map.append(i)

        if not active_filters:
            self.filtered_indices = None
            self.line_tags_codes = None
            total_count = self.log_engine.line_count()
        else:
            # 呼叫引擎 (背景執行緒執行防止卡頓)
            results = await asyncio.to_thread(self.log_engine.filter, active_filters)
            
            # 解包結果 (忽略 timeline_events)
            self.line_tags_codes, self.filtered_indices, hit_counts, _ = results
            total_count = len(self.filtered_indices)
            
            # 更新過濾器命中數
            for idx, count in enumerate(hit_counts):
                if idx < len(active_map):
                    self.filters[active_map[idx]].hit_count = count
            
            await self.render_filters()

        self.current_start_index = 0
        self.jump_to_index(0, update_slider=True)
        
        self.update_status_bar()
        self.needs_render = True
        # self.page.update() # REMOVED: Rely on render_loop
        # self.update_log_view() # jump_to_index already calls update_log_view

    async def on_add_filter_click(self, e):
        # Instead of adding directly, open the dialog
        await self.open_filter_dialog()

    async def open_filter_dialog(self, filter_obj=None, initial_text=None):
        # Create a temporary state for the dialog
        is_new = filter_obj is None
        d_text = (initial_text if initial_text else "") if is_new else filter_obj.text
        d_fore = filter_obj.fore_color if not is_new else "#FFFFFF"
        d_back = filter_obj.back_color if not is_new else "#000000"
        d_regex = filter_obj.is_regex if not is_new else False
        d_exclude = filter_obj.is_exclude if not is_new else False

        # Dialog controls
        txt_pattern = ft.TextField(label="Pattern", value=d_text, autofocus=True, expand=True)
        sw_regex = ft.Switch(label="Regex", value=d_regex)
        sw_exclude = ft.Switch(label="Exclude", value=d_exclude)
        
        # Simple color presets (Matching loganalyzer.py common colors)
        colors = ["#000000", "#FFFFFF", "#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF", 
                  "#800000", "#008000", "#000080", "#808000", "#800080", "#008080", "#C0C0C0", "#808080"]
        
        selected_fg = d_fore
        selected_bg = d_back

        def update_preview():
            is_dark = self.page.theme_mode == ft.ThemeMode.DARK
            adj_bg = adjust_color_for_theme(selected_bg, True, is_dark)
            adj_fg = adjust_color_for_theme(selected_fg, False, is_dark)
            preview.bgcolor = adj_bg
            preview.content.color = adj_fg
            preview.update()

        def set_fg(color):
            nonlocal selected_fg
            selected_fg = color
            update_preview()

        def set_bg(color):
            nonlocal selected_bg
            selected_bg = color
            update_preview()

        preview = ft.Container(
            content=ft.Text("Preview Text", color=adjust_color_for_theme(selected_fg, False, self.page.theme_mode == ft.ThemeMode.DARK), weight=ft.FontWeight.BOLD),
            bgcolor=adjust_color_for_theme(selected_bg, True, self.page.theme_mode == ft.ThemeMode.DARK),
            padding=10,
            border_radius=5,
            alignment=ft.Alignment(0, 0)
        )

        def build_color_grid(on_click_func, is_bg_selection):
            is_dark = self.page.theme_mode == ft.ThemeMode.DARK
            return ft.Row([
                ft.Container(
                    width=24, height=24, 
                    # Show the adjusted color in the palette so it matches preview
                    bgcolor=adjust_color_for_theme(c, is_bg_selection, is_dark), 
                    border_radius=3,
                    border=ft.Border.all(1, ft.Colors.GREY_400),
                    tooltip=f"Original: {c}",
                    on_click=lambda e, col=c: on_click_func(col)
                ) for c in colors
            ], wrap=True, width=300)

        async def save_filter(e):
            nonlocal filter_obj
            self.filters_dirty = True # Mark as modified
            if is_new:
                filter_obj = Filter(txt_pattern.value, selected_fg, selected_bg, True, sw_regex.value, sw_exclude.value)
                self.filters.append(filter_obj)
            else:
                filter_obj.text = txt_pattern.value
                filter_obj.fore_color = selected_fg
                filter_obj.back_color = selected_bg
                filter_obj.is_regex = sw_regex.value
                filter_obj.is_exclude = sw_exclude.value
            
            self.dialog.open = False
            await self.render_filters()
            await self.apply_filters()
            self.page.update()

        self.dialog = ft.AlertDialog(
            title=ft.Text("Edit Filter" if not is_new else "Add Filter"),
            content=ft.Column([
                txt_pattern,
                ft.Row([sw_regex, sw_exclude]),
                ft.Text("Foreground Color:"),
                build_color_grid(set_fg, False),
                ft.Text("Background Color:"),
                build_color_grid(set_bg, True),
                ft.Text("(Colors automatically adjusted for readability)", size=10, italic=True, color=ft.Colors.GREY_500),
                ft.Divider(),
                ft.Text("Preview:"),
                preview
            ], tight=True, scroll=ft.ScrollMode.AUTO, width=400),
            actions=[
                ft.TextButton("Save", on_click=save_filter),
                ft.TextButton("Cancel", on_click=lambda _: [setattr(self.dialog, 'open', False), self.page.update()])
            ]
        )
        self.page.show_dialog(self.dialog)

    async def delete_filter(self, filter_obj):
        if filter_obj in self.filters:
            self.filters.remove(filter_obj)
            self.filters_dirty = True # Set dirty flag
            await self.render_filters()
            await self.apply_filters()
            self.page.update()

    async def move_filter_to_top(self, filter_obj):
        if filter_obj in self.filters:
            self.filters.remove(filter_obj)
            self.filters.insert(0, filter_obj)
            self.filters_dirty = True # Set dirty flag
            await self.render_filters()
            await self.apply_filters()
            self.page.update()

    async def move_filter_to_bottom(self, filter_obj):
        if filter_obj in self.filters:
            self.filters.remove(filter_obj)
            self.filters.append(filter_obj)
            self.filters_dirty = True # Set dirty flag
            await self.render_filters()
            await self.apply_filters()
            self.page.update()

    async def render_filters(self, update_page=True):
        self.filter_list_view.controls.clear()
        # 使用與 ThemeColors 一致的穩定判斷邏輯
        is_dark = str(self.page.theme_mode).split(".")[-1].lower() == "dark"
        
        for i, f in enumerate(self.filters):
            # Checkbox for enabled state
            async def on_cb_change(e, obj=f):
                obj.enabled = e.control.value
                self.filters_dirty = True
                await self.apply_filters()

            cb = ft.Checkbox(
                value=f.enabled, 
                on_change=on_cb_change,
            )
            # Use tab_index=-1 to exclude from keyboard navigation
            cb.tab_index = -1
            
            # Smart Colors for Tag
            adj_bg = adjust_color_for_theme(f.back_color, True, is_dark)
            adj_fg = adjust_color_for_theme(f.fore_color, False, is_dark)
            
            # Label with Background/Foreground colors (Tag-like look)
            type_str = " (R)" if f.is_regex else ""
            if f.is_exclude: type_str += " [X]"
            
            lbl_tag = ft.Container(
                content=ft.Text(
                    value=f"{f.text}{type_str}", 
                    size=12,
                    color=adj_fg, # Adjusted
                    weight=ft.FontWeight.W_500,
                    no_wrap=True,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                bgcolor=adj_bg, # Adjusted
                padding=ft.Padding(8, 2, 8, 2), # Compact padding
                border_radius=15, # Slightly tighter pill shape
                expand=True,
            )
            
            # Hit Count Badge
            hit_badge = ft.Container(
                content=ft.Text(str(f.hit_count), size=10, color="black", weight=ft.FontWeight.BOLD),
                bgcolor="#bdc3c7" if f.hit_count == 0 else "#f1c40f",
                padding=ft.Padding.symmetric(horizontal=6, vertical=0), # More horizontal, less vertical
                border_radius=8,
                alignment=ft.Alignment(0, 0),
                height=16, # Fixed height for better proportion
            )

            # Row container
            async def on_double_tap(e, obj=f):
                await self.open_filter_dialog(obj)

            async def on_secondary_tap(e, obj=f):
                self.open_filter_context_menu(e, obj)

            item_row = ft.GestureDetector(
                key=f"{id(f)}_{is_dark}", # 關鍵：包含主題資訊，強制主題切換時完全重繪
                content=ft.Container(
                    content=ft.Row([
                        cb,
                        lbl_tag,
                        hit_badge
                    ], spacing=2, alignment=ft.MainAxisAlignment.START),
                    padding=ft.padding.only(right=35), # 為 ReorderableListView 的拖曳手把留出空間
                    height=28, # Enforce compact height
                ),
                on_double_tap=on_double_tap,
                on_secondary_tap=on_secondary_tap,
            )
            # Ensure the row doesn't end up in the tab cycle
            item_row.tab_index = -1
            
            self.filter_list_view.controls.append(item_row)
        
        if update_page:
            self.page.update()

    async def on_filter_reorder(self, e):
        """處理過濾器拖曳排序事件。"""
        # e.old_index: 被拖曳項目的原始位置
        # e.new_index: 拖曳到的新位置
        
        # 從事件物件中取得索引 (使用通用方式以相容不同版本)
        old_idx = getattr(e, "old_index", None)
        new_idx = getattr(e, "new_index", None)
        
        if old_idx is None or new_idx is None:
            return
            
        # 1. 更新資料列表
        f = self.filters.pop(old_idx)
        self.filters.insert(new_idx, f)
        self.filters_dirty = True
        
        # 2. 重新渲染介面
        await self.render_filters()
        
        # 3. 重新執行過濾邏輯 (因為順序影響配色優先權)
        await self.apply_filters()

    def open_filter_context_menu(self, e, obj):
        def close_dlg(ev):
            self.filter_ctx.open = False
            self.page.update()

        async def menu_edit(ev):
            await self.open_filter_dialog(obj)
            close_dlg(None)

        async def menu_top(ev):
            await self.move_filter_to_top(obj)
            close_dlg(None)

        async def menu_bottom(ev):
            await self.move_filter_to_bottom(obj)
            close_dlg(None)

        async def menu_delete(ev):
            await self.delete_filter(obj)
            close_dlg(None)

        self.filter_ctx = ft.AlertDialog(
            title=ft.Text("Filter Actions"),
            content=ft.Column([
                ft.ListTile(leading=ft.Icon(ft.Icons.EDIT), title=ft.Text("Edit Filter"), on_click=menu_edit),
                ft.ListTile(leading=ft.Icon(ft.Icons.ARROW_UPWARD), title=ft.Text("Move to Top"), on_click=menu_top),
                ft.ListTile(leading=ft.Icon(ft.Icons.ARROW_DOWNWARD), title=ft.Text("Move to Bottom"), on_click=menu_bottom),
                ft.ListTile(leading=ft.Icon(ft.Icons.DELETE), title=ft.Text("Delete"), on_click=menu_delete),
            ], height=240, width=200),
            actions=[ft.TextButton("Close", on_click=close_dlg)]
        )
        self.page.show_dialog(self.filter_ctx)


    async def on_log_area_double_tap(self, e):
        # Double tap event in Flet doesn't provide coordinates, 
        # so we use the one captured by the last on_tap_down
        local_y = getattr(self, "last_log_tap_y", 0)
        row_idx = int(local_y / self.ROW_HEIGHT)
        
        class MockEvent:
            def __init__(self, data):
                self.control = type('obj', (object,), {'data': data})
        
        mock_e = MockEvent(row_idx)
        await self.on_log_double_click(mock_e)

    async def on_log_double_click(self, e):
        row_idx = e.control.data
        view_idx = self.current_start_index + row_idx
        
        # Determine total items
        if self.show_only_filtered and self.filtered_indices is not None:
            total_items = len(self.filtered_indices)
        else:
            total_items = self.log_engine.line_count() if self.log_engine else 0
            
        if view_idx >= total_items: return
        
        # Map to real_idx
        if self.show_only_filtered and self.filtered_indices is not None:
            real_idx = self.filtered_indices[view_idx]
        else:
            real_idx = view_idx
            
        # Get line text from engine
        if self.log_engine:
            line_text = self.log_engine.get_line(real_idx)
            await self.open_filter_dialog(initial_text=line_text.strip())

    async def on_log_area_tap(self, e: ft.TapEvent):
        # Calculate which row was clicked based on local_y
        local_y = get_event_prop(e, "local_y", 0)
        self.last_log_tap_y = local_y # Store for double tap usage
        
        row_height = self.ROW_HEIGHT
        row_idx = int(local_y / row_height)
        
        # --- WINDOWS ULTIMATE FIX: Direct OS Query ---
        ctrl = False
        shift = False
        
        if sys.platform == "win32":
            import ctypes
            # VK_CONTROL = 0x11, VK_SHIFT = 0x10
            # If the high-order bit is 1, the key is down (0x8000)
            ctrl = (ctypes.windll.user32.GetKeyState(0x11) & 0x8000) != 0
            shift = (ctypes.windll.user32.GetKeyState(0x10) & 0x8000) != 0
        else:
            # Fallback for other platforms
            ctrl = getattr(e, "ctrl", False)
            shift = getattr(e, "shift", False)
        
        # Call the existing click handler with mocked row_idx
        class MockEvent:
            def __init__(self, data, ctrl, shift):
                self.control = type('obj', (object,), {'data': data})
                self.ctrl = ctrl
                self.shift = shift
        
        mock_e = MockEvent(row_idx, ctrl, shift)
        await self.on_log_click(mock_e)

    async def on_log_area_secondary_tap(self, e: ft.TapEvent):
        local_y = get_event_prop(e, "local_y", 0)
        row_height = self.ROW_HEIGHT
        row_idx = int(local_y / row_height)
        
        class MockEvent:
            def __init__(self, data):
                self.control = type('obj', (object,), {'data': data})
        
        mock_e = MockEvent(row_idx)
        await self.on_log_right_click(mock_e)

    async def on_log_click(self, e):
        row_idx = e.control.data
        view_idx = self.current_start_index + row_idx
        
        # Determine total items matching update_log_view logic
        if self.show_only_filtered and self.filtered_indices is not None:
            total_items = len(self.filtered_indices)
        else:
            total_items = self.log_engine.line_count()
            
        if view_idx >= total_items: return
        
        # Map to real_idx matching update_log_view logic
        if self.show_only_filtered and self.filtered_indices is not None:
            real_idx = self.filtered_indices[view_idx]
        else:
            real_idx = view_idx
        
        # Determine modifiers passed from the tap handler
        ctrl = getattr(e, "ctrl", False)
        shift = getattr(e, "shift", False)
        
        if shift and self.selection_anchor != -1:
            # Range Selection
            start_view = self._get_view_index_from_raw(self.selection_anchor)
            if start_view is not None:
                low, high = min(start_view, view_idx), max(start_view, view_idx)
                if not ctrl: self.selected_indices.clear()
                for i in range(low, high + 1):
                    # 正確映射回真實索引
                    if self.show_only_filtered and self.filtered_indices is not None:
                        ridx = self.filtered_indices[i]
                    else:
                        ridx = i
                    self.selected_indices.add(ridx)
                # 注意：範圍選取後不更新 selection_anchor，保留原始起點以供連續選取
        elif ctrl:
            # Toggle Selection
            if real_idx in self.selected_indices:
                self.selected_indices.remove(real_idx)
            else:
                self.selected_indices.add(real_idx)
            self.selection_anchor = real_idx
        else:
            # Single Selection
            self.selected_indices = {real_idx}
            self.selection_anchor = real_idx
        
        await self.immediate_render()

    def _get_view_index_from_raw(self, raw_idx):
        """根據目前的視圖模式，將原始索引映射為視圖索引。"""
        # 如果目前是過濾模式，才需要查找過濾後的索引位置
        if self.show_only_filtered and self.filtered_indices is not None:
            import bisect
            idx = bisect.bisect_left(self.filtered_indices, raw_idx)
            if idx < len(self.filtered_indices) and self.filtered_indices[idx] == raw_idx:
                return idx
            return None
        
        # 全視圖模式下，視圖索引就等於原始索引
        return raw_idx

    async def copy_selected_lines(self, e=None):
        if not self.selected_indices or not self.log_engine:
            return
            
        # Sort indices to ensure chronological order in clipboard
        sorted_indices = sorted(list(self.selected_indices))
        
        # Batch fetch content from Rust
        try:
            # Use get_lines_batch if available, but only for text
            batch_data = self.log_engine.get_lines_batch(sorted_indices)
            lines = [item[0] for item in batch_data]
            text = "\n".join(lines)
            
            # Use the deprecated but functional method as per project notes
            await self.page.clipboard.set(text)
            
            self.show_toast(f"Copied {len(lines)} lines to clipboard.")
        except Exception as ex:
            print(f"Copy Error: {ex}")

    async def on_log_right_click(self, e):
        # e.control.data contains the row index
        row_idx = e.control.data
        view_idx = self.current_start_index + row_idx
        
        # Map view index to real log index
        if self.filtered_indices is not None:
            if view_idx >= len(self.filtered_indices): return
            real_idx = self.filtered_indices[view_idx]
        else:
            real_idx = view_idx
        
        if not self.log_engine or real_idx >= self.log_engine.line_count():
            return

        # Create actions for the context menu
        def close_dlg(e):
            self.context_menu_dlg.open = False
            self.page.update()

        # Using AlertDialog as a simple context menu
        copy_label = f"Copy Line" if len(self.selected_indices) <= 1 else f"Copy {len(self.selected_indices)} Lines"
        
        self.context_menu_dlg = ft.AlertDialog(
            title=ft.Text(f"Line {real_idx + 1} Actions"),
            content=ft.Column([
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.COPY), 
                    title=ft.Text(copy_label), 
                    on_click=lambda _: [asyncio.create_task(self.copy_selected_lines()), close_dlg(None)]
                ),
                ft.ListTile(
                    leading=ft.Icon(ft.Icons.ADD), 
                    title=ft.Text("Add Filter from Line"), 
                    on_click=lambda _: [asyncio.create_task(self.on_log_double_click(e)), close_dlg(None)]
                ),
            ], height=140, width=300),
            actions=[
                ft.TextButton("Cancel", on_click=close_dlg),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.context_menu_dlg.open = True
        self.page.show_dialog(self.context_menu_dlg)
        self.page.update()

    async def load_file(self, path):
        """載入 Log 檔案。"""
        if not path: return
        # 清理路徑
        clean_path = path.strip().strip('\"\'')
        await self._run_safe_async(self._perform_load_logic(clean_path), f"Loading {os.path.basename(clean_path)}")

    def update_status_bar(self):
        """更新底部狀態列的行數統計資訊。"""
        if not self.log_engine:
            self.status_text.value = "Ready"
        else:
            total = self.log_engine.line_count()
            # 決定目前「顯示」的行數
            if self.show_only_filtered and self.filtered_indices is not None:
                shown = len(self.filtered_indices)
            else:
                shown = total
            
            self.status_text.value = f"Showing {shown:,} lines (Total {total:,})"
        
        if hasattr(self, "status_text") and self.status_text.page:
            self.status_text.update()

    def show_toast(self, message, is_error=False, duration=3.0):
        """Displays a custom toast notification in the overlay."""
        is_dark = self.page.theme_mode == ft.ThemeMode.DARK
        
        if is_error:
            bg_color = ft.Colors.RED_800
            fg_color = ft.Colors.WHITE
        else:
            # Theme-aware colors: Dark mode uses dark grey, Light mode uses soft grey/white
            bg_color = "#333333" if is_dark else "#E0E0E0"
            fg_color = ft.Colors.WHITE if is_dark else ft.Colors.BLACK
        
        # Create the toast content
        toast_content = ft.Container(
            content=ft.Text(message, color=fg_color, size=13, weight=ft.FontWeight.W_500),
            bgcolor=bg_color,
            padding=ft.padding.symmetric(horizontal=15, vertical=8),
            border_radius=8,
            opacity=0, # Start hidden for fade-in
            animate_opacity=300,
            alignment=ft.Alignment(0, 0), # Center content inside toast
            shadow=ft.BoxShadow(
                blur_radius=10, 
                color=ft.Colors.with_opacity(0.3, ft.Colors.BLACK if is_dark else ft.Colors.GREY_700)
            ),
        )
        
        # Wrapper for positioning at bottom center
        toast_wrapper = ft.Container(
            content=ft.Row(
                [toast_content], 
                alignment=ft.MainAxisAlignment.CENTER,
            ),
            bottom=50,
            left=0,
            right=0,
        )
        
        self.page.overlay.append(toast_wrapper)
        self.page.update()
        
        # Trigger Fade In
        toast_content.opacity = 1
        toast_content.update()
        
        # Auto-remove task
        async def _remove_toast():
            await asyncio.sleep(duration)
            try:
                # Fade Out
                toast_content.opacity = 0
                toast_content.update()
                await asyncio.sleep(0.3) # Wait for animation
                
                if toast_wrapper in self.page.overlay:
                    self.page.overlay.remove(toast_wrapper)
                    self.page.update()
            except Exception:
                pass # Page might be closed

        asyncio.create_task(_remove_toast())

    async def _perform_load_logic(self, path):
        """實際的檔案載入與引擎初始化邏輯。"""
        start_time = time.time()
        
        # 初始化引擎
        if HAS_RUST:
             self.log_engine = _REAL_LOG_ENGINE(path)
        else:
             self.log_engine = _REAL_LOG_ENGINE(path)
        
        line_count = self.log_engine.line_count()
        duration = time.time() - start_time
        
        self.file_path = path
        self.update_title()
        self.add_to_recent_files(path)
        
        # 更新 UI
        self.initial_content.visible = False
        self.log_view_area.visible = True
        
        # 重置狀態
        self.target_start_index = 0
        self.current_start_index = 0
        self.selected_indices = {0} if line_count > 0 else set()
        self.selection_anchor = 0 if line_count > 0 else -1
        
        # 同步各組件
        await self.on_resize(None)
        await self._perform_filtering_logic() # 直接呼叫邏輯避免二次 Status 更新
        
        self.update_log_view()
        engine_type = "Rust" if HAS_RUST else "Mock"
        
        # Show load stats in SnackBar instead of overwriting Status Bar
        load_msg = f"[{engine_type}] Loaded {os.path.basename(path)} ({line_count:,} lines) in {duration:.3f}s"
        self.show_toast(load_msg)
        
        self.needs_render = True

async def main(page: ft.Page):
    # 階段 1 最終優化：main() 僅負責引導啟動
    # 所有初始化邏輯（設定、背景服務、UI）均在類別內部完成
    app = LogAnalyzerApp(page)

    # --- CLI Argument Handling ---
    import argparse
    import glob
    
    parser = argparse.ArgumentParser(description="Log Analyzer Flet", fromfile_prefix_chars='@')
    parser.add_argument("logs", nargs="*", help="Log files to open")
    parser.add_argument("-f", "--filter", help="Filter file to load (.tat)")
    
    # Use parse_known_args to avoid conflict with Flet arguments
    args, _ = parser.parse_known_args()
    
    if args.filter:
        await app._run_safe_async(app._perform_import_filters_logic(args.filter), "Loading Filters from CLI")
        
    if args.logs:
        final_logs = []
        for log_arg in args.logs:
            # Handle Wildcards (for CMD where shell doesn't expand)
            if any(c in log_arg for c in '*?['):
                expanded = glob.glob(log_arg)
                if expanded:
                    final_logs.extend(expanded)
                else:
                    final_logs.append(log_arg)
            else:
                final_logs.append(log_arg)
        
        # Load logs sequentially
        for log_file in final_logs:
            await app.load_file(log_file)

if __name__ == "__main__":
    # 使用隱藏啟動以防閃爍
    ft.app(main, view=ft.AppView.FLET_APP_HIDDEN)
