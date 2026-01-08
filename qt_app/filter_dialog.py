from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QCheckBox, QPushButton, QColorDialog, QDialogButtonBox, QGroupBox, QGridLayout)
from PySide6.QtGui import QColor, QFont
from PySide6.QtCore import Qt
from .utils import set_windows_title_bar_color, adjust_color_for_theme
from .resources import get_svg_icon

class FilterDialog(QDialog):

    def __init__(self, parent=None, filter_data=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Filter" if filter_data else "Add Filter")
        self.resize(450, 320) # Slightly larger for better spacing

        self.filter_data = filter_data or {}

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        # --- Group 1: Matching Rules ---
        group_match = QGroupBox("Matching Rules")
        group_match_layout = QVBoxLayout(group_match)
        group_match_layout.setSpacing(10)

        # Pattern Input (Top-aligned label)
        lbl_pattern = QLabel("Filter Pattern")
        f = lbl_pattern.font(); f.setBold(True); lbl_pattern.setFont(f)
        self.pattern_edit = QLineEdit(self.filter_data.get("text", ""))
        self.pattern_edit.setPlaceholderText("e.g. Error, Warning, ^[0-9]+")
        self.pattern_edit.setMinimumHeight(30)
        self.pattern_edit.textChanged.connect(self._update_preview)
        
        group_match_layout.addWidget(lbl_pattern)
        group_match_layout.addWidget(self.pattern_edit)

        # Options (Horizontal)
        opts_layout = QHBoxLayout()
        self.chk_regex = QCheckBox("Regex")
        self.chk_regex.setChecked(self.filter_data.get("is_regex", False))
        self.chk_exclude = QCheckBox("Exclude")
        self.chk_exclude.setChecked(self.filter_data.get("is_exclude", False))
        
        # Case sensitive (New feature place holder or if supported)
        # self.chk_case = QCheckBox("Case Sensitive") 

        opts_layout.addWidget(self.chk_regex)
        opts_layout.addWidget(self.chk_exclude)
        opts_layout.addStretch()
        group_match_layout.addLayout(opts_layout)

        main_layout.addWidget(group_match)

        # --- Group 2: Appearance ---
        group_style = QGroupBox("Appearance")
        group_style_layout = QVBoxLayout(group_style)
        
        color_grid = QGridLayout()
        
        self.btn_fg = QPushButton(" Text Color")
        self.btn_fg.setIcon(get_svg_icon("type"))
        self.btn_fg.setMinimumHeight(30)
        self.btn_bg = QPushButton(" Background")
        self.btn_bg.setIcon(get_svg_icon("droplet"))
        self.btn_bg.setMinimumHeight(30)

        # Default colors
        self.fg_color = self.filter_data.get("fg_color", "#000000")
        self.bg_color = self.filter_data.get("bg_color", "#FFFFFF")

        self.btn_fg.clicked.connect(self._pick_fg)
        self.btn_bg.clicked.connect(self._pick_bg)

        color_grid.addWidget(self.btn_fg, 0, 0)
        color_grid.addWidget(self.btn_bg, 0, 1)
        
        group_style_layout.addLayout(color_grid)
        
        # Live Preview Area
        self.lbl_preview = QLabel("Preview Text")
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setFixedHeight(40)
        # Give it a border to stand out
        self.lbl_preview.setStyleSheet("border: 1px solid #cccccc; border-radius: 4px;")
        
        group_style_layout.addWidget(QLabel("Preview:"))
        group_style_layout.addWidget(self.lbl_preview)

        main_layout.addWidget(group_style)

        # Initial Update
        self._update_btn_styles()
        self._update_preview()

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)

        # Apply Title Bar Theme
        if parent and hasattr(parent, 'is_dark_mode'):
            set_windows_title_bar_color(self.winId(), parent.is_dark_mode)

    def _pick_fg(self):
        c = QColorDialog.getColor(QColor(self.fg_color), self, "Select Text Color")
        if c.isValid():
            self.fg_color = c.name()
            self._update_btn_styles()
            self._update_preview()

    def _pick_bg(self):
        c = QColorDialog.getColor(QColor(self.bg_color), self, "Select Background")
        if c.isValid():
            self.bg_color = c.name()
            self._update_btn_styles()
            self._update_preview()

    def _update_preview(self):
        txt = self.pattern_edit.text() or "Preview Text"
        
        # Use theme-adjusted colors for preview to match actual list view look
        is_dark = False
        if self.parent() and hasattr(self.parent(), 'is_dark_mode'):
            is_dark = self.parent().is_dark_mode

        display_fg = adjust_color_for_theme(self.fg_color, False, is_dark)
        display_bg = adjust_color_for_theme(self.bg_color, True, is_dark)
        
        self.lbl_preview.setText(txt)
        self.lbl_preview.setStyleSheet(f"background-color: {display_bg}; color: {display_fg}; border: 1px solid #888; border-radius: 4px; font-family: 'Inter', 'Consolas'; font-size: 14px;")

    def _update_btn_styles(self):
        # Calculate contrast text for button readability
        def contrast(hex_color):
            c = QColor(hex_color)
            lum = 0.2126 * c.red() + 0.7152 * c.green() + 0.0722 * c.blue()
            return "#000000" if lum > 128 else "#FFFFFF"

        # Smart Color Adjustment
        is_dark = False
        if self.parent() and hasattr(self.parent(), 'is_dark_mode'):
            is_dark = self.parent().is_dark_mode

        display_fg = adjust_color_for_theme(self.fg_color, False, is_dark)
        display_bg = adjust_color_for_theme(self.bg_color, True, is_dark)

        # Update buttons to show the ACTUAL appearance in current theme
        self.btn_fg.setStyleSheet(f"background-color: {display_fg}; color: {contrast(display_fg)}; border: 1px solid #888; border-radius: 4px;")
        self.btn_bg.setStyleSheet(f"background-color: {display_bg}; color: {contrast(display_bg)}; border: 1px solid #888; border-radius: 4px;")

    def get_data(self):
        return {
            "text": self.pattern_edit.text(),
            "is_regex": self.chk_regex.isChecked(),
            "is_exclude": self.chk_exclude.isChecked(),
            "fg_color": self.fg_color,
            "bg_color": self.bg_color,
            "enabled": self.filter_data.get("enabled", True)
        }
