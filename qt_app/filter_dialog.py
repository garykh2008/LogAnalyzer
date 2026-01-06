from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
                               QCheckBox, QPushButton, QColorDialog, QDialogButtonBox)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from .utils import set_windows_title_bar_color, adjust_color_for_theme

class FilterDialog(QDialog):
    def __init__(self, parent=None, filter_data=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Filter" if filter_data else "Add Filter")
        self.resize(400, 200)

        self.filter_data = filter_data or {}

        layout = QVBoxLayout(self)

        # Pattern Input
        self.pattern_edit = QLineEdit(self.filter_data.get("text", ""))
        self.pattern_edit.setPlaceholderText("Filter Pattern...")
        layout.addWidget(QLabel("Pattern:"))
        layout.addWidget(self.pattern_edit)

        # Options
        opts_layout = QHBoxLayout()
        self.chk_regex = QCheckBox("Regex")
        self.chk_regex.setChecked(self.filter_data.get("is_regex", False))
        self.chk_exclude = QCheckBox("Exclude")
        self.chk_exclude.setChecked(self.filter_data.get("is_exclude", False))

        opts_layout.addWidget(self.chk_regex)
        opts_layout.addWidget(self.chk_exclude)
        layout.addLayout(opts_layout)

        # Colors
        color_layout = QHBoxLayout()
        self.btn_fg = QPushButton("Text Color")
        self.btn_bg = QPushButton("Background")

        # Default colors
        self.fg_color = self.filter_data.get("fg_color", "#000000")
        self.bg_color = self.filter_data.get("bg_color", "#FFFFFF")

        self.btn_fg.clicked.connect(self._pick_fg)
        self.btn_bg.clicked.connect(self._pick_bg)

        self._update_btn_styles()

        color_layout.addWidget(self.btn_fg)
        color_layout.addWidget(self.btn_bg)
        layout.addLayout(color_layout)

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Apply Title Bar Theme
        if parent and hasattr(parent, 'is_dark_mode'):
            set_windows_title_bar_color(self.winId(), parent.is_dark_mode)

    def _pick_fg(self):
        c = QColorDialog.getColor(QColor(self.fg_color), self, "Select Text Color")
        if c.isValid():
            self.fg_color = c.name()
            self._update_btn_styles()

    def _pick_bg(self):
        c = QColorDialog.getColor(QColor(self.bg_color), self, "Select Background")
        if c.isValid():
            self.bg_color = c.name()
            self._update_btn_styles()

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

        # Explicitly setting border to ensure visibility in both themes
        self.btn_fg.setStyleSheet(f"background-color: {display_fg}; color: {contrast(display_fg)}; border: 1px solid #888; padding: 5px;")
        self.btn_bg.setStyleSheet(f"background-color: {display_bg}; color: {contrast(display_bg)}; border: 1px solid #888; padding: 5px;")

    def get_data(self):
        return {
            "text": self.pattern_edit.text(),
            "is_regex": self.chk_regex.isChecked(),
            "is_exclude": self.chk_exclude.isChecked(),
            "fg_color": self.fg_color,
            "bg_color": self.bg_color,
            "enabled": self.filter_data.get("enabled", True)
        }
