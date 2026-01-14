from PySide6.QtGui import QColor

class ThemeManager:
    """
    Centralizes color palettes and QSS generation for LogAnalyzer.
    """
    def __init__(self):
        self.is_dark = True
        self._init_palettes()

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark

    def _init_palettes(self):
        self.dark_palette = {
            "bg_color": "#1e1e1e",
            "fg_color": "#cccccc",
            "selection_bg": "#264f78",
            "selection_fg": "#ffffff",
            "hover_bg": "rgba(255, 255, 255, 30)",
            "hover_qcolor": QColor(255, 255, 255, 30),
            
            "scrollbar_bg": "#1e1e1e",
            "scrollbar_handle": "#424242",
            "scrollbar_hover": "#4f4f4f",
            
            "menu_bg": "#252526",
            "menu_fg": "#cccccc",
            "menu_sel": "#094771",
            "menu_sel_fg": "#ffffff",
            
            "bar_bg": "#007acc",
            "bar_fg": "#ffffff",
            "input_bg": "#3c3c3c",
            "input_fg": "#cccccc",
            
            "float_bg": "#252526",
            "float_border": "#303031",
            "dock_title_bg": "#2d2d2d",
            "tree_bg": "#252526",
            
            "tab_bg": "#2d2d2d",
            "tab_fg": "#858585",
            "tab_sel_bg": "#1e1e1e",
            
            "activity_bg": "#181818",
            "sidebar_bg": "#252526",
            "header_bg": "#1e1e1e",
            "dialog_bg": "#252526",
            "dialog_fg": "#cccccc",
            "checkbox_active": "#007acc",
            
            "titlebar_bg": "#181818",
            "titlebar_fg": "#cccccc",
            "titlebar_hover": "#333333",
            "close_hover": "#c42b1c",
            
            # Log View Specific
            "log_gutter_bg": "#1e1e1e",
            "log_gutter_fg": "#858585",
            "log_border": "#303031",

             # Filter/Dock Specific
            "dock_header_bg": "#252526",
            "dock_content_bg": "#252526",
            "dock_border": "#303031",
            
            # Checkbox border
            "cb_border": "#3c3c3c" 
        }

        self.light_palette = {
            "bg_color": "#ffffff",
            "fg_color": "#333333",
            "selection_bg": "#add6ff",
            "selection_fg": "#000000",
            "hover_bg": "rgba(0, 0, 0, 20)",
            "hover_qcolor": QColor(0, 0, 0, 20),
            
            "scrollbar_bg": "#f3f3f3",
            "scrollbar_handle": "#c1c1c1",
            "scrollbar_hover": "#a8a8a8",
            
            "menu_bg": "#f3f3f3",
            "menu_fg": "#333333",
            "menu_sel": "#add6ff",
            "menu_sel_fg": "#000000",
            
            "bar_bg": "#007acc",
            "bar_fg": "#ffffff",
            "input_bg": "#ffffff",
            "input_fg": "#000000",
            
            "float_bg": "#ffffff",
            "float_border": "#e5e5e5",
            "dock_title_bg": "#f3f3f3",
            "tree_bg": "#f3f3f3",
            
            "tab_bg": "#e1e1e1",
            "tab_fg": "#666666",
            "tab_sel_bg": "#ffffff",
            
            "activity_bg": "#e8e8e8",
            "sidebar_bg": "#f3f3f3",
            "header_bg": "#ffffff",
            "dialog_bg": "#f3f3f3",
            "dialog_fg": "#000000",
            "checkbox_active": "#007acc",
            
            "titlebar_bg": "#e8e8e8",
            "titlebar_fg": "#333333",
            "titlebar_hover": "#d0d0d0",
            "close_hover": "#c42b1c",
            
            # Log View Specific
            "log_gutter_bg": "#ffffff",
            "log_gutter_fg": "#237893",
            "log_border": "#e5e5e5",

             # Filter/Dock Specific
            "dock_header_bg": "#f3f3f3",
            "dock_content_bg": "#f3f3f3",
            "dock_border": "#e5e5e5",
            
            # Checkbox border
            "cb_border": "#bbbbbb"
        }

    @property
    def palette(self):
        return self.dark_palette if self.is_dark else self.light_palette

    def get_color(self, key: str) -> str:
        return self.palette.get(key, "#ff0000")

    def get_qcolor(self, key: str) -> QColor:
        val = self.palette.get(key)
        if isinstance(val, QColor):
            return val
        return QColor(val)

    def get_stylesheet(self, font_family: str, font_size: int) -> str:
        p = self.palette
        
        # Menu Style Template
        menu_style = f"""
        QMenuBar {{ background-color: transparent; color: {p['titlebar_fg']}; border: none; padding: 0px; font-family: "{font_family}"; }}
        QMenuBar::item {{ background-color: transparent; padding: 5px 10px; border-radius: 4px; }}
        QMenuBar::item:selected {{ background-color: {p['titlebar_hover']}; }}
        QMenu {{ background-color: {p['menu_bg']}; color: {p['menu_fg']}; border: 1px solid {p['float_border']}; border-radius: 4px; padding: 4px; margin: 0px; font-family: "{font_family}"; }}
        QMenu::item {{ padding: 6px 25px 6px 20px; border-radius: 3px; margin: 1px 0px; }}
        QMenu::item:selected {{ background-color: {p['menu_sel']}; color: {p['menu_sel_fg']}; }}
        QMenu::separator {{ height: 1px; background: {p['float_border']}; margin: 4px 8px; }}
        QToolTip {{ color: {p['fg_color']}; background-color: {p['menu_bg']}; border: 1px solid {p['float_border']}; padding: 5px; border-radius: 0px; }}
        """

        # Checkbox SVG Logic
        cb_svg = f"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='20 6 9 17 4 12'%3E%3C/polyline%3E%3C/svg%3E"
        
        cb_style = f"""
        QCheckBox {{ spacing: 8px; }}
        QCheckBox::indicator, QTreeView::indicator {{ 
            width: 14px; height: 14px; border-radius: 3px; 
            border: 1px solid {p['cb_border']}; background: {p['input_bg']}; margin: 0px; padding: 0px;
        }}
        QTreeView::indicator {{ subcontrol-origin: padding; subcontrol-position: center; }}
        QCheckBox::indicator:checked, QTreeView::indicator:checked {{ 
            background: {p['checkbox_active']}; 
            image: url("{cb_svg}");
        }}
        QCheckBox::indicator:hover, QTreeView::indicator:hover {{ border: 1px solid {p['menu_sel']}; }}
        """

        # Main Style
        style = f"""
        QWidget {{ font-family: "{font_family}", "Segoe UI", "Microsoft JhengHei UI", sans-serif; }}
        QMainWindow, QDialog, QMessageBox {{ background-color: {p['bg_color']}; color: {p['fg_color']}; }}
        QDockWidget {{ background-color: {p['bg_color']}; color: {p['fg_color']}; }}
        QMainWindow::separator {{ background-color: transparent; width: 4px; }}
        QMainWindow::separator:hover {{ background-color: {p['float_border']}; }}
        QWidget {{ color: {p['fg_color']}; font-size: {font_size}px; }}
        
        #activity_bar {{ background-color: {p['activity_bg']}; border: none; spacing: 10px; padding-top: 5px; }}
        #activity_bar QToolButton {{ background-color: transparent; border: none; border-left: 3px solid transparent; border-radius: 0px; margin: 0px; font-size: {font_size}px; }}
        #activity_bar QToolButton:hover {{ background-color: {p['hover_bg']}; }}
        #activity_bar QToolButton:checked {{ border-left: 3px solid {p['bar_bg']}; background-color: {p['sidebar_bg']}; }}
        #activity_bar QToolButton:checked QLabel {{ color: #ffffff; }}
        
        QDockWidget#FilterDock, QDockWidget#NotesDock, QDockWidget#LogListDock {{ color: {p['fg_color']}; font-family: "Inter SemiBold", "Inter", "Segoe UI"; font-weight: normal; titlebar-close-icon: none; titlebar-normal-icon: none; border-bottom: 1px solid {p['float_border']}; }}
        QDockWidget#FilterDock::title, QDockWidget#NotesDock::title, QDockWidget#LogListDock::title {{ background: {p['sidebar_bg']}; padding: 10px; border: none; }}
        #FilterDock QWidget, #NotesDock QWidget, #LogListDock QWidget {{ background-color: {p['sidebar_bg']}; }}
        #FilterDock QTreeWidget, #NotesDock QTreeWidget, #LogListDock QTreeWidget {{ background-color: {p['sidebar_bg']}; border: none; }}
        
        {menu_style}
        
        QListView {{ background-color: {p['bg_color']}; color: {p['fg_color']}; border: none; outline: 0; }}
        QListView::item:selected {{ background-color: {p['selection_bg']}; color: {p['selection_fg']}; }}
        
        QTreeWidget {{ background-color: {p['tree_bg']}; border: none; color: {p['fg_color']}; outline: 0; }}
        QTreeWidget::item {{ padding: 4px; border: none; }}
        QTreeWidget::item:selected {{ background-color: {p['selection_bg']}; color: {p['selection_fg']}; }}
        QTreeWidget::item:hover {{ background-color: {p['hover_bg']}; color: {p['fg_color']}; }}
        
        QHeaderView {{ background-color: {p['header_bg']}; border: none; border-bottom: 1px solid {p['float_border']}; }}
        QHeaderView::section {{ background-color: {p['header_bg']}; color: {p['fg_color']}; border: none; border-right: none; padding: 6px 8px; font-family: "Inter SemiBold", "Inter", "Segoe UI"; font-weight: normal; text-align: left; }}
        QHeaderView::section:first {{ padding-left: 0px; padding-right: 0px; text-align: center; }}
        QHeaderView::section:last {{ padding-right: 4px; }}
        QHeaderView::section:horizontal {{ border-right: 1px solid transparent; }}
        
        QTabBar {{ height: 0px; width: 0px; background: transparent; }}
        QTabBar::tab {{ height: 0px; width: 0px; padding: 0px; margin: 0px; border: none; }}
        
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{ background-color: {p['input_bg']}; color: {p['input_fg']}; border: 1px solid {p['float_border']}; border-radius: 4px; padding: 4px 8px; }}
        
        QPushButton {{ background-color: {p['menu_bg']}; color: {p['fg_color']}; border: 1px solid {p['float_border']}; padding: 6px 16px; border-radius: 4px; }}
        QPushButton:hover {{ background-color: {p['hover_bg']}; }}
        QPushButton:pressed {{ background-color: {p['selection_bg']}; }}
        QPushButton:default {{ background-color: {p['bar_bg']}; color: {p['bar_fg']}; border: 1px solid {p['bar_bg']}; font-weight: bold; }}
        QPushButton:default:hover {{ background-color: {p['checkbox_active']}; border: 1px solid {p['checkbox_active']}; }}
        
        QToolButton {{ background-color: transparent; color: {p['input_fg']}; border: 1px solid transparent; border-radius: 4px; padding: 2px; }}
        QToolButton:hover {{ background-color: {p['hover_bg']}; border: 1px solid {p['float_border']}; }}
        QToolButton:pressed {{ background-color: {p['selection_bg']}; }}
        QToolButton:checked {{ background-color: {p['selection_bg']}; color: {p['selection_fg']}; border: 1px solid {p['menu_sel']}; }}
        
        QStatusBar {{ background-color: {p['menu_bg']}; color: {p['menu_fg']}; border-top: 1px solid {p['float_border']}; }}
        QStatusBar QLabel {{ padding: 2px 6px; border-radius: 3px; }}
        QStatusBar QLabel:hover {{ background-color: {p['hover_bg']}; }}
        
        QScrollBar:vertical {{ border: none; background: transparent; width: 10px; margin: 0px; }}
        QScrollBar::handle:vertical {{ background: {p['scrollbar_handle']}; min-height: 20px; border-radius: 5px; }}
        QScrollBar::handle:vertical:hover {{ background: {p['scrollbar_hover']}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; background: transparent; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        
        QScrollBar:horizontal {{ border: none; background: transparent; height: 10px; margin: 0px; }}
        QScrollBar::handle:horizontal {{ background: {p['scrollbar_handle']}; min-width: 20px; border-radius: 5px; }}
        QScrollBar::handle:horizontal:hover {{ background: {p['scrollbar_hover']}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; background: transparent; }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
        
        QAbstractScrollArea::corner {{ background: transparent; border: none; }}
        QSplitter::handle {{ background-color: {p['float_border']}; }}
        
        {cb_style}
        """
        return style

    def get_title_bar_style(self, font_family, font_size):
        p = self.palette
        return f"""
            #title_bar {{ background-color: {p['titlebar_bg']}; border-bottom: 1px solid {p['float_border']}; }}
            #title_bar QLabel {{ color: {p['titlebar_fg']}; font-family: "{font_family}"; font-size: {font_size + 2}px; }}
            QToolButton {{ background-color: transparent; border: none; border-radius: 0px; }}
            QToolButton:hover {{ background-color: {p['titlebar_hover']}; }}
        """

    def get_dock_title_style(self):
        p = self.palette
        return f"""
            .QWidget {{ background-color: {p['dock_header_bg']}; border-bottom: 1px solid {p['dock_border']}; }}
            QLabel {{ border: none; }}
            QToolButton {{ border: none; background: transparent; border-radius: 4px; padding: 2px; }}
            QToolButton:hover {{ background-color: {p['hover_bg']}; }}
            QToolButton:pressed {{ background-color: {p['selection_bg']}; }}
        """

    def get_close_btn_style(self):
        return f"""
            QToolButton {{ background-color: transparent; border: none; border-radius: 0px; }}
            QToolButton:hover {{ background-color: {self.palette['close_hover']}; }}
        """

    def get_dock_list_style(self, is_dark_mode):
        # Specific QSS for the dock lists (Logs, Filters) which have specific selection colors
        p = self.palette
        # Re-implement the conditional logic from original ui.py for list item selection
        if is_dark_mode:
            sel_bg, sel_fg = "#264f78", "#ffffff"
        else:
            sel_bg, sel_fg = "#add6ff", "#000000"
            
        return f"""
            QTreeWidget {{ background-color: {p['dock_content_bg']}; border: none; }}
            QTreeWidget::item {{ padding: 4px; border: none; }}
            QTreeWidget::item:selected {{ background-color: {sel_bg}; color: {sel_fg}; }}
            QTreeWidget::item:hover {{ background-color: {p['hover_bg']}; }}
        """
