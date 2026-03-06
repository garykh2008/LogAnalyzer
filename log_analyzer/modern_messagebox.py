from PySide6.QtWidgets import QMessageBox, QPushButton, QVBoxLayout, QHBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from .modern_dialog import ModernDialog
from .theme_manager import theme_manager
from .native_window import apply_window_rounding
from .icon_manager import icon_manager

class ModernMessageBox(ModernDialog):
    """
    A custom message box that inherits from ModernDialog.
    Fixed missing icons and applied rounded corners.
    """
    def __init__(self, parent=None, title="Message", text="", icon_type=QMessageBox.Information, buttons=QMessageBox.Ok):
        super().__init__(parent, title=title, fixed_size=(450, 200))
        
        self.winId()
        apply_window_rounding(self.winId())

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        # Content Row (Icon + Text)
        content_row = QHBoxLayout()
        content_row.setSpacing(20)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(48, 48)
        self._set_msg_icon(icon_type)
        content_row.addWidget(self.icon_label)

        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setTextFormat(Qt.RichText)
        # Ensure text is readable in current theme
        self.text_label.setStyleSheet(f"color: {theme_manager.get_color('fg_primary')};")
        content_row.addWidget(self.text_label, 1)

        layout.addLayout(content_row)

        # Buttons Row
        self.button_box = QHBoxLayout()
        self.button_box.addStretch()
        self._add_buttons(buttons)
        layout.addLayout(self.button_box)

        self.setContentLayout(layout)

    def _set_msg_icon(self, icon_type):
        """Maps standard QMessageBox types to our theme icons."""
        p = theme_manager.palette
        icon_name = "activity" # Default
        color = p['accent']
        
        if icon_type == QMessageBox.Information:
            icon_name = "activity"
            color = p['accent']
        elif icon_type == QMessageBox.Warning:
            icon_name = "warning"
            color = "#f2c037"
        elif icon_type == QMessageBox.Critical:
            icon_name = "x-circle"
            color = "#c42b1c"
        elif icon_type == QMessageBox.Question:
            icon_name = "hash"
            color = p['accent']
            
        pixmap = icon_manager.load_pixmap(icon_name, color, 48, 48)
        self.icon_label.setPixmap(pixmap)

    def _add_buttons(self, buttons):
        if buttons & QMessageBox.Ok:
            btn = QPushButton("OK")
            btn.setMinimumWidth(80)
            btn.setDefault(True)
            btn.clicked.connect(self.accept)
            self.button_box.addWidget(btn)
        
        if buttons & QMessageBox.Save:
            btn = QPushButton("Save")
            btn.setDefault(True)
            btn.clicked.connect(self.accept)
            self.button_box.addWidget(btn)

        if buttons & QMessageBox.Discard:
            btn = QPushButton("Discard")
            btn.clicked.connect(lambda: self.done(QMessageBox.Discard))
            self.button_box.addWidget(btn)

        if buttons & QMessageBox.Cancel:
            btn = QPushButton("Cancel")
            btn.clicked.connect(self.reject)
            self.button_box.addWidget(btn)

        if buttons & QMessageBox.Yes:
            btn = QPushButton("Yes")
            btn.setDefault(True)
            btn.clicked.connect(self.accept)
            self.button_box.addWidget(btn)

        if buttons & QMessageBox.No:
            btn = QPushButton("No")
            btn.clicked.connect(self.reject)
            self.button_box.addWidget(btn)

    @staticmethod
    def information(parent, title, text):
        dlg = ModernMessageBox(parent, title, text, QMessageBox.Information)
        return dlg.exec()

    @staticmethod
    def warning(parent, title, text):
        dlg = ModernMessageBox(parent, title, text, QMessageBox.Warning)
        return dlg.exec()

    @staticmethod
    def critical(parent, title, text):
        dlg = ModernMessageBox(parent, title, text, QMessageBox.Critical)
        return dlg.exec()

    @staticmethod
    def question(parent, title, text, buttons=QMessageBox.Yes | QMessageBox.No, default_button=QMessageBox.Yes):
        dlg = ModernMessageBox(parent, title, text, QMessageBox.Question, buttons)
        return dlg.exec()
