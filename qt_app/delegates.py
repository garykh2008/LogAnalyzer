from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtGui import QTextDocument, QAbstractTextDocumentLayout, QPalette, QColor
from PySide6.QtCore import QSize, QRectF, Qt

class LogDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hover_color = QColor("#2a2d2e") # Default Dark Mode Hover
        self.search_query = None
        self.search_match_color = QColor("#653306") # Orange-ish highlight background
        self.search_match_text_color = QColor("#ffffff") # White text on highlight

    def set_hover_color(self, color):
        self.hover_color = QColor(color)

    def set_search_query(self, query):
        self.search_query = query

    def paint(self, painter, option, index):
        painter.save()
        try:
            # 1. Background (Selection & Hover)
            bg_color = None
            state = option.state

            # Check Selection
            if state & QStyle.State_Selected:
                bg_color = option.palette.highlight()
            elif state & QStyle.State_MouseOver:
                 bg_color = self.hover_color

            if bg_color:
                painter.fillRect(option.rect, bg_color)

            # 2. Text Drawing
            text = index.data(Qt.DisplayRole)
            if text:
                # Calculate rect with padding
                rect = option.rect.adjusted(4, 0, -4, 0)

                # Check for Search Highlight
                if self.search_query and self.search_query.lower() in text.lower():
                    self._paint_highlighted_text(painter, rect, text, option)
                else:
                    # Standard Drawing
                    if state & QStyle.State_Selected:
                        painter.setPen(option.palette.highlightedText().color())
                    else:
                        painter.setPen(option.palette.text().color())

                    font_metrics = option.fontMetrics
                    elided_text = font_metrics.elidedText(text, Qt.ElideNone, rect.width())
                    painter.drawText(rect, Qt.AlignLeft, elided_text)

        finally:
            painter.restore()

    def _paint_highlighted_text(self, painter, rect, text, option):
        """Draws text with search highlights."""
        query = self.search_query
        lower_query = query.lower()
        lower_text = text.lower()

        start = 0
        x = rect.left()
        y = rect.top() + option.fontMetrics.ascent() # Draw baseline

        # Default colors
        default_pen = option.palette.text().color()
        if option.state & QStyle.State_Selected:
            default_pen = option.palette.highlightedText().color()

        while True:
            idx = lower_text.find(lower_query, start)
            if idx == -1:
                # Draw remaining text
                remaining = text[start:]
                painter.setPen(default_pen)
                painter.drawText(x, y, remaining)
                break

            # Draw highlight
            # 1. Text before match
            pre_text = text[start:idx]
            if pre_text:
                painter.setPen(default_pen)
                painter.drawText(x, y, pre_text)
                x += option.fontMetrics.horizontalAdvance(pre_text)

            # 2. Match text
            match_text = text[idx:idx+len(query)]
            match_width = option.fontMetrics.horizontalAdvance(match_text)

            # Draw highlight background
            # Note: rect.top() is the top of the cell, y is baseline.
            # We want to fill the cell height roughly.
            bg_rect = QRectF(x, rect.top(), match_width, rect.height())
            painter.fillRect(bg_rect, self.search_match_color)

            # Draw highlight text
            painter.setPen(self.search_match_text_color)
            painter.drawText(x, y, match_text)
            x += match_width

            start = idx + len(query)

    def sizeHint(self, option, index):
        height = option.fontMetrics.height()
        return QSize(option.rect.width(), height)
