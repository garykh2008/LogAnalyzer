from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtGui import QPalette, QColor, QPainter, QFont
from PySide6.QtCore import QSize, QRectF, Qt, QRect, Signal, QEvent
from .resources import get_svg_icon


class LogListDelegate(QStyledItemDelegate):
    close_requested = Signal(str) # Emits filepath

    def __init__(self, parent=None):
        super().__init__(parent)
        self.close_btn_rects = {} # Map index to rect
        self.border_color = QColor("#3c3c3c")

    def set_theme_config(self, border_color):
        self.border_color = QColor(border_color)

    def paint(self, painter, option, index):
        painter.save()
        try:
            # Draw standard background and hover/selection
            state = option.state
            bg_color = None
            if state & QStyle.State_Selected:
                bg_color = option.palette.highlight().color()
                bg_color.setAlpha(80) # Semi-transparent selection
            elif state & QStyle.State_MouseOver:
                alpha = 30 if option.palette.base().color().lightness() < 128 else 20
                bg_color = QColor(255, 255, 255, alpha) if option.palette.base().color().lightness() < 128 else QColor(0, 0, 0, alpha)

            if bg_color:
                painter.fillRect(option.rect, bg_color)

            # Define Close Button Area (Far Left, 24px wide)
            close_rect = QRect(option.rect.left(), option.rect.top(), 24, option.rect.height())
            self.close_btn_rects[index.row()] = close_rect

            # Draw SVG 'X' only on hover
            if state & QStyle.State_MouseOver:
                painter.setRenderHint(QPainter.Antialiasing)

                # Get SVG icon with current text color
                icon_color = option.palette.text().color().name()
                icon = get_svg_icon("x-close", icon_color)

                # Draw icon centered in close_rect
                icon_size = 14
                target_rect = QRect(
                    close_rect.left() + (close_rect.width() - icon_size) // 2,
                    close_rect.top() + (close_rect.height() - icon_size) // 2,
                    icon_size, icon_size
                )
                icon.paint(painter, target_rect)

            # Draw Filename (offset by the close button space)
            text_rect = option.rect.adjusted(24, 0, 0, 0)
            text = index.data(Qt.DisplayRole)
            painter.setPen(option.palette.text().color())
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)

            # Draw Bottom Border
            painter.setPen(self.border_color)
            painter.drawLine(option.rect.bottomLeft(), option.rect.bottomRight())

        finally:
            painter.restore()

    def editorEvent(self, event, model, option, index):
        # Handle mouse click on the 'X' button
        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton:
                pos = event.pos()
                if index.row() in self.close_btn_rects:
                    if self.close_btn_rects[index.row()].contains(pos):
                        filepath = index.data(Qt.UserRole)
                        self.close_requested.emit(filepath)
                        return True
        return super().editorEvent(event, model, option, index)

    def sizeHint(self, option, index):
        s = super().sizeHint(option, index)
        return QSize(s.width() + 24, max(28, s.height()))


class LogDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hover_color = QColor("#2a2d2e")
        self.search_query = None
        self.search_case_sensitive = False
        self.search_match_color = QColor("#653306")
        self.search_match_text_color = QColor("#ffffff")
        self.max_line_number = 1000

        # Theme config
        self.gutter_bg = None
        self.gutter_fg = QColor(100, 100, 100)
        self.border_color = QColor("#3c3c3c")
        self.show_line_numbers = True
        self.line_spacing = 0

    def set_line_spacing(self, spacing):
        self.line_spacing = spacing

    def set_theme_config(self, gutter_bg, gutter_fg, border_color):
        if gutter_bg: self.gutter_bg = QColor(gutter_bg)
        if gutter_fg: self.gutter_fg = QColor(gutter_fg)
        if border_color: self.border_color = QColor(border_color)

    def set_show_line_numbers(self, show):
        self.show_line_numbers = show

    def set_hover_color(self, color):
        self.hover_color = QColor(color)

    def set_max_line_number(self, count):
        self.max_line_number = count

    def set_search_query(self, query, case_sensitive=False):
        self.search_query = query
        self.search_case_sensitive = case_sensitive

    def paint(self, painter, option, index):
        painter.save()
        painter.setFont(option.font) # Ensure custom font is used for drawing
        try:
            # Get horizontal scroll offset to keep line numbers fixed
            scroll_x = option.widget.horizontalScrollBar().value() if option.widget else 0

            # 1. Background
            state = option.state

            # First, draw model-provided background (if any)
            model_bg = index.data(Qt.BackgroundRole)
            if model_bg and isinstance(model_bg, QColor):
                painter.fillRect(option.rect, model_bg)

            if state & QStyle.State_Selected:
                painter.fillRect(option.rect, option.palette.highlight())
            elif state & QStyle.State_MouseOver:
                 # Standard hover overlay (blended over the current background)
                 painter.fillRect(option.rect, self.hover_color)

            # --- Fixed Line Number Column ---
            raw_index = index.data(Qt.UserRole + 1)

            line_num_width = 0
            if self.show_line_numbers:
                digits = len(str(self.max_line_number))
                char_w = option.fontMetrics.horizontalAdvance('8')
                # Increase padding: Left (10px) + digits*char_w + Right (10px)
                line_num_width = max(45, digits * char_w + 20)

            # The line number column rect should be shifted by scroll_x to stay on the left
            line_bg_rect = QRectF(option.rect.left() + scroll_x, option.rect.top(), line_num_width, option.rect.height())

            if self.show_line_numbers and raw_index is not None:
                line_num_str = str(raw_index + 1)

                # Draw Line Num Column Background
                # If gutter_bg is None, use base (content) color for blending
                fill_color = self.gutter_bg if self.gutter_bg else option.palette.color(QPalette.Base)
                painter.fillRect(line_bg_rect, fill_color)

                # Draw Right Border
                painter.setPen(self.border_color)
                painter.drawLine(line_bg_rect.topRight(), line_bg_rect.bottomRight())

                # Draw Line Num Text (Right Aligned with padding)
                painter.save()
                painter.setPen(self.gutter_fg)
                # Right padding 12px
                painter.drawText(line_bg_rect.adjusted(0, 0, -12, 0), Qt.AlignRight | Qt.AlignVCenter, line_num_str)
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
                    # Calculate vertical center for standard text
                    fm = option.fontMetrics
                    y_center = text_rect.top() + (text_rect.height() - fm.height()) // 2 + fm.ascent()
                    painter.drawText(text_rect.left(), y_center, text)


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

        # Center text vertically
        fm = option.fontMetrics
        y = rect.top() + (rect.height() - fm.height()) // 2 + fm.ascent()

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
        line_num_width = 0
        if self.show_line_numbers:
            digits = len(str(self.max_line_number))
            char_w = option.fontMetrics.horizontalAdvance('8')
            line_num_width = max(45, digits * char_w + 20)

        # Total width = line number column + text width + margins
        text_width = option.fontMetrics.horizontalAdvance(text)
        return QSize(line_num_width + 8 + text_width + 20, option.fontMetrics.height() + self.line_spacing)


class FilterDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.border_color = QColor("#3c3c3c")

    def set_theme_config(self, border_color):
        self.border_color = QColor(border_color)

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
            has_custom_bg = bg_color and bg_color.isValid()

            if option.state & QStyle.State_Selected:
                # Tint the background with blue, but use lower alpha for custom colors
                alpha = 40 if has_custom_bg else 80
                painter.fillRect(option.rect, QColor(0, 122, 204, alpha))
            elif option.state & QStyle.State_MouseOver:
                # Standardized brightness overlay
                alpha = 30 if is_dark_bg else 20
                overlay = QColor(255, 255, 255, alpha) if is_dark_bg else QColor(0, 0, 0, alpha)
                painter.fillRect(option.rect, overlay)

            # 3. Draw default content
        finally:
            painter.restore()


class FontPreviewDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        
        # Draw background (standard style)
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.fillRect(option.rect, option.palette.base())
            painter.setPen(option.palette.text().color())

        # Get font name
        font_family = index.data(Qt.DisplayRole)
        if font_family:
            # Use the specific font for preview
            preview_font = QFont(font_family, 10)
            painter.setFont(preview_font)
            
            # Draw text
            text_rect = option.rect.adjusted(5, 0, -5, 0)
            painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, font_family)
            
        painter.restore()

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 28)

