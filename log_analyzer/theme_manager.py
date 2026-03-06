from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtWidgets import QApplication
import os
from .icon_manager import icon_manager

class ThemeManager(QObject):
    """
    Centralizes color palettes and QSS generation for LogAnalyzer.
    Maintains pill-shaped scrollbars, hidden dock tabs, and interactive buttons.
    """
    _instance = None
    theme_changed = Signal()
    font_changed = Signal()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThemeManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized: return
        super().__init__()
        self._initialized = True
        self.current_theme_name = "dark_classic"
        self._init_palettes()

    def set_theme(self, theme_name: str):
        self.current_theme_name = theme_name
        themes = {
            "dark_classic": self._init_dark_classic_palette,
            "light_classic": self._init_light_classic_palette,
            "nord": self._init_nord_palette,
            "cyber": self._init_cyber_palette,
            "ocean": self._init_ocean_light_palette,
            "dracula": self._init_dracula_palette
        }
        init_func = themes.get(theme_name, self._init_dark_classic_palette)
        init_func()
        self.theme_changed.emit()

    def get_color(self, key: str) -> str:
        return self.palette.get(key, "#FF00FF")

    def get_qcolor(self, key: str) -> QColor:
        val = self.palette.get(key, "#FF00FF")
        if isinstance(val, QColor): return val
        return QColor(val)

    def get_hover_color(self): return self.get_color("hover_bg")

    def get_font(self, size_pt=10.5, weight=QFont.Normal, italic=False):
        font = QFont()
        font.setFamilies(["Inter", "Segoe UI", "Microsoft JhengHei UI", "sans-serif"])
        font.setPointSizeF(size_pt)
        font.setWeight(weight)
        font.setItalic(italic)
        font.setStyleStrategy(QFont.PreferAntialias | QFont.PreferQuality)
        return font

    def get_ui_font_base(self): return self.get_font(10.5, QFont.Normal)
    def get_ui_font_large(self): return self.get_font(12.5, QFont.DemiBold)
    def get_ui_font_small(self): return self.get_font(9.5, QFont.Normal)

    def _init_palettes(self): self._init_dark_classic_palette()

    def _init_dark_classic_palette(self):
        self.is_dark = True
        self.palette = {
            "bg_primary": "#1e1e1e", "bg_secondary": "#252526",
            "fg_primary": "#cccccc", "fg_on_accent": "#ffffff",
            "accent": "#007acc", "border": "#3c3c3c",
            "hover_bg": "rgba(255, 255, 255, 30)",
            "bg_color": "#1e1e1e", "fg_color": "#cccccc",
            "selection_bg": "#264f78", "selection_fg": "#ffffff",
            "hover_qcolor": QColor(255, 255, 255, 30),
            "scrollbar_bg": "transparent", "scrollbar_handle": "#424242", "scrollbar_hover": "#4f4f4f",
            "menu_bg": "#252526", "menu_fg": "#cccccc", "menu_sel": "#094771", "menu_sel_fg": "#ffffff",
            "bar_bg": "#007acc", "bar_fg": "#ffffff", "input_bg": "#3c3c3c", "input_fg": "#cccccc",
            "float_bg": "#252526", "float_border": "#505050", "dock_title_bg": "#2d2d2d", "tree_bg": "#252526",
            "tab_bg": "#2d2d2d", "tab_fg": "#858585", "tab_sel_bg": "#1e1e1e",
            "activity_bg": "#181818", "sidebar_bg": "#252526", "header_bg": "#1e1e1e",
            "dialog_bg": "#252526", "dialog_fg": "#cccccc", "checkbox_active": "#007acc", "accent_hover": "#1f8ad2",
            "titlebar_bg": "#181818", "titlebar_fg": "#cccccc", "titlebar_hover": "#333333", "close_hover": "#c42b1c",
            "log_gutter_bg": "#1e1e1e", "log_gutter_fg": "#858585", "log_border": "#303031",
            "dock_header_bg": "#252526", "dock_content_bg": "#252526", "dock_border": "#303031",
            "cb_border": "#3c3c3c", "tooltip_bg": "#2d2d2d", "tooltip_fg": "#cccccc", "tooltip_border": "#505050"
        }

    def _init_light_classic_palette(self):
        self.is_dark = False
        self.palette = {
            "bg_primary": "#ffffff", "bg_secondary": "#f3f3f3",
            "fg_primary": "#333333", "fg_on_accent": "#ffffff",
            "accent": "#007acc", "border": "#bbbbbb",
            "hover_bg": "rgba(0, 0, 0, 20)",
            "bg_color": "#ffffff", "fg_color": "#333333",
            "selection_bg": "#add6ff", "selection_fg": "#000000",
            "hover_qcolor": QColor(0, 0, 0, 20),
            "scrollbar_bg": "transparent", "scrollbar_handle": "#c1c1c1", "scrollbar_hover": "#a8a8a8",
            "menu_bg": "#f3f3f3", "menu_fg": "#333333", "menu_sel": "#add6ff", "menu_sel_fg": "#000000",
            "bar_bg": "#007acc", "bar_fg": "#ffffff", "input_bg": "#ffffff", "input_fg": "#000000",
            "float_bg": "#ffffff", "float_border": "#e5e5e5", "dock_title_bg": "#f3f3f3", "tree_bg": "#f3f3f3",
            "tab_bg": "#e1e1e1", "tab_fg": "#666666", "tab_sel_bg": "#ffffff",
            "activity_bg": "#e8e8e8", "sidebar_bg": "#f3f3f3", "header_bg": "#ffffff",
            "dialog_bg": "#f3f3f3", "dialog_fg": "#000000", "checkbox_active": "#007acc", "accent_hover": "#0062a3",
            "titlebar_bg": "#e8e8e8", "titlebar_fg": "#333333", "titlebar_hover": "#d0d0d0", "close_hover": "#c42b1c",
            "log_gutter_bg": "#ffffff", "log_gutter_fg": "#237893", "log_border": "#e5e5e5",
            "dock_header_bg": "#f3f3f3", "dock_content_bg": "#f3f3f3", "dock_border": "#e5e5e5",
            "cb_border": "#bbbbbb", "tooltip_bg": "#ffffff", "tooltip_fg": "#333333", "tooltip_border": "#bbbbbb"
        }

    def _init_nord_palette(self):
        self.is_dark = True; self.palette = self._derive_from_template({"bg_primary": "#2E3440", "bg_secondary": "#3B4252", "fg_primary": "#ECEFF4", "fg_on_accent": "#2E3440", "accent": "#88C0D0", "border": "#4C566A", "hover_bg": "rgba(255, 255, 255, 0.15)"})

    def _init_cyber_palette(self):
        self.is_dark = True; self.palette = self._derive_from_template({"bg_primary": "#0D1117", "bg_secondary": "#161B22", "fg_primary": "#C9D1D9", "fg_on_accent": "#FFFFFF", "accent": "#58A6FF", "border": "#30363D", "hover_bg": "rgba(255, 255, 255, 0.15)"})

    def _init_dracula_palette(self):
        self.is_dark = True; self.palette = self._derive_from_template({"bg_primary": "#282A36", "bg_secondary": "#44475A", "fg_primary": "#F8F8F2", "fg_on_accent": "#282A36", "accent": "#BD93F9", "border": "#6272A4", "hover_bg": "rgba(255, 255, 255, 0.15)"})

    def _init_ocean_light_palette(self):
        self.is_dark = False; self.palette = self._derive_from_template({"bg_primary": "#F0F4F8", "bg_secondary": "#E1E8F0", "fg_primary": "#1A365D", "fg_on_accent": "#FFFFFF", "accent": "#3182CE", "border": "#CBD5E0", "hover_bg": "rgba(0, 0, 0, 0.1)"})

    def _derive_from_template(self, template_palette):
        p = template_palette.copy()
        is_dark = self.is_dark
        p["bg_color"] = p["bg_primary"]; p["fg_color"] = p["fg_primary"]; p["input_bg"] = p["bg_secondary"]; p["input_fg"] = p["fg_primary"]; p["sidebar_bg"] = p["bg_secondary"]; p["header_bg"] = p["bg_primary"]; p["dialog_bg"] = p["bg_secondary"]; p["dialog_fg"] = p["fg_primary"]; p["bar_bg"] = p["accent"]; p["bar_fg"] = p["fg_on_accent"]; p["checkbox_active"] = p["accent"]; p["float_bg"] = p["bg_secondary"]; p["float_border"] = p["border"]; p["tree_bg"] = p["bg_secondary"]; p["menu_bg"] = p["bg_secondary"]; p["menu_fg"] = p["fg_primary"]; p["menu_sel"] = p["accent"]; p["menu_sel_fg"] = p["fg_on_accent"]
        p["scrollbar_bg"] = "transparent"; p["scrollbar_handle"] = p["border"]; p["scrollbar_hover"] = p["accent"]
        p["titlebar_bg"] = p["bg_primary"]; p["titlebar_fg"] = p["fg_primary"]; p["titlebar_hover"] = "rgba(128, 128, 128, 0.2)"; p["close_hover"] = "#e81123"
        p["selection_bg"] = p["accent"]; p["selection_fg"] = p["fg_on_accent"]
        p["log_gutter_bg"] = p["bg_primary"]; p["log_gutter_fg"] = p["border"]; p["log_border"] = p["border"]
        p["dock_header_bg"] = p["bg_secondary"]; p["dock_content_bg"] = p["bg_secondary"]; p["dock_border"] = p["border"]; p["dock_title_bg"] = p["bg_secondary"]; p["tab_bg"] = p["bg_secondary"]; p["tab_fg"] = p["fg_primary"]; p["tab_sel_bg"] = p["bg_primary"]
        p["activity_bg"] = p["bg_primary"]; p["cb_border"] = p["border"]; p["accent_hover"] = p["accent"] 
        p["hover_qcolor"] = QColor(p["hover_bg"]) if "rgba" in p["hover_bg"] else QColor(p["hover_bg"])
        p["tooltip_bg"] = p["bg_secondary"] if is_dark else "#ffffff"
        p["tooltip_fg"] = p["fg_primary"]
        p["tooltip_border"] = p["border"]
        return p

    @staticmethod
    def apply_menu_theme(menu):
        menu.setWindowFlags(menu.windowFlags() | Qt.NoDropShadowWindowHint)
        menu.setAttribute(Qt.WA_TranslucentBackground)

    def get_stylesheet(self, font_family: str, font_size: int) -> str:
        p = self.palette
        ui_font = f'"{font_family}", "Inter", "Segoe UI", "Microsoft JhengHei UI", sans-serif'
        chevron_down_url = icon_manager.get_icon_css_url("chevron-down", p['fg_color'])
        chevron_up_url = icon_manager.get_icon_css_url("chevron-up", p['fg_color'])
        check_color = "#ffffff" if self.is_dark else "#000000"
        check_url = icon_manager.get_icon_css_url("check", check_color)

        scrollbar_style = f"""
        QScrollBar:vertical {{ border: none; background: transparent; width: 10px; margin: 0px; }}
        QScrollBar::handle:vertical {{ background: {p['scrollbar_handle']}; min-height: 20px; border-radius: 5px; }}
        QScrollBar::handle:vertical:hover {{ background: {p['scrollbar_hover']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ border: none; background: none; height: 0px; width: 0px; }}
        
        QScrollBar:horizontal {{ border: none; background: transparent; height: 10px; margin: 0px; }}
        QScrollBar::handle:horizontal {{ background: {p['scrollbar_handle']}; min-width: 20px; border-radius: 5px; }}
        QScrollBar::handle:horizontal:hover {{ background: {p['scrollbar_hover']}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal, QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ border: none; background: none; height: 0px; width: 0px; }}
        """

        style = f"""
        QWidget {{ font-family: {ui_font}; }}
        QMainWindow, QDialog, QMessageBox {{ background-color: {p['bg_color']}; color: {p['fg_color']}; }}
        #central_widget {{ background-color: {p['bg_color']}; }}
        QDockWidget {{ background-color: {p['bg_color']}; color: {p['fg_color']}; border: none; }}
        QMainWindow::separator {{ background-color: {p['bg_color']}; width: 4px; height: 4px; border: none; }}
        QMainWindow::separator:hover {{ background-color: {p['float_border']}; }}
        QWidget {{ color: {p['fg_color']}; font-size: {font_size}px; }}
        
        QTabBar {{ height: 0px; width: 0px; background: transparent; border: none; }}
        QTabBar::tab {{ height: 0px; width: 0px; padding: 0px; margin: 0px; border: none; }}
        
        #activity_bar {{ background-color: {p['activity_bg']}; border: none; spacing: 10px; padding-top: 5px; }}
        #activity_bar QToolButton {{ background-color: transparent; border: none; border-left: 3px solid transparent; border-radius: 0px; margin: 0px; }}
        #activity_bar QToolButton:hover {{ background-color: {p['hover_bg']}; }}
        #activity_bar QToolButton:checked {{ border-left: 3px solid {p['bar_bg']}; background-color: {p['sidebar_bg']}; }}
        QDockWidget#FilterDock, QDockWidget#NotesDock, QDockWidget#LogListDock {{ color: {p['fg_color']}; font-family: "Inter SemiBold", "Inter", "Segoe UI"; border: none; }}
        QDockWidget#FilterDock::title, QDockWidget#NotesDock::title, QDockWidget#LogListDock::title {{ background: {p['sidebar_bg']}; padding: 10px; border: none; }}
        #FilterDock QTreeWidget, #NotesDock QTreeWidget, #LogListDock QTreeWidget {{ background-color: {p['sidebar_bg']}; border: none; }}
        QMenuBar {{ background-color: transparent; color: {p['titlebar_fg']}; padding: 2px; font-size: 10pt; }}
        QMenuBar::item {{ background-color: transparent; padding: 6px 12px; margin: 2px; border-radius: 6px; }}
        QMenuBar::item:selected {{ background-color: {p['titlebar_hover']}; }}
        QMenu {{ background-color: {p['menu_bg']}; color: {p['menu_fg']}; border: 1px solid {p['float_border']}; border-radius: 2px; padding: 4px; margin: 4px; }}
        QMenu::item {{ padding: 4px 30px 4px 24px; border-radius: 4px; margin: 2px 4px; }}
        QMenu::item:selected {{ background-color: {p['menu_sel']}; color: {p['menu_sel_fg']}; }}
        QComboBox {{ background-color: {p['input_bg']}; color: {p['input_fg']}; border: 1px solid {p['float_border']}; border-radius: 4px; padding: 4px 30px 4px 10px; min-height: 24px; }}
        QComboBox:hover {{ border: 1px solid {p['accent']}; }}
        QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 30px; border-left: none; }}
        QComboBox::down-arrow {{ image: {chevron_down_url}; width: 14px; height: 14px; }}
        QSpinBox {{ background-color: {p['input_bg']}; color: {p['input_fg']}; border: 1px solid {p['float_border']}; border-radius: 4px; padding: 4px 2px 4px 8px; min-height: 24px; }}
        QSpinBox:hover {{ border: 1px solid {p['accent']}; }}
        QSpinBox::up-button {{ subcontrol-origin: border; subcontrol-position: top right; width: 20px; border-left: 1px solid {p['float_border']}; border-top-right-radius: 4px; background: {p['bg_secondary']}; }}
        QSpinBox::down-button {{ subcontrol-origin: border; subcontrol-position: bottom right; width: 20px; border-left: 1px solid {p['float_border']}; border-bottom-right-radius: 4px; background: {p['bg_secondary']}; }}
        QSpinBox::up-arrow {{ image: {chevron_up_url}; width: 10px; height: 10px; }}
        QSpinBox::down-arrow {{ image: {chevron_down_url}; width: 10px; height: 10px; }}
        QCheckBox::indicator, QTreeView::indicator {{ width: 16px; height: 16px; border-radius: 3px; border: 1px solid {p['float_border']}; background: {p['input_bg']}; }}
        QCheckBox::indicator:hover, QTreeView::indicator:hover {{ border: 1px solid {p['accent']}; background: {p['hover_bg']}; }}
        QCheckBox::indicator:checked, QTreeView::indicator:checked {{ background: {p['checkbox_active']}; border: 1px solid {p['checkbox_active']}; image: {check_url}; }}
        QListView {{ background-color: {p['bg_color']}; color: {p['fg_color']}; border: none; outline: 0; }}
        QListView::item:selected {{ background-color: {p['selection_bg']}; color: {p['selection_fg']}; }}
        QTreeWidget {{ background-color: {p['tree_bg']}; border: none; color: {p['fg_color']}; outline: 0; }}
        QTreeWidget::item {{ padding: 4px; border: none; }}
        QTreeWidget::item:selected {{ background-color: {p['selection_bg']}; color: {p['selection_fg']}; }}
        QTreeWidget::item:hover {{ background-color: {p['hover_bg']}; color: {p['fg_color']}; }}
        QHeaderView {{ background-color: {p['header_bg']}; border: none; border-bottom: 1px solid {p['float_border']}; }}
        QHeaderView::section {{ background-color: {p['header_bg']}; color: {p['fg_color']}; border: none; padding: 6px 8px; }}
        QLineEdit, QTextEdit, QPlainTextEdit {{ background-color: {p['input_bg']}; color: {p['input_fg']}; border: 1px solid {p['float_border']}; border-radius: 4px; padding: 4px 8px; }}
        
        QPushButton {{ background-color: {p['menu_bg']}; color: {p['fg_color']}; border: 1px solid {p['float_border']}; padding: 6px 16px; border-radius: 4px; }}
        QPushButton:hover {{ background-color: {p['hover_bg']}; }}
        QPushButton:default {{ background-color: {p['bar_bg']}; color: {p['bar_fg']}; border: 1px solid {p['bar_bg']}; font-weight: bold; }}
        QPushButton:default:hover {{ background-color: {p['accent_hover']}; border: 1px solid {p['accent_hover']}; }}
        
        QStatusBar {{ background-color: {p['menu_bg']}; color: {p['menu_fg']}; border-top: 1px solid {p['float_border']}; }}
        
        QToolTip {{ 
            background-color: {p['tooltip_bg']}; 
            color: {p['tooltip_fg']}; 
            border: 1px solid {p['tooltip_border']}; 
            border-radius: 0px; 
            padding: 5px;
        }}
        
        {scrollbar_style}
        """
        return style

    def get_title_bar_style(self, font_family, font_size):
        p = self.palette
        return f"""
            #title_bar {{ background-color: {p['titlebar_bg']}; border-bottom: 1px solid {p['float_border']}; }}
            #title_bar QLabel {{ color: {p['titlebar_fg']} !important; background: transparent; font-family: "{font_family}"; font-size: {font_size + 2}px; }}
            QToolButton {{ background-color: transparent; border: none; border-radius: 0px; }}
            QToolButton:hover {{ background-color: {p['titlebar_hover']}; }}
        """

    def get_dock_title_style(self):
        p = self.palette
        return f"""
            .QWidget {{ background-color: {p['dock_header_bg']}; border-bottom: 1px solid {p['dock_border']}; }}
            QLabel {{ border: none; background: transparent; }}
            QToolButton {{ border: none; background: transparent; border-radius: 4px; padding: 2px; }}
            QToolButton:hover {{ background-color: {p['hover_bg']}; }}
            QToolButton:pressed {{ background-color: {p['selection_bg']}; }}
        """

    def get_close_btn_style(self):
        return f"""
            QToolButton {{ background-color: transparent; border: none; border-radius: 0px; }}
            QToolButton:hover {{ background-color: {self.palette['close_hover']}; }}
        """

    def get_close_btn_style(self):
        return f"""
            QToolButton {{ background-color: transparent; border: none; border-radius: 0px; }}
            QToolButton:hover {{ background-color: {self.palette['close_hover']}; }}
        """

    def get_dock_list_style(self, is_dark_mode):
        p = self.palette
        return f"""
            QTreeWidget {{ background-color: {p['dock_content_bg']}; border: none; }}
            QTreeWidget::item {{ padding: 4px; border: none; }}
            QTreeWidget::item:selected {{ background-color: {p['selection_bg']}; color: {p['selection_fg']}; }}
            QTreeWidget::item:hover {{ background-color: {p['hover_bg']}; }}
        """

# Export a lazy singleton
class _LazyThemeManager:
    def __getattr__(self, name):
        global theme_manager_instance
        if 'theme_manager_instance' not in globals():
            global theme_manager_instance
            theme_manager_instance = ThemeManager()
        return getattr(theme_manager_instance, name)

theme_manager = _LazyThemeManager()
