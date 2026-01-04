import flet as ft
import os
import sys
import time
import asyncio
import json
import re
import threading
import bisect
import webbrowser
import tkinter as tk
from tkinter import filedialog

from log_analyzer.core.engine import LogEngine, MockLogEngine, HAS_RUST
from log_analyzer.core.filter import Filter
from log_analyzer.ui.theme import ThemeColors
from log_analyzer.utils.helpers import get_luminance, adjust_color_for_theme, get_event_prop
from log_analyzer.ui.components.top_bar import TopBar
from log_analyzer.ui.components.sidebar import Sidebar
from log_analyzer.ui.components.search_bar import SearchBar
from log_analyzer.ui.components.status_bar import StatusBar
from log_analyzer.ui.dialogs import Dialogs
from log_analyzer.core.navigation import NavigationController

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

        # App Info
        self.APP_NAME = "Log Analyzer (Flet Edition)"
        self.VERSION = "V1.7" # To be updated manually for releases

        # Search History
        self.search_history = []

        # App 引擎與路徑
        self.log_engine = None
        self.file_path = None

        # 滾動與渲染控制
        self.is_programmatic_scroll = False
        self.last_slider_update = 0
        self.last_render_time = 0
        self.target_start_index = 0
        self.current_start_index = 0
        self.loaded_count = 0
        self.BATCH_SIZE = 200

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
        self.last_log_tap_y = 0

        # Focus Management
        self.active_pane = "log"  # "log" or "filter"
        self.selected_filter_index = -1

        # 系統標記
        self.is_closing = False
        self.is_picking_file = False

        # UI Components
        self.top_bar_comp = TopBar(self)
        self.sidebar_comp = Sidebar(self)
        self.search_bar_comp = SearchBar(self)
        self.status_bar_comp = StatusBar(self)
        self.dialogs = Dialogs(self)

        # Navigation Controller
        self.navigator = NavigationController(self)

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
            "search_history": [],
            "window_maximized": False,
            "main_window_geometry": "1200x800+100+100",
            "note_view_visible": False,
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
        async def on_save(e):
            self.dialogs.dialog.open = False
            self.page.update()
            # 嘗試儲存
            await self.save_tat_filters()
            # 如果儲存成功 (dirty flag 被清除)，則關閉程式
            if not self.filters_dirty:
                self.save_config()
                await self.page.window.destroy()

        async def on_dont_save(e):
            self.dialogs.dialog.open = False
            self.page.update()
            # 不儲存直接關閉
            self.save_config()
            await self.page.window.destroy()

        def on_cancel(e):
            self.dialogs.dialog.open = False
            self.page.update()

        self.dialogs.show_unsaved_changes_dialog(on_save, on_dont_save, on_cancel)

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

    def _get_colors(self):
        """獲取當前主題模式的顏色表。"""
        return ThemeColors.get(self.page.theme_mode)

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

        self.log_list_column = ft.ListView(
            expand=True,
            spacing=0,
            item_extent=self.ROW_HEIGHT,
            padding=0,
            on_scroll=self.on_log_list_scroll,
        )
        # Handle API difference for scroll interval
        if hasattr(self.log_list_column, "on_scroll_interval"):
             self.log_list_column.on_scroll_interval = 10
        elif hasattr(self.log_list_column, "scroll_interval"):
             self.log_list_column.scroll_interval = 10

        self.log_display_column = ft.Container(
            content=ft.GestureDetector(
                content=self.log_list_column,
                on_tap_down=self.on_log_area_tap,
                on_double_tap=self.on_log_area_double_tap,
                on_secondary_tap_down=self.on_log_area_secondary_tap,
                expand=True
            ),
            expand=True,
            bgcolor=colors["log_bg"],
        )

        # Log 區域容器
        self.log_view_area = ft.Container(
            content=self.log_display_column,
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

        # Dummy focus target for Log View
        # Use a transparent button to accept focus but not obstruct view
        self.log_focus_target = ft.TextField(
            value="", width=1, height=1, opacity=0, read_only=True, border_width=0
        )

        return ft.Stack(
            controls=[
                ft.Column(
                    controls=[
                        self.initial_content,
                        self.log_view_area
                    ],
                    spacing=0,
                    expand=True,
                    alignment=ft.MainAxisAlignment.START,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH
                ),
                self.log_focus_target
            ],
            expand=True
        )

    def build_ui(self, update_page=True):
        # --- Theme-Aware Colors ---
        colors = self._get_colors()

        # 同步更新頁面背景色
        self.page.bgcolor = colors["sidebar_bg"]

        # 1. 構建各個模組
        self.top_bar = self.top_bar_comp.build()
        self.sidebar = self.sidebar_comp.build()
        self.log_area_comp = self._build_log_view()
        self.search_bar = self.search_bar_comp.build()
        self.status_bar = self.status_bar_comp.build()

        # 3. Main Layout Assembly
        # Wrap log area in a Stack to overlay the Search Bar
        self.log_stack = ft.Stack([
            self.log_area_comp,
            ft.Container(
                content=self.search_bar,
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
        self.top_bar_comp.update_colors()
        self.sidebar_comp.update_colors()
        self.search_bar_comp.update_colors()
        self.status_bar_comp.update_colors()

        # 4. Log 區域
        if hasattr(self, "log_display_column"):
            self.log_display_column.bgcolor = colors["log_bg"]
        if hasattr(self, "initial_content"):
            self.initial_content.bgcolor = colors["log_bg"]

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
        # 這裡不直接銷毀，而是呼叫我們的關閉處理器，讓它可以檢查 unsaved changes
        await self.handle_app_close(e)

    def update_recent_files_menu(self):
        recent = self.config.get("recent_files", [])
        if self.top_bar_comp.recent_files_submenu:
            self.top_bar_comp.recent_files_submenu.controls.clear()

            if not recent:
                self.top_bar_comp.recent_files_submenu.controls.append(
                    ft.MenuItemButton(content=ft.Text("No recent files"), disabled=True)
                )
            else:
                # Closure helper to capture path
                def create_click_handler(p):
                    return lambda _: asyncio.create_task(self.load_file(p))

                for path in recent:
                    self.top_bar_comp.recent_files_submenu.controls.append(
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
        if self.top_bar_comp.menu_bar:
            self.top_bar_comp.menu_bar.update()

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
        for f_node in root.iter('filter'): # Explicitly iterate 'filter' tags
            en = f_node.get('enabled', 'y').lower() == 'y'
            # Compatible with both 'exclude' and 'excluding'
            exc_attr = f_node.get('exclude', f_node.get('excluding', 'n')).lower()
            exc = exc_attr == 'y'

            # Compatible with both 'regex' and 'case_sensitive' for determining regex
            reg_attr = f_node.get('regex', f_node.get('case_sensitive', 'n')).lower()
            reg = reg_attr == 'y'

            fg = f_node.get('foreColor', '000000')
            bg = f_node.get('backColor', 'ffffff')
            if not fg.startswith("#"): fg = "#" + fg
            if not bg.startswith("#"): bg = "#" + bg

            # For btm.tat, text is an attribute
            text = f_node.get('text')
            if text is None: # For older format, text might be directly inside tag
                text = f_node.text if f_node.text else ""

            new_filters.append(Filter(text, fg, bg, en, reg, exc))
        if new_filters:
            self.filters.extend(new_filters)
            await self.render_filters()
            await self._perform_filtering_logic()
            self.config["last_filter_dir"] = os.path.dirname(path)
            self.current_tat_path = path
            self.filters_dirty = False
            self.update_title()

            # 如果側邊欄是關閉的，載入 Filter 後自動開啟
            if not self.sidebar.visible:
                self.toggle_sidebar()

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
        xml_content = '<?xml version="1.0" encoding="utf-8" standalone="yes"?>\n'
        xml_content += '<TextAnalysisTool.NET version="2017-01-24" showOnlyFilteredLines="True">\n'
        xml_content += '  <filters>\n'
        for f in self.filters:
            xml_content += f"    {f.to_tat_xml()}\n"
        xml_content += '  </filters>\n'
        xml_content += '</TextAnalysisTool.NET>'
        with open(path, 'w', encoding='utf-8') as f:
            f.write(xml_content)
        self.config["last_filter_dir"] = os.path.dirname(path)
        self.current_tat_path = path
        self.filters_dirty = False
        self.update_title()
        self.save_config()
        return "Filters saved successfully"

    def toggle_sidebar(self):
        self.sidebar.visible = not self.sidebar.visible
        # Force a layout recalculation in case the sidebar position affects the log view (e.g. bottom mode)
        asyncio.create_task(self.on_resize(None))
        self.page.update()

    async def set_active_pane(self, pane):
        self.active_pane = pane
        if pane == "filter":
            # Ensure a valid selection if none exists
            if self.filters and self.selected_filter_index == -1:
                self.selected_filter_index = 0
                asyncio.create_task(self.render_filters())

            # Request focus on sidebar dummy target
            if hasattr(self.sidebar_comp, 'sidebar_focus_target'):
                try:
                    await self.sidebar_comp.sidebar_focus_target.focus()
                except Exception: pass
        elif pane == "log":
            # Clear filter selection visual
            if self.selected_filter_index != -1:
                self.selected_filter_index = -1
                asyncio.create_task(self.render_filters())

            try:
                await self.log_focus_target.focus()
            except Exception: pass

    def change_sidebar_position(self, pos):
        """更改側邊欄位置並重建佈局。"""
        self.config["sidebar_position"] = pos
        self.save_config()

        # Save current state
        was_visible = self.sidebar.visible

        # 重新建構 UI 以套用佈局變更
        self.build_ui()

        # Restore state
        self.sidebar.visible = was_visible

        if self.log_engine:
             self.initial_content.visible = False
             self.log_view_area.visible = True
             # Force recalculate layout metrics before updating view
             asyncio.create_task(self.on_resize(None))

             self.reload_log_view()

        # 重建 UI 後需確保過濾器列表正確渲染
        asyncio.create_task(self.render_filters())
        self.page.update()

    def update_title(self):
        log_name = os.path.basename(self.file_path) if self.file_path else "No file loaded"
        filter_name = os.path.basename(self.current_tat_path) if self.current_tat_path else "No filter file"
        title_str = f"[{log_name}] - [{filter_name}] - LogAnalyzer"

        self.page.title = title_str
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
        self.sidebar_comp.filter_list_view.update() # 強制局部刷新以處理 ReorderableListView 的 key 變更

        if self.log_engine:
            # 更新 Log 每一行的顏色
            self.reload_log_view()
            # 更新時間軸已移除 (Timeline removed)

        # 5. 保存設定並更新
        self.save_config()
        self.page.update()


    async def show_search_bar(self):
        self.search_bar.visible = True
        self.active_pane = "search" # Prevent keyboard navigation interference

        # Reset count display on show, as per user request to clear record before new search
        self.update_results_count("")

        self.page.update() # First update to make it visible

        # Then focus
        try:
            await self.search_bar_comp.search_input.focus()
        except Exception:
            pass

        self.page.update() # Second update to ensure focus state is rendered

    async def hide_search_bar(self, e=None):
        self.search_bar.visible = False
        self.search_results = []
        self.current_search_idx = -1
        self.reload_log_view()
        self.page.update()

    async def on_find_next(self, e=None):
        await self.perform_search(backward=False)

    async def on_find_prev(self, e=None):
        await self.perform_search(backward=True)

    async def perform_search(self, backward=False):
        if not self.log_engine: return

        query = self.search_bar_comp.search_input.value
        if not query:
            self.search_results = []
            self.current_search_idx = -1
            self.reload_log_view()
            return

        # Check if we need to perform a new search (query changed or results cleared)
        is_new_search = (query != self.search_query or not self.search_results)

        if is_new_search:
            # Update history
            if query and query.strip():
                if query in self.search_history:
                    self.search_history.remove(query)
                self.search_history.insert(0, query)
                if len(self.search_history) > 10:
                    self.search_history.pop()

                # Update UI history menu if component exists
                if self.search_bar_comp:
                    self.search_bar_comp.update_history_menu()

            self.search_query = query
            # Call Rust engine search (returns list of raw indices)
            self.search_results = await asyncio.to_thread(
                self.log_engine.search, query, False, self.search_case_sensitive
            )

            if not self.search_results:
                self.update_results_count("0/0")
                self.status_bar_comp.update_status(f"No results for '{query}'")
                self.page.update()
                return

            # Find nearest starting point relative to current position
            current_raw = self.selection_anchor
            if current_raw == -1:
                # Map current start index to raw
                if self.show_only_filtered and self.filtered_indices is not None:
                    if self.current_start_index < len(self.filtered_indices):
                        current_raw = self.filtered_indices[self.current_start_index]
                    else:
                        current_raw = 0
                else:
                    current_raw = self.current_start_index

            # --- "Find Nearest" Logic ---
            if backward:
                # Find insertion point (left). Elements to left are < current_raw.
                # If current_raw is a match, bisect_left returns its index.
                # We want the previous match, so idx - 1.
                idx = bisect.bisect_left(self.search_results, current_raw)
                self.current_search_idx = idx - 1
                # Wrap around if needed (start from end if currently at beginning)
                if self.current_search_idx < 0:
                    self.current_search_idx = len(self.search_results) - 1
            else:
                # Find insertion point (right). Elements to right are > current_raw.
                # If current_raw is a match, bisect_right returns index + 1 (next match).
                idx = bisect.bisect_right(self.search_results, current_raw)
                self.current_search_idx = idx
                # Wrap around if needed (start from beginning if currently at end)
                if self.current_search_idx >= len(self.search_results):
                    self.current_search_idx = 0

        else:
            # --- "Find Next" Logic (Existing Results) ---
            if not self.search_results: return

            if backward:
                if self.current_search_idx <= 0:
                    if self.search_wrap:
                        self.current_search_idx = len(self.search_results) - 1
                    else:
                        self.status_bar_comp.update_status("Reached Top")
                        self.page.update()
                        return
                else:
                    self.current_search_idx -= 1
            else:
                if self.current_search_idx >= len(self.search_results) - 1:
                    if self.search_wrap:
                        self.current_search_idx = 0
                    else:
                        self.status_bar_comp.update_status("Reached Bottom")
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

        # If the search result is filtered out, switch to Full View
        if target_view_idx is None:
            await self.toggle_show_filtered()
            target_view_idx = target_raw_idx # In full view, view index == raw index
            self.show_toast(f"Switched to Full View to show result on line {target_raw_idx+1}")

        # Execute jump (this handles rendering)
        self.jump_to_index(target_view_idx, immediate=True, center=True)

        # Ensure focus stays on search input if we are in search mode,
        # to allow repeated Enter presses to trigger on_submit
        if self.active_pane == "search":
            try:
                await self.search_bar_comp.search_input.focus()
            except Exception: pass

    def update_results_count(self, text):
        self.search_bar_comp.search_results_count.value = text
        self.page.update()

    async def on_log_list_scroll(self, e: ft.OnScrollEvent):
        """Handle native scrolling for infinite scroll behavior."""
        if e.pixels >= e.max_scroll_extent - 100:
            await self.load_more_logs()

    def reload_log_view(self, start_index=0):
        """
        Resets and repopulates the ListView starting from a specific index.
        This effectively 'teleports' the view window.
        """
        if not self.log_engine: return

        # PRE-CALCULATE filter colors logic
        # We need this to ensure we have fresh colors when reloading view
        self._filter_color_cache = {}
        is_dark = self.page.theme_mode == ft.ThemeMode.DARK
        if self.filters:
            active_filters_objs = []
            for f in self.filters:
                if f.enabled and f.text:
                    active_filters_objs.append(f)
                    idx = len(active_filters_objs) - 1
                    self._filter_color_cache[idx] = (
                        adjust_color_for_theme(f.back_color, True, is_dark),
                        adjust_color_for_theme(f.fore_color, False, is_dark)
                    )

        # Determine valid start index
        total_items = self.navigator.total_items

        # Improve Context: When jumping, we want to see lines BEFORE the target.
        # So we shift the start index back by 50 lines (if possible).
        context_lines = 50
        adjusted_start = max(0, start_index - context_lines)

        # Clamp to bounds
        adjusted_start = max(0, min(adjusted_start, total_items - 1)) if total_items > 0 else 0

        self.loaded_count = adjusted_start # We start loading FROM here
        self.log_list_column.controls.clear()

        # Load first batch
        asyncio.create_task(self.load_more_logs())

    async def load_more_logs(self):
        """Appends the next batch of logs to the ListView."""
        if not self.log_engine: return

        # Prevent concurrent loads if we wanted (not strictly needed with async/await on UI thread)
        # But helpful to debounce
        if hasattr(self, "_is_loading_more") and self._is_loading_more: return
        self._is_loading_more = True

        try:
            total_items = self.navigator.total_items
            if self.loaded_count >= total_items:
                return

            # Determine range
            start_idx = self.loaded_count
            end_idx = min(start_idx + self.BATCH_SIZE, total_items)

            # Prepare indices
            target_indices = []
            for i in range(start_idx, end_idx):
                real_idx = self.filtered_indices[i] if (self.show_only_filtered and self.filtered_indices is not None) else i
                target_indices.append(real_idx)

            if not target_indices: return

            # Fetch Data
            batch_data = []
            if getattr(self.log_engine, 'get_lines_batch', None):
                batch_data = self.log_engine.get_lines_batch(target_indices)

            # Colors setup
            is_dark = self.page.theme_mode == ft.ThemeMode.DARK
            c_default = "#d4d4d4" if is_dark else "#1e1e1e"
            c_error = "#ff6b6b"
            c_warn = "#ffd93d"
            c_info = "#4dabf7"
            c_select_bg = "#264f78" if is_dark else "#b3d7ff"

            # Use cached filter colors if available
            filter_cache = getattr(self, "_filter_color_cache", {})
            _line_tags_codes = self.line_tags_codes

            # Search setup
            search_query = self.search_bar_comp.search_input.value
            search_active = bool(search_query and self.search_bar.visible)

            # Prepare controls
            new_controls = []
            for i, (line_data, level_code) in enumerate(batch_data):
                real_idx = target_indices[i]

                # Colors logic
                if level_code == 1: base_color = c_error
                elif level_code == 2: base_color = c_warn
                elif level_code == 3: base_color = c_info
                else: base_color = c_default

                # Apply Filter Colors
                bg_color = ft.Colors.TRANSPARENT
                if _line_tags_codes is not None and real_idx < len(_line_tags_codes):
                    tag_code = _line_tags_codes[real_idx]
                    if tag_code >= 2:
                        af_idx = tag_code - 2
                        if af_idx in filter_cache:
                            f_bg, f_fg = filter_cache[af_idx]
                            if f_bg: bg_color = f_bg
                            if f_fg: base_color = f_fg
                    elif tag_code == 1:
                        base_color = ft.Colors.GREY_500 if is_dark else ft.Colors.GREY_400

                # Selection BG overrides filter BG
                if real_idx in self.selected_indices:
                     bg_color = c_select_bg

                t = ft.Text(
                    font_family="Consolas, monospace",
                    size=self.FONT_SIZE,
                    no_wrap=True,
                    color=base_color,
                )

                if search_active and search_query.lower() in line_data.lower():
                    # Search Highlight Logic
                    h_bg = ft.Colors.YELLOW
                    h_fg = ft.Colors.BLACK
                    if bg_color != ft.Colors.TRANSPARENT and get_luminance(bg_color) > 0.6:
                         h_bg = ft.Colors.BLUE_800
                         h_fg = ft.Colors.WHITE

                    try:
                        parts = re.split(f"({re.escape(search_query)})", line_data, flags=re.IGNORECASE)
                        t.spans = [
                            ft.TextSpan(p, style=ft.TextStyle(bgcolor=h_bg, color=h_fg, weight=ft.FontWeight.BOLD))
                            if p.lower() == search_query.lower() else ft.TextSpan(p, style=ft.TextStyle(color=base_color))
                            for p in parts
                        ]
                    except Exception:
                        t.value = line_data
                else:
                    t.value = line_data

                c = ft.Container(
                    content=t,
                    height=self.ROW_HEIGHT,
                    alignment=ft.Alignment(-1, 0),
                    bgcolor=bg_color,
                    on_click=self.on_log_row_click,
                    data=start_idx + i
                )
                new_controls.append(c)

            self.log_list_column.controls.extend(new_controls)
            self.loaded_count = end_idx
            self.log_list_column.update()

            # Yield slightly to prevent UI freeze on rapid updates
            await asyncio.sleep(0.01)

        finally:
            self._is_loading_more = False

    async def on_log_row_click(self, e):
        # Handle click on row to select
        # Use data as index
        view_idx = e.control.data

        # Map to real idx
        if self.show_only_filtered and self.filtered_indices is not None:
             real_idx = self.filtered_indices[view_idx]
        else:
             real_idx = view_idx

        self.selected_indices = {real_idx}
        self.selection_anchor = real_idx

        # Visual update is hard with ListView without rebuilding or finding control
        # For performance, maybe we don't highlight background on tap?
        # Or we rely on rebuilding if user really needs it.
        # Ideally we iterate controls to unset old and set new, but that's slow.
        # User accepted standard ListView behavior. Selection highlight is secondary to scroll perf.
        # We'll just show status.
        self.status_bar_comp.update_status(f"Selected Line {real_idx + 1}")

    def jump_to_index(self, idx, update_slider=True, immediate=False, center=False):
        """
        Jumps to a specific line index.
        In the new ListView architecture, this means reloading the view starting from that index.
        """
        # Calculate start index to show context if centering
        target_idx = int(idx)
        if center:
            target_idx = max(0, target_idx - 10) # Show some context lines above

        self.reload_log_view(start_index=target_idx)

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
            # Restore focus to log view after closing search
            if self.active_pane == "search":
                await self.set_active_pane("log")
            return
        if e.key == "F2":
            await self.perform_search(backward=True)
            return
        if e.key == "F3":
            await self.perform_search(backward=e.shift)
            return
        # --- Context-Aware Navigation ---

        # If search is active, do not navigate logs/filters with keys
        # unless specialized keys are handled above (like Enter/F3)
        if self.active_pane == "search":
            # Let TextField.on_submit handle Enter to avoid double triggering search
            if e.key == "Enter":
                return

            # Allow F3 to work even while typing
            if e.key == "F3":
                await self.perform_search(backward=e.shift)
                return

            return

        if e.key == "Enter" and self.search_bar.visible:
            await self.perform_search(backward=e.shift)
            return

        if self.active_pane == "filter":
            await self._handle_filter_navigation(e)
        else:
            await self._handle_log_navigation(e)

    async def _handle_filter_navigation(self, e):
        # Force focus back to sidebar to prevent wandering
        if hasattr(self.sidebar_comp, 'sidebar_focus_target'):
            try:
                await self.sidebar_comp.sidebar_focus_target.focus()
            except Exception: pass

        if not self.filters: return

        idx = self.selected_filter_index
        if idx == -1: idx = 0

        if e.key == " ":
            # Toggle enabled state
            if 0 <= idx < len(self.filters):
                f = self.filters[idx]
                f.enabled = not f.enabled
                self.filters_dirty = True
                await self.render_filters() # Re-render to update checkbox and selection
                await self.apply_filters()
            return

        if e.key in ["ArrowDown", "Arrow Down"]:
            idx += 1
        elif e.key in ["ArrowUp", "Arrow Up"]:
            idx -= 1
        else:
            return

        # Clamp
        idx = max(0, min(idx, len(self.filters) - 1))

        if idx != self.selected_filter_index:
            old_idx = self.selected_filter_index
            self.selected_filter_index = idx
            await self.update_filter_selection_visuals(old_idx, idx)

    async def _handle_log_navigation(self, e):
        # Force focus back to log view to prevent wandering
        try:
            await self.log_focus_target.focus()
        except Exception: pass

        # Determine total items
        total_items = self.navigator.total_items
        if total_items == 0: return

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

    async def on_resize(self, e):
        # Update scrollbar track height info
        if self.page.height:
            # Check if initial content is hidden
            is_initial = self.initial_content.visible
            status_h = self.status_bar.height if self.status_bar.height else 30
            menu_h = self.top_bar.height if self.top_bar.height else 40

            # Sidebar adjustment if at bottom
            sidebar_h = 0
            if self.config.get("sidebar_position") == "bottom" and self.sidebar.visible:
                sidebar_h = 200 # Fixed height from sidebar.py

            # Safe margin calculation
            self.scrollbar_track_height = self.page.height - status_h - menu_h - sidebar_h

            # Dynamic LINES_PER_PAGE
            line_height = self.ROW_HEIGHT
            if self.scrollbar_track_height > 0:
                # Calculate exactly how many rows fit in the track
                new_lines_per_page = int((self.scrollbar_track_height - 10) / line_height)
                # Clamp to pool size
                new_lines_per_page = max(10, min(new_lines_per_page, self.TEXT_POOL_SIZE))

                if new_lines_per_page != self.LINES_PER_PAGE:
                    self.LINES_PER_PAGE = new_lines_per_page
                    # Only reload if we are in initial state or small view,
                    # otherwise infinite scroll handles it.
                    # But actually reload_log_view clears the list, so we might skip this.
                    # If we really want to force update on resize, we can call:
                    # self.reload_log_view(self.current_start_index)
                    pass

            # No longer need manual height setting or sync
            pass

        self.page.update()

    def sync_scrollbar_position(self):
        # Deprecated: Native scrollbar handles itself
        pass

    async def toggle_show_filtered(self, e=None):
        self.show_only_filtered = not self.show_only_filtered
        self.show_toast(f"Mode: {'Filtered Only' if self.show_only_filtered else 'Full View'}")
        self.current_start_index = 0 # Reset to top
        self.update_status_bar() # Update line counts in status bar
        self.reload_log_view()
        self.sync_scrollbar_position()
        self.page.update()

    async def _run_safe_async(self, coro, status_msg=None):
        """
        通用的非同步任務執行器。
        提供統一的錯誤捕捉、Log 紀錄與 SnackBar 提示，防止 UI 崩潰。
        """
        if status_msg:
            self.status_bar_comp.update_status(f"{status_msg}...")

        try:
            result = await coro
            # If the coroutine returns a result message, show it as a Toast
            if isinstance(result, str) and status_msg:
                self.show_toast(result)

            # Clean up status bar if it's still showing the transient progress message
            if status_msg and self.status_bar_comp.status_text.value == f"{status_msg}...":
                self.status_bar_comp.update_status("Ready")

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
        self.reload_log_view()

    async def on_add_filter_click(self, e):
        # Instead of adding directly, open the dialog
        await self.open_filter_dialog()

    async def open_filter_dialog(self, filter_obj=None, index=None, initial_text=None):
        async def on_save():
            await self.render_filters()
            await self.apply_filters()

        self.dialogs.show_filter_dialog(filter_obj, initial_text, on_save)

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
        self.sidebar_comp.filter_list_view.controls.clear()
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

            # --- Selection Highlight Logic ---
            is_selected = (i == self.selected_filter_index)
            border = ft.border.all(2, ft.Colors.BLUE) if is_selected else None
            bg_color = ft.Colors.with_opacity(0.1, ft.Colors.BLUE) if is_selected else None

            async def on_tap(e, idx=i):
                old_idx = self.selected_filter_index
                self.selected_filter_index = idx

                # Run visual update and focus switch concurrently to reduce perceived delay
                await asyncio.gather(
                    self.update_filter_selection_visuals(old_idx, idx),
                    self.set_active_pane("filter")
                )

            item_row = ft.GestureDetector(
                key=f"{id(f)}_{is_dark}", # 關鍵：包含主題資訊，強制主題切換時完全重繪
                content=ft.Container(
                    content=ft.Row([
                        cb,
                        lbl_tag,
                        hit_badge
                    ], spacing=2, alignment=ft.MainAxisAlignment.START),
                    padding=ft.padding.only(right=35, left=5), # 為 ReorderableListView 的拖曳手把留出空間
                    height=28, # Enforce compact height
                    border=border,
                    bgcolor=bg_color,
                    border_radius=5,
                ),
                on_tap=on_tap,
                on_double_tap=on_double_tap,
                on_secondary_tap=on_secondary_tap,
            )
            # Ensure the row doesn't end up in the tab cycle
            item_row.tab_index = -1

            self.sidebar_comp.filter_list_view.controls.append(item_row)

        if update_page:
            self.page.update()

    async def update_filter_selection_visuals(self, old_idx, new_idx):
        """Updates the visual selection state of filters without full re-render."""
        controls = self.sidebar_comp.filter_list_view.controls

        # Helper to apply style
        def apply_style(idx, is_sel):
            if 0 <= idx < len(controls):
                container = controls[idx].content
                container.border = ft.border.all(2, ft.Colors.BLUE) if is_sel else None
                container.bgcolor = ft.Colors.with_opacity(0.1, ft.Colors.BLUE) if is_sel else None
                container.update()

        if old_idx != -1 and old_idx != new_idx:
            apply_style(old_idx, False)

        if new_idx != -1:
            apply_style(new_idx, True)

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
        self.dialogs.show_filter_context_menu(obj)

    def _get_row_index_from_local_y(self, local_y):
        """Converts local Y coordinate to row index."""
        return int(local_y / self.ROW_HEIGHT)

    async def on_log_area_double_tap(self, e):
        # Double tap event in Flet doesn't provide coordinates,
        # so we use the one captured by the last on_tap_down
        local_y = getattr(self, "last_log_tap_y", 0)
        row_idx = self._get_row_index_from_local_y(local_y)

        class MockEvent:
            def __init__(self, data):
                self.control = type('obj', (object,), {'data': data})

        mock_e = MockEvent(row_idx)
        await self.on_log_double_click(mock_e)

    async def on_log_double_click(self, e):
        row_idx = e.control.data
        view_idx = self.current_start_index + row_idx

        # Determine total items
        total_items = self.navigator.total_items

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
        await self.set_active_pane("log")

        # Calculate which row was clicked based on local_y
        local_y = get_event_prop(e, "local_y", 0)
        self.last_log_tap_y = local_y # Store for double tap usage

        row_idx = self._get_row_index_from_local_y(local_y)

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
        row_idx = self._get_row_index_from_local_y(local_y)

        class MockEvent:
            def __init__(self, data):
                self.control = type('obj', (object,), {'data': data})

        mock_e = MockEvent(row_idx)
        await self.on_log_right_click(mock_e)

    async def on_log_click(self, e):
        row_idx = e.control.data
        view_idx = self.current_start_index + row_idx

        # Determine total items matching update_log_view logic
        total_items = self.navigator.total_items

        if view_idx >= total_items: return

        # Map to real_idx matching reload_log_view logic
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

        def on_copy():
            asyncio.create_task(self.copy_selected_lines())

        def on_add_filter():
            asyncio.create_task(self.on_log_double_click(e))

        self.dialogs.show_log_context_menu(real_idx, on_copy, on_add_filter)

    async def load_file(self, path):
        """載入 Log 檔案。"""
        if not path: return
        # 清理路徑
        clean_path = path.strip().strip('\"\'')
        await self._run_safe_async(self._perform_load_logic(clean_path), f"Loading {os.path.basename(clean_path)}")

    def update_status_bar(self):
        """更新底部狀態列的行數統計資訊。"""
        if not self.log_engine:
            self.status_bar_comp.update_status("Ready")
        else:
            total = self.log_engine.line_count()
            # 決定目前「顯示」的行數
            if self.show_only_filtered and self.filtered_indices is not None:
                shown = len(self.filtered_indices)
            else:
                shown = total

            self.status_bar_comp.update_status(f"Showing {shown:,} lines (Total {total:,})")

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

    # --- [Helper] Path Resource Finder ---
    def resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    async def open_documentation(self, e):
        """Opens the documentation HTML file in the default web browser."""
        doc_filename = f"Log_Analyzer_{self.VERSION}_Docs_EN.html"
        doc_path = self.resource_path(os.path.join("Doc", doc_filename))

        # Check if the file exists, as resource_path might return a non-existent path
        if not os.path.exists(doc_path):
            self.show_toast(f"Documentation file not found:\n{doc_path}", is_error=True)
            return

        try:
            # webbrowser opens the local file path
            webbrowser.open('file://' + os.path.realpath(doc_path))
        except Exception as ex:
            self.show_toast(f"Failed to open documentation:\n{ex}", is_error=True)

    async def show_keyboard_shortcuts_dialog(self, e):
        self.dialogs.show_keyboard_shortcuts_dialog()

    async def show_about_dialog(self, e):
        self.dialogs.show_about_dialog()

    async def _perform_load_logic(self, path):
        """實際的檔案載入與引擎初始化邏輯。"""
        start_time = time.time()

        # 初始化引擎
        if HAS_RUST:
             self.log_engine = LogEngine(path)
        else:
             self.log_engine = LogEngine(path)

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

        self.reload_log_view()
        engine_type = "Rust" if HAS_RUST else "Mock"

        # Show load stats in SnackBar instead of overwriting Status Bar
        load_msg = f"[{engine_type}] Loaded {os.path.basename(path)} ({line_count:,} lines) in {duration:.3f}s"
        self.show_toast(load_msg)
