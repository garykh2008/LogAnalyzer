from PySide6.QtWidgets import QScrollBar, QStyleOptionSlider, QStyle
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt


class SearchScrollBar(QScrollBar):
    def __init__(self, orientation=Qt.Vertical, parent=None):
        super().__init__(orientation, parent)
        self.search_results = []
        self.total_lines = 0
        self.mark_color = QColor("#f2c037") # Default orange-yellow
        self.is_dark = True

    def set_search_results(self, results, total_lines):
        self.search_results = results
        self.total_lines = max(1, total_lines)
        self.update()

    def set_theme(self, is_dark):
        self.is_dark = is_dark
        self.mark_color = QColor("#f2c037") if is_dark else QColor("#ff9800")
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        if not self.search_results or self.total_lines <= 0:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)

        opt = QStyleOptionSlider()
        self.initStyleOption(opt)

        groove_rect = self.style().subControlRect(QStyle.CC_ScrollBar, opt, QStyle.SC_ScrollBarGroove, self)
        h = groove_rect.height()
        y_offset = groove_rect.top()

        # Mark dimensions
        w = 6
        x = self.width() - w - 2

        painter.setPen(Qt.NoPen)
        painter.setBrush(self.mark_color)

        count = len(self.search_results)
        scale = h / self.total_lines

        # Optimization: If too many results, downsample to avoid drawing millions of rects
        # Max 2000 marks visually distinguishable
        step = max(1, count // 2000)

        # We need to draw specific unique Y positions
        # Use a set to avoid overdraw is good, but iterating huge list is slow.
        # Downsampling via slice is faster.

        subset = self.search_results[::step]

        for row in subset:
            y = int(row * scale) + y_offset
            # Draw 2px mark
            if y < y_offset + h:
                painter.drawRect(x, y, w, 2)

        painter.end()
