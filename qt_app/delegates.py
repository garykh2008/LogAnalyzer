from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtGui import QTextDocument, QAbstractTextDocumentLayout, QPalette, QColor
from PySide6.QtCore import QSize, QRectF, Qt

class LogDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hover_color = QColor("#2a2d2e")
        self.search_query = None
        self.search_case_sensitive = False
        self.search_match_color = QColor("#653306")
        self.search_match_text_color = QColor("#ffffff")
        self.max_line_number = 1000

    def set_hover_color(self, color):
        self.hover_color = QColor(color)

    def set_max_line_number(self, count):
        self.max_line_number = count

    def set_search_query(self, query, case_sensitive=False):
        self.search_query = query
        self.search_case_sensitive = case_sensitive

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

            # --- Line Number ---
            raw_index = index.data(Qt.UserRole + 1)
            
            # Calculate width based on max lines
            digits = len(str(self.max_line_number))
            char_w = option.fontMetrics.horizontalAdvance('8')
            line_num_width = max(40, digits * char_w + 15)
            
            if raw_index is not None:
                line_num_str = str(raw_index + 1)
                
                # Line Num Background
                line_bg_rect = QRectF(option.rect.left(), option.rect.top(), line_num_width, option.rect.height())
                # Calculate subtle bg based on base color
                base_col = option.palette.color(QPalette.Base)
                if base_col.lightness() > 128:
                    num_bg = QColor(240, 240, 240) # Light theme
                    num_fg = QColor(128, 128, 128)
                else:
                    num_bg = QColor(40, 40, 40) # Dark theme
                    num_fg = QColor(100, 100, 100)
                
                painter.fillRect(line_bg_rect, num_bg)
                
                # Line Num Text
                painter.save()
                painter.setPen(num_fg)
                painter.drawText(line_bg_rect.adjusted(0, 0, -5, 0), Qt.AlignRight | Qt.AlignVCenter, line_num_str)
                painter.restore()

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

                rect = option.rect.adjusted(line_num_width + 8, 0, -4, 0)

                # Search Highlight check
                should_highlight = False
                if self.search_query and self.search_query.strip():
                    if self.search_case_sensitive:
                        if self.search_query in text: should_highlight = True
                    else:
                        if self.search_query.lower() in text.lower(): should_highlight = True
                
                if should_highlight:
                    self._paint_highlighted_text(painter, rect, text, option)
                else:
                    font_metrics = option.fontMetrics
                    elided_text = font_metrics.elidedText(text, Qt.ElideNone, rect.width())
                    painter.drawText(rect, Qt.AlignLeft, elided_text)

        finally:
            painter.restore()

    def _paint_highlighted_text(self, painter, rect, text, option):
        query = self.search_query
        
        if self.search_case_sensitive:
            search_text = text
            search_query = query
        else:
            search_text = text.lower()
            search_query = query.lower()

        start = 0
        x = rect.left()
        y = rect.top() + option.fontMetrics.ascent()

        # Use current pen (set in paint method) as base text color
        base_pen = painter.pen()

        while True:
            idx = search_text.find(search_query, start)
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
