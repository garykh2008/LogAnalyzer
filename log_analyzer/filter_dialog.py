from PySide6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit,
                               QCheckBox, QPushButton, QColorDialog, QDialogButtonBox, QSizePolicy)
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from .utils import adjust_color_for_theme
from .modern_dialog import ModernDialog


class FilterDialog(ModernDialog):

    def __init__(self, parent=None, filter_data=None):
        # Increased height slightly, removed fixed size constraint to allow layout to breathe if needed
        super().__init__(parent, title="Edit Filter" if filter_data else "Add Filter", fixed_size=(500, 320))

        self.filter_data = filter_data or {}

        # Use the existing content_layout from ModernDialog
        self.content_layout.setSpacing(12) # Slightly tighter spacing

        # --- Section 1: Pattern ---
        lbl_pattern = QLabel("Pattern")
        f = lbl_pattern.font(); f.setBold(True); lbl_pattern.setFont(f)
        self.content_layout.addWidget(lbl_pattern)

        self.pattern_edit = QLineEdit(self.filter_data.get("text", ""))
        self.pattern_edit.setPlaceholderText("e.g. Error, Warning, ^[0-9]+")
        self.pattern_edit.setMinimumHeight(32)
        self.pattern_edit.textChanged.connect(self._update_preview)
        self.content_layout.addWidget(self.pattern_edit)

        # Options Row
        opts_layout = QHBoxLayout()
        opts_layout.setSpacing(20)
        self.chk_regex = QCheckBox("Regex")
        self.chk_regex.setChecked(self.filter_data.get("is_regex", False))
        self.chk_exclude = QCheckBox("Exclude")
        self.chk_exclude.setChecked(self.filter_data.get("is_exclude", False))

        opts_layout.addWidget(self.chk_regex)
        opts_layout.addWidget(self.chk_exclude)
        opts_layout.addStretch()
        self.content_layout.addLayout(opts_layout)

        # --- Section 2: Style ---
        lbl_style = QLabel("Appearance")
        f = lbl_style.font(); f.setBold(True)
        lbl_style.setFont(f)
        self.content_layout.addWidget(lbl_style)

        # Style Row: [Text Color] [Bg Color] [Preview Area]
        style_layout = QHBoxLayout()
        style_layout.setSpacing(10)

        self.btn_fg = QPushButton("Text")
        self.btn_fg.setFixedWidth(80)
        self.btn_fg.setMinimumHeight(32)
        self.btn_bg = QPushButton("Back")
        self.btn_bg.setFixedWidth(80)
        self.btn_bg.setMinimumHeight(32)

        # Default colors
        self.fg_color = self.filter_data.get("fg_color", "#000000")
        self.bg_color = self.filter_data.get("bg_color", "#FFFFFF")

        self.btn_fg.clicked.connect(self._pick_fg)
        self.btn_bg.clicked.connect(self._pick_bg)

        # Preview Label (Acts as the third column)
        self.lbl_preview = QLabel("Preview")
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setMinimumHeight(32)
        self.lbl_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        style_layout.addWidget(self.btn_fg)
        style_layout.addWidget(self.btn_bg)
        style_layout.addWidget(self.lbl_preview)

        self.content_layout.addLayout(style_layout)

        self.content_layout.addStretch() # Push buttons to bottom

        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.content_layout.addWidget(buttons)

        # Initial Update
        self._update_btn_styles()
        self._update_preview()

    def apply_theme(self):
        super().apply_theme() # Apply base modern dialog styles

        # Ensure buttons show correct theme adjusted preview
        self._update_btn_styles()
        self._update_preview()


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
        if not hasattr(self, 'lbl_preview') or not hasattr(self, 'pattern_edit'): return
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
        if not hasattr(self, 'btn_fg') or not hasattr(self, 'btn_bg'): return
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
