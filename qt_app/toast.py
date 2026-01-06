from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QVBoxLayout, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QAbstractAnimation
from PySide6.QtGui import QColor, QPalette

class Toast(QWidget):
    """
    A custom Toast notification widget for PySide6.
    Displays a message for a short duration and then fades out.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents) # Click through
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # UI Setup
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        self.label = QLabel("")
        self.label.setAlignment(Qt.AlignCenter)
        self.label.setWordWrap(False)
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
        self.opacity_anim.finished.connect(self._on_anim_finished)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)

        self.is_fading_out = False
        self.hide()

    def show_message(self, message, duration=3000):
        # 1. Stop any existing animations or timers
        self.timer.stop()
        self.opacity_anim.stop()
        self.is_fading_out = False

        # 2. Update Content
        self.label.setText(message)
        self.label.adjustSize()
        self.adjustSize()

        # 3. Position
        if self.parent():
            parent_rect = self.parent().rect()
            x = (parent_rect.width() - self.width()) // 2
            y = parent_rect.height() - self.height() - 50
            self.move(x, y)

        # 4. Show & Animate In
        # If we were already visible/fading out, snapping to 0 might look jerky,
        # but for a "new message" it's better to restart the cycle clearly.
        self.opacity_effect.setOpacity(0.0)
        self.show()
        self.raise_()

        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.start()

        # 5. Schedule Fade Out
        # Wait for fade in (300ms) + duration
        self.timer.start(duration + 300)

    def fade_out(self):
        self.is_fading_out = True
        self.opacity_anim.setStartValue(1.0)
        self.opacity_anim.setEndValue(0.0)
        self.opacity_anim.start()

    def _on_anim_finished(self):
        # Only hide if we just finished the fade-out animation
        if self.is_fading_out:
            self.hide()
            self.is_fading_out = False
