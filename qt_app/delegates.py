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
            # Get horizontal scroll offset to keep line numbers fixed
            scroll_x = option.widget.horizontalScrollBar().value() if option.widget else 0
            
            # 1. Background
            bg_color = None
            state = option.state

            if state & QStyle.State_Selected:
                bg_color = option.palette.highlight()
            elif state & QStyle.State_MouseOver:
                 bg_color = self.hover_color
            else:
                model_bg = index.data(Qt.BackgroundRole)
                if model_bg and isinstance(model_bg, QColor):
                    bg_color = model_bg

            if bg_color:
                painter.fillRect(option.rect, bg_color)

            # --- Fixed Line Number Column ---
            raw_index = index.data(Qt.UserRole + 1)
            digits = len(str(self.max_line_number))
            char_w = option.fontMetrics.horizontalAdvance('8')
            line_num_width = max(40, digits * char_w + 15)
            
            # The line number column rect should be shifted by scroll_x to stay on the left
            line_bg_rect = QRectF(option.rect.left() + scroll_x, option.rect.top(), line_num_width, option.rect.height())
            
            if raw_index is not None:
                line_num_str = str(raw_index + 1)
                
                # Draw Line Num Column Background
                base_col = option.palette.color(QPalette.Base)
                if base_col.lightness() > 128:
                    num_bg = QColor(240, 240, 240)
                    num_fg = QColor(128, 128, 128)
                else:
                    num_bg = QColor(40, 40, 40)
                    num_fg = QColor(100, 100, 100)
                
                painter.fillRect(line_bg_rect, num_bg)
                
                # Draw Line Num Text
                painter.save()
                painter.setPen(num_fg)
                painter.drawText(line_bg_rect.adjusted(0, 0, -5, 0), Qt.AlignRight, line_num_str)
                painter.restore()

            # 2. Text (Scrolls with the content)
            text = index.data(Qt.DisplayRole)
            if text:
                if state & QStyle.State_Selected:
                    painter.setPen(option.palette.highlightedText().color())
                else:
                    model_fg = index.data(Qt.ForegroundRole)
                    if model_fg and isinstance(model_fg, QColor):
                        painter.setPen(model_fg)
                    else:
                        painter.setPen(option.palette.text().color())

                # The text area remains relative to option.rect
                text_rect = option.rect.adjusted(line_num_width + 8, 0, -4, 0)

                # Set clipping to prevent text from overlapping the fixed line number column when scrolling
                painter.setClipRect(option.rect.adjusted(line_num_width + scroll_x, 0, 0, 0))

                should_highlight = False
                if self.search_query and self.search_query.strip():
                    if self.search_case_sensitive:
                        if self.search_query in text: should_highlight = True
                    else:
                        if self.search_query.lower() in text.lower(): should_highlight = True
                
                if should_highlight:
                    self._paint_highlighted_text(painter, text_rect, text, option)
                else:
                    painter.drawText(text_rect, Qt.AlignLeft, text)


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
        text = index.data(Qt.DisplayRole)
        if not text:
            return QSize(option.rect.width(), option.fontMetrics.height())
        
        # Calculate line number column width
        digits = len(str(self.max_line_number))
        char_w = option.fontMetrics.horizontalAdvance('8')
        line_num_width = max(40, digits * char_w + 15)
        
        # Total width = line number column + text width + margins
        text_width = option.fontMetrics.horizontalAdvance(text)
        return QSize(line_num_width + 8 + text_width + 20, option.fontMetrics.height())

class FilterDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        try:
            # 1. Draw base background from item data
            brush = index.data(Qt.BackgroundRole)
            bg_color = None
            if brush and hasattr(brush, 'color'):
                bg_color = brush.color()
            
            if bg_color and bg_color.isValid():
                painter.fillRect(option.rect, bg_color)
            
            # 2. Draw Hover/Selection Overlay
            # Use specific color or fall back to theme base color to determine lightness
            effective_bg = bg_color if (bg_color and bg_color.isValid()) else option.palette.color(QPalette.Base)
            is_dark_bg = effective_bg.lightness() < 128
            
            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, QColor(0, 122, 204, 80))
            elif option.state & QStyle.State_MouseOver:
                # If background is dark, make it lighter. If light, make it darker.
                overlay = QColor(255, 255, 255, 60) if is_dark_bg else QColor(0, 0, 0, 40)
                painter.fillRect(option.rect, overlay)




            
            # 3. Draw default content
            super().paint(painter, option, index)
        finally:
            painter.restore()



