from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QToolButton, QStyleOption, QStyle)
from PySide6.QtGui import QIcon, QPainter, QFont
from PySide6.QtCore import Qt
from .resources import get_svg_icon
import os

class CustomTitleBar(QWidget):
    def __init__(self, parent=None, title="Log Analyzer", hide_icon=False, show_minimize=True, show_maximize=True):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 0, 0)
        self.layout.setSpacing(5)

        # 1. App Icon
        self.icon_label = QLabel()
        self.icon_label.setFixedSize(20, 20)
        self.icon_label.setScaledContents(True)
        
        if not hide_icon:
            icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "loganalyzer.ico")
            if os.path.exists(icon_path):
                 self.icon_label.setPixmap(QIcon(icon_path).pixmap(24, 24))
            else:
                 self.icon_label.setPixmap(get_svg_icon("activity", "#888888").pixmap(24, 24))
            self.layout.addWidget(self.icon_label)
        else:
            self.icon_label.hide()
        
        # 2. Menu Bar Area (Menu will be inserted at index 1 externally if needed)
        
        # 3. Title (We want it ABSOLUTELY centered)
        self.title_label = QLabel(title, self)
        self.title_label.setAlignment(Qt.AlignCenter)
        font = QFont("Inter", 11)
        font.setBold(True)
        self.title_label.setFont(font)
        # Note: We don't add title_label to self.layout, handled in resizeEvent

        self.layout.addStretch()

        # 4. Window Controls
        self.btn_min = QToolButton()
        self.btn_max = QToolButton()
        self.btn_close = QToolButton()
        
        for btn in [self.btn_min, self.btn_max, self.btn_close]:
            btn.setFixedSize(46, 40)
            btn.setFocusPolicy(Qt.NoFocus)

        self.btn_min.clicked.connect(self.minimize_window)
        self.btn_max.clicked.connect(self.toggle_max_restore)
        self.btn_close.clicked.connect(self.close_window)

        if show_minimize:
            self.layout.addWidget(self.btn_min)
        else:
            self.btn_min.hide()
            
        if show_maximize:
            self.layout.addWidget(self.btn_max)
        else:
            self.btn_max.hide()
            
        self.layout.addWidget(self.btn_close)

    def paintEvent(self, event):
        # Mandatory for custom QWidget to support QSS background-color
        opt = QStyleOption()
        opt.initFrom(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, p, self)
        p.end()

    def resizeEvent(self, event):
        # Force title to be in the exact center of the bar
        bar_width = self.width()
        title_width = 600 # Assume a safe maximum width
        self.title_label.setGeometry((bar_width - title_width) // 2, 0, title_width, self.height())
        super().resizeEvent(event)

    def minimize_window(self):
        if self.window(): self.window().showMinimized()

    def close_window(self):
        if self.window(): self.window().close()

    def toggle_max_restore(self):
        win = self.window()
        if not win: return
        if win.isMaximized():
            win.showNormal()
        else:
            win.showMaximized()
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.y() < self.height():
            win = self.window()
            if win:
                win.windowHandle().startSystemMove()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_max_restore()
