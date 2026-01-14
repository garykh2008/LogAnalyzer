from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QFrame, QHBoxLayout, QGraphicsDropShadowEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, Signal, QPoint, QEasingCurve, QObject, QRect
from PySide6.QtGui import QColor
from .resources import get_svg_icon
import sys

class ToastNotification(QWidget):
    closed = Signal()

    def __init__(self, parent, message, type_str="info", duration=3000, is_dark=True, font_size=13):
        # On Linux, parent is centralWidget (Child Widget mode)
        # On Windows, parent is None (Independent Window mode)
        super().__init__(parent)
        
        if sys.platform != "linux":
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
            self.setAttribute(Qt.WA_TranslucentBackground)
            self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        # UI Setup
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 2, 10, 10)

        self.content_frame = QFrame()
        self.content_frame.setObjectName("ToastContent")
        self.main_layout.addWidget(self.content_frame)

        colors = {
            "info":    {"border": "#3794ff", "icon": "message-info"},
            "success": {"border": "#28a745", "icon": "check-circle"},
            "warning": {"border": "#ffc107", "icon": "message-warn"},
            "error":   {"border": "#dc3545", "icon": "message-error"}
        }
        cfg = colors.get(type_str, colors["info"])

        if is_dark:
            text_color = "#ffffff"; border_color = "#454545"
            bg_color = {"success":"#1e3a1e", "error":"#3a1e1e", "warning":"#3a3a1e"}.get(type_str, "#252526")
        else:
            text_color = "#333333"; border_color = "#cccccc"
            bg_color = {"success":"#f0fff4", "error":"#fff0f0", "warning":"#fffbe6"}.get(type_str, "#ffffff")

        self.content_frame.setStyleSheet(f"""
            #ToastContent {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: 4px;
                border: 1px solid {border_color};
                border-left: 4px solid {cfg['border']};
            }}
            QLabel {{ color: {text_color}; background: transparent; font-family: "Segoe UI", "Inter", sans-serif; font-size: {font_size}px; }}
        """)

        self.shadow = QGraphicsDropShadowEffect(self.content_frame)
        self.shadow.setBlurRadius(15); self.shadow.setXOffset(0); self.shadow.setYOffset(4); self.shadow.setColor(QColor(0, 0, 0, 60))
        self.content_frame.setGraphicsEffect(self.shadow)

        frame_layout = QHBoxLayout(self.content_frame)
        frame_layout.setContentsMargins(12, 10, 16, 10); frame_layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setFixedSize(18, 18); icon_label.setScaledContents(True)
        icon_label.setPixmap(get_svg_icon(cfg['icon'], cfg['border'], 18).pixmap(18, 18))
        frame_layout.addWidget(icon_label)

        text_label = QLabel(message)
        frame_layout.addWidget(text_label)

        # Animation logic
        if sys.platform == "linux":
            # No windowOpacity for child widgets, just show/hide
            self.timer = QTimer(self)
            self.timer.setSingleShot(True); self.timer.timeout.connect(self.close_notification)
            self.timer.start(duration)
        else:
            self.setWindowOpacity(0.0)
            self.anim = QPropertyAnimation(self, b"windowOpacity")
            self.anim.setDuration(300); self.anim.setStartValue(0.0); self.anim.setEndValue(1.0); self.anim.setEasingCurve(QEasingCurve.OutQuint); self.anim.start()
            self.timer = QTimer(self)
            self.timer.setSingleShot(True); self.timer.timeout.connect(self.fade_out); self.timer.start(duration)

    def fade_out(self):
        self.anim.setStartValue(1.0); self.anim.setEndValue(0.0); self.anim.setDuration(300); self.anim.setEasingCurve(QEasingCurve.InQuint); self.anim.finished.connect(self.close_notification); self.anim.start()

    def close_notification(self):
        self.closed.emit()
        self.deleteLater()

class Toast(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent_window = parent # MainWindow
        self.is_dark_mode = True
        self.font_size = 13
        self.notifications = []

    def set_theme(self, is_dark, font_size=None):
        self.is_dark_mode = is_dark
        if font_size: self.font_size = font_size

    def show_message(self, message, duration=3000, type_str="info"):
        if len(self.notifications) >= 5:
            oldest = self.notifications.pop(0)
            oldest.close_notification()

        # Use centralWidget as parent on Linux to keep toast inside window but below title bar
        p = self.parent_window.centralWidget() if sys.platform == "linux" else None
        notif = ToastNotification(p, message, type_str, duration, self.is_dark_mode, self.font_size)
        
        self.notifications.append(notif)
        notif.closed.connect(lambda: self._remove_notification(notif))
        
        notif.show()
        notif.adjustSize()
        self.reposition_all()

    def _remove_notification(self, notif):
        if notif in self.notifications:
            self.notifications.remove(notif)
        self.reposition_all()

    def reposition_all(self):
        if not self.parent_window: return
        
        if sys.platform == "linux":
            # Position relative to centralWidget
            cw = self.parent_window.centralWidget()
            if not cw: return
            base_y = cw.height() - 20
            center_x = cw.width() // 2
            for notif in reversed(self.notifications):
                w, h = notif.width(), notif.height()
                notif.move(center_x - w // 2, base_y - h)
                base_y -= (h - 8)
        else:
            # Position relative to screen (Windows)
            parent_pos = self.parent_window.mapToGlobal(QPoint(0, 0))
            base_y = parent_pos.y() + self.parent_window.height() - 60 
            center_x = parent_pos.x() + self.parent_window.width() // 2
            for notif in reversed(self.notifications):
                w, h = notif.width(), notif.height()
                notif.move(center_x - w // 2, base_y - h)
                base_y -= (h - 8)

    def resize_to_parent(self):
        self.reposition_all()
    
    def raise_(self):
        for n in self.notifications: n.raise_()