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

                # Simple drawText is fastest.
                # QRect adjustment for padding
                rect = option.rect.adjusted(4, 0, -4, 0)

                font_metrics = option.fontMetrics
                elided_text = font_metrics.elidedText(text, Qt.ElideNone, rect.width())

                # Draw text aligned left (User feedback: remove VCenter to fix layout)
                painter.drawText(rect, Qt.AlignLeft, elided_text)

        finally:
            painter.restore()

    def sizeHint(self, option, index):
        # User feedback: Remove extra padding, rely on standard height/lineSpacing
        height = option.fontMetrics.height()
        return QSize(option.rect.width(), height)
