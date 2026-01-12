from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QHBoxLayout, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, Signal, QPoint, QEasingCurve, QSize
from PySide6.QtGui import QColor, QPalette, QPainter
from .resources import get_svg_icon

class ToastNotification(QWidget): # Container Widget for Opacity
    closed = Signal()

    def __init__(self, parent, message, type_str="info", duration=3000, is_dark=True):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents) 
        
        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(4, 4, 4, 4) # Space for shadow
        
        # Content Frame (The actual visible part)
        self.content_frame = QFrame()
        self.content_frame.setObjectName("ToastContent")
        self.layout.addWidget(self.content_frame)
        
        # Style Config
        colors = {
            "info":    {"border": "#3794ff", "icon": "message-info"},
            "success": {"border": "#28a745", "icon": "check-circle"},
            "warning": {"border": "#ffc107", "icon": "message-warn"},
            "error":   {"border": "#dc3545", "icon": "message-error"}
        }
        cfg = colors.get(type_str, colors["info"])
        
        # Theme Colors with Tint
        if is_dark:
            text_color = "#ffffff"
            border_color = "#454545"
            # Subtle background tints for dark mode
            if type_str == "success": bg_color = "#1e3a1e" 
            elif type_str == "error": bg_color = "#3a1e1e"
            elif type_str == "warning": bg_color = "#3a3a1e"
            else: bg_color = "#252526"
        else:
            text_color = "#333333"
            border_color = "#cccccc"
            # Subtle background tints for light mode
            if type_str == "success": bg_color = "#f0fff4"
            elif type_str == "error": bg_color = "#fff0f0"
            elif type_str == "warning": bg_color = "#fffbe6"
            else: bg_color = "#ffffff"

        # Stylesheet
        self.content_frame.setStyleSheet(f"""
            #ToastContent {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 4px;
                border: 1px solid {border_color};
                border-left: 4px solid {cfg['border']};
            }}
            QLabel {{
                color: {text_color};
                background: transparent;
                font-family: "Segoe UI", "Inter", sans-serif;
                font-size: 13px;
            }}
        """)
        
        # Shadow Effect (Applied to Content Frame)
        self.shadow = QGraphicsDropShadowEffect(self.content_frame)
        self.shadow.setBlurRadius(15)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(4)
        self.shadow.setColor(QColor(0, 0, 0, 60)) # Semi-transparent black shadow
        self.content_frame.setGraphicsEffect(self.shadow)
        
        # Inner Layout
        frame_layout = QHBoxLayout(self.content_frame)
        frame_layout.setContentsMargins(12, 10, 16, 10)
        frame_layout.setSpacing(12)
        
        # Icon
        icon_label = QLabel()
        icon_label.setFixedSize(18, 18)
        icon_label.setScaledContents(True)
        # Use border color for icon to match theme
        icon_label.setPixmap(get_svg_icon(cfg['icon'], cfg['border'], 18).pixmap(18, 18))
        frame_layout.addWidget(icon_label)
        
        # Text
        text_label = QLabel(message)
        frame_layout.addWidget(text_label)
        
        # Opacity Effect for Animation (Applied to SELF - the container)
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        
        # Fade In Animation
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(250)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()
        
        # Timer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.fade_out)
        self.timer.start(duration)

    def fade_out(self):
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setDuration(250)
        self.anim.finished.connect(self.close_notification)
        self.anim.start()

    def close_notification(self):
        self.closed.emit()
        self.deleteLater()

class Toast(QWidget):
    """
    Toast Manager that handles stacking notifications.
    Uses Qt.Tool to float above everything.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        self.is_dark_mode = True # Default
        
        # Container Layout - Stack from bottom
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 40) # Bottom padding relative to window
        self.layout.setSpacing(8)
        self.layout.setAlignment(Qt.AlignBottom | Qt.AlignHCenter)
        
        self.notifications = []
        
        # Initial size
        if parent:
            self.resize_to_parent()

    def set_theme(self, is_dark):
        self.is_dark_mode = is_dark

    def show_message(self, message, duration=3000, type_str="info"):
        # Limit max notifications to avoid screen clutter
        if len(self.notifications) >= 5:
            # Remove oldest
            oldest = self.notifications.pop(0)
            self.layout.removeWidget(oldest)
            oldest.deleteLater()

        notif = ToastNotification(self, message, type_str, duration, self.is_dark_mode)
        self.layout.addWidget(notif)
        self.notifications.append(notif)
        
        notif.closed.connect(lambda: self._remove_notification(notif))
        
        notif.show()
        self.show()
        self.raise_()

    def _remove_notification(self, notif):
        if notif in self.notifications:
            self.notifications.remove(notif)
            self.layout.removeWidget(notif)
            # notif.deleteLater() is called inside notif.close_notification

    def resize_to_parent(self):
        if self.parent():
            self.setGeometry(self.parent().geometry())
