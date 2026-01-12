from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QHBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, Signal, QPoint, QEasingCurve, QObject, QRect
from PySide6.QtGui import QColor
from .resources import get_svg_icon

class ToastNotification(QWidget):
    closed = Signal()

    def __init__(self, message, type_str="info", duration=3000, is_dark=True):
        super().__init__(None) # Top-level window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # Main Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 2, 10, 10) # Minimal top margin

        # Content Frame
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

        # Theme Colors
        if is_dark:
            text_color = "#ffffff"
            border_color = "#454545"
            if type_str == "success": bg_color = "#1e3a1e"
            elif type_str == "error": bg_color = "#3a1e1e"
            elif type_str == "warning": bg_color = "#3a3a1e"
            else: bg_color = "#252526"
        else:
            text_color = "#333333"
            border_color = "#cccccc"
            if type_str == "success": bg_color = "#f0fff4"
            elif type_str == "error": bg_color = "#fff0f0"
            elif type_str == "warning": bg_color = "#fffbe6"
            else: bg_color = "#ffffff"

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

        # Shadow
        self.shadow = QGraphicsDropShadowEffect(self.content_frame)
        self.shadow.setBlurRadius(15)
        self.shadow.setXOffset(0)
        self.shadow.setYOffset(4)
        self.shadow.setColor(QColor(0, 0, 0, 60))
        self.content_frame.setGraphicsEffect(self.shadow)

        # Inner Content
        frame_layout = QHBoxLayout(self.content_frame)
        frame_layout.setContentsMargins(12, 10, 16, 10)
        frame_layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setFixedSize(18, 18)
        icon_label.setScaledContents(True)
        icon_label.setPixmap(get_svg_icon(cfg['icon'], cfg['border'], 18).pixmap(18, 18))
        frame_layout.addWidget(icon_label)

        text_label = QLabel(message)
        frame_layout.addWidget(text_label)

        # Animation (Window Opacity)
        self.setWindowOpacity(0.0)
        self.anim = QPropertyAnimation(self, b"windowOpacity")
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

class Toast(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_widget = parent
        self.is_dark_mode = True
        self.notifications = []

    def set_theme(self, is_dark):
        self.is_dark_mode = is_dark

    def show_message(self, message, duration=3000, type_str="info"):
        if len(self.notifications) >= 5:
            oldest = self.notifications.pop(0)
            oldest.close_notification()

        notif = ToastNotification(message, type_str, duration, self.is_dark_mode)
        # Ensure it's shown to calculate size hint
        notif.show()
        notif.adjustSize() 
        
        self.notifications.append(notif)
        notif.closed.connect(lambda: self._remove_notification(notif))
        
        self.reposition_all()

    def _remove_notification(self, notif):
        if notif in self.notifications:
            self.notifications.remove(notif)
        self.reposition_all()

    def reposition_all(self):
        if not self.parent_widget: return
        
        geo = self.parent_widget.geometry()
        # Start from bottom center
        base_y = geo.y() + geo.height() - 60 
        center_x = geo.x() + geo.width() // 2
        
        # Iterate backwards (newest at bottom)
        for notif in reversed(self.notifications):
            w = notif.width()
            h = notif.height()
            x = center_x - w // 2
            y = base_y - h
            
            notif.move(x, y)
            
            base_y -= (h - 8) # Spacing adjustment to account for shadow overlap

    # Called by MainWindow on move/resize
    def resize_to_parent(self):
        self.reposition_all()
    
    # Compatibility with previous interface
    def raise_(self):
        for n in self.notifications:
            n.raise_()