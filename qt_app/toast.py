from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPalette

class Toast(QWidget):
    """
    A custom Toast notification widget for PySide6.
    Displays a message for a short duration and then fades out.
    """
    def __init__(self, parent):
        super().__init__(parent)
        # Use ToolTip or Popup to allow it to float above but stay attached logically
        # However, for a simple in-app toast, just being a child with Raise is fine.
        # But for opacity animation on child widgets, we need QGraphicsOpacityEffect.
        self.setAttribute(Qt.WA_TransparentForMouseEvents) # Click through
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # UI Setup
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(False) # Disable wrapping per user request
        self.label.setStyleSheet("""
            background-color: #333333;
            color: #ffffff;
            border-radius: 4px;
            padding: 8px 16px;
            font-family: Consolas;
            font-size: 12px;
            border: 1px solid #454545;
        """)

        self.layout.addWidget(self.label)

        # Opacity Effect
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        # Animation setup
        self.opacity_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.opacity_anim.setDuration(300)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)

        self.hide()

    def show_message(self, message, duration=3000):
        self.label.setText(message)
        self.label.adjustSize()
        self.adjustSize()

        # Position: Bottom Center of parent
        if self.parent():
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            y = parent_rect.height() - self.height() - 50 # 50px padding from bottom
            self.move(x, y)

        self.opacity_effect.setOpacity(0.0)
        self.show()
        self.raise_()

        # Fade In
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.start()

        # Start timer for fade out
        self.timer.start(duration)

    def fade_out(self):
        self.opacity_anim.setStartValue(1.0)
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.finished.connect(self.hide)
        self.opacity_anim.start()
