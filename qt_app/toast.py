from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QColor, QPalette

class Toast(QWidget):
    """
    A custom Toast notification widget for PySide6.
    Displays a message for a short duration and then fades out.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SubWindow)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # UI Setup
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setStyleSheet("""
            background-color: #333333;
            color: #ffffff;
            border-radius: 4px;
            padding: 8px 16px;
            font-family: Consolas;
            font-size: 12px;
            border: 1px solid #454545;
        """)

        # Drop shadow (simulated with border for now for simplicity/performance)

        self.layout.addWidget(self.label)

        # Animation setup
        self.opacity_anim = QPropertyAnimation(self, b"windowOpacity")
        self.opacity_anim.setDuration(300)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)

        self.hide()

    def show_message(self, message, duration=2000):
        self.label.setText(message)
        self.adjustSize()

        # Position: Bottom Center of parent
        parent_rect = self.parent().rect()
        x = (parent_rect.width() - self.width()) // 2
        y = parent_rect.height() - self.height() - 50 # 50px padding from bottom
        self.move(x, y)

        self.setWindowOpacity(0.0)
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
