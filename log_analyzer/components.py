from PySide6.QtWidgets import (QWidget, QHBoxLayout, QLabel, QToolButton, QStyleOption, QStyle, QApplication, QLineEdit, QFrame, QVBoxLayout, QGraphicsOpacityEffect, QGraphicsDropShadowEffect, QComboBox, QSizePolicy, QCompleter)
from PySide6.QtGui import QIcon, QPainter, QFont, QColor
from PySide6.QtCore import Qt, QRect, Signal, QTimer, QPropertyAnimation, QEasingCurve, QStringListModel
from .resources import get_svg_icon
import os

class CustomTitleBar(QWidget):
    def __init__(self, parent=None, title="Log Analyzer", hide_icon=False, show_minimize=True, show_maximize=True):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(10, 0, 0, 0)
        self.layout.setSpacing(5)
        self.click_pos = None

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
        
        self.btn_min.setToolTip("Minimize")
        self.btn_max.setToolTip("Maximize")
        self.btn_close.setToolTip("Close")

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
        if event.button() == Qt.LeftButton:
            self.click_pos = event.globalPosition().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.click_pos and event.buttons() & Qt.LeftButton:
            diff = (event.globalPosition().toPoint() - self.click_pos).manhattanLength()
            if diff > QApplication.startDragDistance():
                win = self.window()
                if win:
                    win.windowHandle().startSystemMove()
                    self.click_pos = None
        super().mouseMoveEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_max_restore()


class DimmerOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False) # Catch mouse events
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 100)) # Semi-transparent black

    def showEvent(self, event):
        if self.parent():
            self.resize(self.parent().size())
        self.raise_()
        super().showEvent(event)
        
    def mousePressEvent(self, event):
        # Consume event to block interaction with underlying window
        pass


class BadgeToolButton(QToolButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.badge_label = QLabel(self)
        self.badge_label.hide()
        self.badge_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.badge_label.setAlignment(Qt.AlignCenter)
        self._bg_color = "#007acc"
        self._update_style()

    def _update_style(self):
        self.badge_label.setStyleSheet(f"""
            background-color: {self._bg_color};
            color: white;
            border-radius: 8px;
            font-weight: bold;
            font-family: Inter, Segoe UI;
            font-size: 10px;
        """)

    def set_badge(self, text, bg_color=None):
        if not text or str(text) == "0":
            self.badge_label.hide()
            return
            
        self.badge_label.setText(str(text))
        if bg_color: 
            self._bg_color = bg_color
            self._update_style()
        
        # Calculate width: min 16px, expand for longer text
        fm = self.badge_label.fontMetrics()
        w = max(16, fm.horizontalAdvance(str(text)) + 6)
        self.badge_label.setFixedSize(w, 16)
        
        self.badge_label.show()
        self.badge_label.raise_()
        self._update_pos()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_pos()
        
    def _update_pos(self):
        if self.badge_label.isVisible():
            x = self.width() - self.badge_label.width() - 4
            y = 4
            self.badge_label.move(x, y)


class ClickableLabel(QLabel):
    clicked = Signal()
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor) # Always show hand cursor to indicate interactivity

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class LoadingSpinner(QWidget):
    def __init__(self, parent=None, size=16, color="#007acc"):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._color = color
        self._angle = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._rotate)
        self.icon_pixmap = get_svg_icon("loader", self._color, size).pixmap(size, size)
        self.hide()

    def _rotate(self):
        self._angle = (self._angle + 30) % 360
        self.update()

    def start(self):
        if not self.timer.isActive():
            self.show()
            self.timer.start(50)

    def stop(self):
        self.timer.stop()
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self._angle)
        painter.translate(-self.width() / 2, -self.height() / 2)
        
        painter.drawPixmap(0, 0, self.icon_pixmap)
        painter.end()


class HistoryLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Down:
            self.show_history()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        # Show history on click if empty, or maybe always if user wants to see history?
        # Standard combo box behavior: click shows list.
        # But for line edit, click usually moves cursor.
        # Let's show only if text is empty, mimicking "recent searches".
        if not self.text():
            self.show_history()

    def show_history(self):
        c = self.completer()
        if c:
            c.setCompletionPrefix("") 
            c.complete() 


