from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtGui import QTextDocument, QAbstractTextDocumentLayout, QPalette, QColor
from PySide6.QtCore import QSize, QRectF, Qt

class LogDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

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
                 # Match the hover color from QSS
                 bg_color = QColor("#2a2d2e")

            if bg_color:
                painter.fillRect(option.rect, bg_color)

            # 2. Text
            text = index.data(Qt.DisplayRole)
            if text:
                # Setup Pen
                if state & QStyle.State_Selected:
                    painter.setPen(option.palette.highlightedText().color())
                else:
                    painter.setPen(option.palette.text().color())

                # Calculate rect with padding
                # Using 4px left/right padding
                rect = option.rect.adjusted(4, 0, -4, 0)

                # Use ElideNone to show full text if possible, or ElideRight if preferred.
                # Log viewers usually prioritize seeing start of line, but scrolling handles horizontal.

                font_metrics = option.fontMetrics
                elided_text = font_metrics.elidedText(text, Qt.ElideNone, rect.width())

                # Vertically center
                painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, elided_text)

        finally:
            painter.restore()

    def sizeHint(self, option, index):
        # Use lineSpacing() which includes proper vertical leading.
        # Add 8px padding (4px top, 4px bottom) to prevent any overlap/clipping.
        height = option.fontMetrics.lineSpacing() + 8
        return QSize(option.rect.width(), height)
