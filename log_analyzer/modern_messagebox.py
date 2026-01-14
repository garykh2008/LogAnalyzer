from PySide6.QtWidgets import (QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox, QMessageBox)
from PySide6.QtCore import Qt
from .modern_dialog import ModernDialog
from .resources import get_svg_icon


class ModernMessageBox(ModernDialog):
    def __init__(self, parent=None, title="Message", text="", icon_name="message-info", buttons=QMessageBox.Ok, default_button=None):
        super().__init__(parent, title=title, fixed_size=(400, 180)) # Slightly wider, auto height if possible

        # Content Layout
        self.content_layout = QVBoxLayout() # Just a container
        self.content_layout.setSpacing(20)

        # Main Area: Icon + Text
        main_area = QHBoxLayout()
        main_area.setSpacing(20)

        # Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(48, 48)
        self.icon_label.setScaledContents(True)
        # Choose color based on type
        icon_color = "#cccccc" # Default
        if "info" in icon_name: icon_color = "#3794ff"
        elif "warn" in icon_name: icon_color = "#cca700"
        elif "error" in icon_name: icon_color = "#f44b56"
        elif "question" in icon_name: icon_color = "#3794ff"

        self.icon_label.setPixmap(get_svg_icon(icon_name, icon_color, 48).pixmap(48, 48))
        main_area.addWidget(self.icon_label, 0, Qt.AlignTop)

        # Text
        self.text_label = QLabel(text)
        self.text_label.setWordWrap(True)
        self.text_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        # Increase font size slightly
        f = self.text_label.font(); f.setPointSize(f.pointSize() + 1); self.text_label.setFont(f)

        main_area.addWidget(self.text_label, 1)
        self.content_layout.addLayout(main_area)

        self.content_layout.addStretch()

        # Buttons
        # Convert QMessageBox.StandardButtons to QDialogButtonBox.StandardButtons
        # Luckily they are usually binary compatible or we can map them

        # Simple mapping for common buttons
        btn_box_flags = QDialogButtonBox.NoButton

        # Mapping logic (simplified)
        if buttons & QMessageBox.Ok: btn_box_flags |= QDialogButtonBox.Ok
        if buttons & QMessageBox.Save: btn_box_flags |= QDialogButtonBox.Save
        if buttons & QMessageBox.SaveAll: btn_box_flags |= QDialogButtonBox.SaveAll
        if buttons & QMessageBox.Open: btn_box_flags |= QDialogButtonBox.Open
        if buttons & QMessageBox.Yes: btn_box_flags |= QDialogButtonBox.Yes
        if buttons & QMessageBox.YesToAll: btn_box_flags |= QDialogButtonBox.YesToAll
        if buttons & QMessageBox.No: btn_box_flags |= QDialogButtonBox.No
        if buttons & QMessageBox.NoToAll: btn_box_flags |= QDialogButtonBox.NoToAll
        if buttons & QMessageBox.Abort: btn_box_flags |= QDialogButtonBox.Abort
        if buttons & QMessageBox.Retry: btn_box_flags |= QDialogButtonBox.Retry
        if buttons & QMessageBox.Ignore: btn_box_flags |= QDialogButtonBox.Ignore
        if buttons & QMessageBox.Close: btn_box_flags |= QDialogButtonBox.Close
        if buttons & QMessageBox.Cancel: btn_box_flags |= QDialogButtonBox.Cancel
        if buttons & QMessageBox.Discard: btn_box_flags |= QDialogButtonBox.Discard
        if buttons & QMessageBox.Help: btn_box_flags |= QDialogButtonBox.Help
        if buttons & QMessageBox.Apply: btn_box_flags |= QDialogButtonBox.Apply
        if buttons & QMessageBox.Reset: btn_box_flags |= QDialogButtonBox.Reset
        if buttons & QMessageBox.RestoreDefaults: btn_box_flags |= QDialogButtonBox.RestoreDefaults

        self.button_box = QDialogButtonBox(btn_box_flags)
        self.button_box.clicked.connect(self._on_button_clicked)

        # Set Default Button
        if default_button:
            # We need to find the QAbstractButton corresponding to the standard button
            # This is tricky because QDialogButtonBox creates them internally
            # We can try to map back
            pass

        self.content_layout.addWidget(self.button_box)
        self.setContentLayout(self.content_layout)

        self.result_val = 0

    def _on_button_clicked(self, button):
        std_btn = self.button_box.standardButton(button)

        # Map QDialogButtonBox.StandardButton back to QMessageBox.StandardButton value
        try:
            self.result_val = QMessageBox.StandardButton(std_btn.value)
        except Exception:
            self.result_val = std_btn

        self.accept()

    @staticmethod
    def information(parent, title, text, buttons=QMessageBox.Ok, default_button=QMessageBox.Ok):
        dlg = ModernMessageBox(parent, title, text, "message-info", buttons, default_button)
        dlg.exec()
        return dlg.result_val

    @staticmethod
    def warning(parent, title, text, buttons=QMessageBox.Ok, default_button=QMessageBox.Ok):
        dlg = ModernMessageBox(parent, title, text, "message-warn", buttons, default_button)
        dlg.exec()
        return dlg.result_val

    @staticmethod
    def critical(parent, title, text, buttons=QMessageBox.Ok, default_button=QMessageBox.Ok):
        dlg = ModernMessageBox(parent, title, text, "message-error", buttons, default_button)
        dlg.exec()
        return dlg.result_val

    @staticmethod
    def question(parent, title, text, buttons=QMessageBox.Yes | QMessageBox.No, default_button=QMessageBox.Yes):
        dlg = ModernMessageBox(parent, title, text, "message-question", buttons, default_button)
        dlg.exec()
        return dlg.result_val
