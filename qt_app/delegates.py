from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtGui import QTextDocument, QAbstractTextDocumentLayout, QPalette, QColor
from PySide6.QtCore import QSize, QRectF, Qt

class LogDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hover_color = QColor("#2a2d2e")
        self.search_query = None
        self.search_match_color = QColor("#653306")
        self.search_match_text_color = QColor("#ffffff")

    def set_hover_color(self, color):
        self.hover_color = QColor(color)

    def set_search_query(self, query):
        self.search_query = query

    def paint(self, painter, option, index):
        painter.save()
        try:
            # 1. Background
            bg_color = None
            state = option.state

            # Priority: Selection > Hover > Filter Color

            if state & QStyle.State_Selected:
                bg_color = option.palette.highlight()
            elif state & QStyle.State_MouseOver:
                 bg_color = self.hover_color
            else:
                # Check model for background color (Filter)
                model_bg = index.data(Qt.BackgroundRole)
                if model_bg and isinstance(model_bg, QColor):
                    bg_color = model_bg

            if bg_color:
                painter.fillRect(option.rect, bg_color)

            # 2. Text
            text = index.data(Qt.DisplayRole)
            if text:
                # Setup Pen
                if state & QStyle.State_Selected:
                    painter.setPen(option.palette.highlightedText().color())
                else:
                    # Check model for foreground (Filter)
                    model_fg = index.data(Qt.ForegroundRole)
                    if model_fg and isinstance(model_fg, QColor):
                        painter.setPen(model_fg)
                    else:
                        painter.setPen(option.palette.text().color())

                rect = option.rect.adjusted(4, 0, -4, 0)

                # Search Highlight check
                # FIX: "ctrl+right highlight everything" implies search_query might be "" or handled wrong
                # .find() with empty string returns 0, infinite loop potential if not careful,
                # but we usually check if query is truthy.
                if self.search_query and self.search_query.strip() and self.search_query.lower() in text.lower():
                    self._paint_highlighted_text(painter, rect, text, option)
                else:
                    font_metrics = option.fontMetrics
                    elided_text = font_metrics.elidedText(text, Qt.ElideNone, rect.width())
                    painter.drawText(rect, Qt.AlignLeft, elided_text)

        finally:
            painter.restore()

    def _paint_highlighted_text(self, painter, rect, text, option):
        query = self.search_query
        lower_query = query.lower()
        lower_text = text.lower()

        start = 0
        x = rect.left()
        y = rect.top() + option.fontMetrics.ascent()

        # Use current pen (set in paint method) as base text color
        base_pen = painter.pen()

        while True:
            idx = lower_text.find(lower_query, start)
            if idx == -1:
                remaining = text[start:]
                painter.setPen(base_pen)
                painter.drawText(x, y, remaining)
                break

            pre_text = text[start:idx]
            if pre_text:
                painter.setPen(base_pen)
                painter.drawText(x, y, pre_text)
                x += option.fontMetrics.horizontalAdvance(pre_text)

            match_text = text[idx:idx+len(query)]
            match_width = option.fontMetrics.horizontalAdvance(match_text)

            bg_rect = QRectF(x, rect.top(), match_width, rect.height())
            painter.fillRect(bg_rect, self.search_match_color)

            painter.setPen(self.search_match_text_color)
            painter.drawText(x, y, match_text)
            x += match_width

            start = idx + len(query)

    def sizeHint(self, option, index):
        # Ensure fast return
        return QSize(option.rect.width(), option.fontMetrics.height())
