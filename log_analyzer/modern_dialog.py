from PySide6.QtWidgets import QDialog, QVBoxLayout, QWidget, QSizeGrip
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from .components import CustomTitleBar
from .utils import adjust_color_for_theme

class ModernDialog(QDialog):
    def __init__(self, parent=None, title="Dialog", fixed_size=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        
        # Main Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Title Bar
        self.title_bar = CustomTitleBar(self, title=title, hide_icon=True, show_minimize=False, show_maximize=False)
        self.title_bar.setObjectName("dialog_title_bar")
        self.main_layout.addWidget(self.title_bar)
        
        # Content Area
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(20, 20, 20, 20)
        self.content_layout.setSpacing(10)
        self.main_layout.addWidget(self.content_widget)
        
        # Size Grip (Optional, usually dialogs are fixed size, but good to have)
        # self.size_grip = QSizeGrip(self)
        # self.main_layout.addWidget(self.size_grip, 0, Qt.AlignBottom | Qt.AlignRight)

        if fixed_size:
            self.setFixedSize(*fixed_size)
            
        self.apply_theme()

    def setContentLayout(self, layout):
        # Move items from user layout to content layout or set as main content
        if self.content_widget.layout():
            QWidget().setLayout(self.content_widget.layout()) # Delete old layout
        self.content_widget.setLayout(layout)
        layout.setContentsMargins(20, 20, 20, 20) # Enforce consistent padding

    def setWindowTitle(self, title):
        super().setWindowTitle(title)
        if hasattr(self, 'title_bar'):
            self.title_bar.title_label.setText(title)

    def apply_theme(self):
        from .config import get_config
        config = get_config()
        is_dark = (config.theme == "Dark")
        
        # Define Colors ( synced with MainWindow )
        if is_dark:
            bg_color = "#252526"
            fg_color = "#cccccc"
            border_color = "#454545"
            titlebar_bg = "#181818" # Synced with Main Window
            titlebar_hover = "#333333"
            close_hover = "#c42b1c"
        else:
            bg_color = "#f3f3f3"
            fg_color = "#333333"
            border_color = "#cccccc"
            titlebar_bg = "#e8e8e8" # Synced with Main Window
            titlebar_hover = "#d0d0d0"
            close_hover = "#c42b1c"

        # Apply Styles
        self.setStyleSheet(f"""
            QDialog {{ background-color: {bg_color}; color: {fg_color}; border: 1px solid {border_color}; }}
            QLabel, QCheckBox {{ color: {fg_color}; }}
            #dialog_title_bar {{ background-color: {titlebar_bg}; border-bottom: 1px solid {border_color}; }}
            #dialog_title_bar QLabel {{ color: {fg_color}; font-weight: bold; }}
            QToolButton {{ background-color: transparent; border: none; border-radius: 0px; }}
            QToolButton:hover {{ background-color: {titlebar_hover}; }}
            
            QGroupBox {{ 
                border: 1px solid {border_color}; 
                border-radius: 4px; 
                margin-top: 18px; /* Leave space for title */
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                padding: 0 3px;
                background-color: {bg_color}; /* Cover the border */
            }}
        """)
        
        # Specific hover for close button
        self.title_bar.btn_close.setStyleSheet(f"""
            QToolButton {{ background-color: transparent; border: none; border-radius: 0px; }}
            QToolButton:hover {{ background-color: {close_hover}; }}
        """)
        
        # Update Icon Colors
        icon_c = fg_color
        from .resources import get_svg_icon
        self.title_bar.btn_close.setIcon(get_svg_icon("x-close", icon_c))

    def exec(self):
        if self.parent() and hasattr(self.parent(), "show_dimmer"):
            self.parent().show_dimmer()
        
        res = super().exec()
        
        if self.parent() and hasattr(self.parent(), "hide_dimmer"):
            self.parent().hide_dimmer()
        return res