class SearchOverlay(QWidget):
    findNext = Signal(str, bool, bool) # text, case, wrap
    findPrev = Signal(str, bool, bool)
    closed = Signal()
    searchChanged = Signal(str, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(550)
        self.hide()
        
        # Card Frame
        self.card = QFrame(self)
        self.card.setObjectName("SearchCard")
        
        # Shadow
        self.shadow = QGraphicsDropShadowEffect(self.card)
        self.shadow.setBlurRadius(20)
        self.shadow.setColor(QColor(0, 0, 0, 100))
        self.shadow.setOffset(0, 4)
        self.card.setGraphicsEffect(self.shadow)
        
        # Layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.addWidget(self.card)
        
        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(10, 6, 10, 6)
        card_layout.setSpacing(6)
        
        # Input
        self.input = HistoryLineEdit()
        self.input.setPlaceholderText("Find...")
        self.input.setMinimumHeight(28)
        self.input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.input.returnPressed.connect(self._on_return_pressed)
        
        self.history_model = QStringListModel()
        self.completer = QCompleter(self.history_model, self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.input.setCompleter(self.completer)
        
        card_layout.addWidget(self.input, 1)
        
        # Buttons
        self.btn_case = QToolButton()
        self.btn_case.setCheckable(True)
        self.btn_case.setToolTip("Match Case")
        self.btn_case.setFixedSize(28, 28) # 也稍微加大按鈕
        self.btn_case.toggled.connect(self._on_search_params_changed)
        
        self.btn_wrap = QToolButton()
        self.btn_wrap.setCheckable(True)
        self.btn_wrap.setChecked(True)
        self.btn_wrap.setToolTip("Wrap Search")
        self.btn_wrap.setFixedSize(28, 28)
        
        self.btn_prev = QToolButton()
        self.btn_prev.setFixedSize(28, 28)
        self.btn_prev.clicked.connect(lambda: self.findPrev.emit(self.input.text(), self.btn_case.isChecked(), self.btn_wrap.isChecked()))
        
        self.btn_next = QToolButton()
        self.btn_next.setFixedSize(28, 28)
        self.btn_next.clicked.connect(lambda: self.findNext.emit(self.input.text(), self.btn_case.isChecked(), self.btn_wrap.isChecked()))
        
        self.info_label = QLabel()
        self.info_label.setMinimumWidth(40)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("color: #888888; font-size: 11px;")
        
        self.btn_close = QToolButton()
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.clicked.connect(self.hide_overlay)
        
        card_layout.addWidget(self.btn_case)
        card_layout.addWidget(self.btn_wrap)
        card_layout.addWidget(self.btn_prev)
        card_layout.addWidget(self.btn_next)
        card_layout.addWidget(self.info_label)
        card_layout.addWidget(self.btn_close)

    def _on_return_pressed(self):
        text = self.input.text()
        if text:
            history = self.history_model.stringList()
            if text in history: history.remove(text)
            history.insert(0, text)
            if len(history) > 10: history = history[:10]
            self.history_model.setStringList(history)
            
        self.findNext.emit(text, self.btn_case.isChecked(), self.btn_wrap.isChecked())

    def _on_search_params_changed(self):
        self.searchChanged.emit(self.input.text(), self.btn_case.isChecked())

    def show_overlay(self):
        self.adjustSize()
        self.show()
        self.raise_()
        self.input.setFocus()
        self.input.selectAll()

    def hide_overlay(self):
        self.hide()
        self.set_results_info("")
        self.closed.emit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.hide_overlay()
        else:
            super().keyPressEvent(event)

    def set_results_info(self, text):
        self.info_label.setText(text)

    def apply_theme(self, is_dark):
        if is_dark:
            bg = "#252526"
            fg = "#cccccc"
            border = "#454545"
            input_bg = "#3c3c3c"
        else:
            bg = "#ffffff"
            fg = "#333333"
            border = "#cccccc"
            input_bg = "#f3f3f3"
            
        self.card.setStyleSheet(f"""
            #SearchCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            QLineEdit {{
                background-color: {input_bg};
                color: {fg};
                border: 1px solid {border};
                border-radius: 4px;
                padding: 2px 6px;
            }}
            QToolButton {{
                background: transparent;
                border: 1px solid transparent;
                border-radius: 4px;
            }}
            QToolButton:hover {{
                background-color: rgba(128, 128, 128, 40);
                border: 1px solid {border};
            }}
            QToolButton:checked {{
                background-color: rgba(0, 122, 204, 80);
                border: 1px solid {border};
            }}
        """)
        ic = fg
        self.btn_case.setIcon(get_svg_icon("case-sensitive", ic, 16))
        self.btn_wrap.setIcon(get_svg_icon("wrap", ic, 16))
        self.btn_prev.setIcon(get_svg_icon("chevron-up", ic, 16))
        self.btn_next.setIcon(get_svg_icon("chevron-down", ic, 16))
        self.btn_close.setIcon(get_svg_icon("x-close", ic, 16))





