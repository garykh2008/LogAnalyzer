from PySide6.QtWidgets import QStyledItemDelegate, QStyle
from PySide6.QtGui import QTextDocument, QAbstractTextDocumentLayout, QPalette
from PySide6.QtCore import QSize, QRectF, Qt

class LogDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)

    def paint(self, painter, option, index):
        painter.save()

        # 1. Background (Selection & Hover)
        # We manually handle selection, but rely on style for base.
        # However, custom painting usually overrides stylesheet background unless we use style().drawPrimitive.
        # Simpler approach: Check state and fill rect.

        # PySide6 Enum Access: QStyle.State is the enum type

        bg_color = None
        state = option.state

        # Check Selection
        if state & QStyle.State_Selected:
            bg_color = option.palette.highlight()
        elif state & QStyle.State_MouseOver:
             # Match the hover color from QSS
             # We can't easily get the specific QSS color here without parsing or hardcoding.
             # Hardcoding to match ui.py #2a2d2e is safest for this custom delegate approach.
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

            # Vertically center
            painter.drawText(rect, Qt.AlignLeft | Qt.AlignVCenter, elided_text)

        painter.restore()

    def sizeHint(self, option, index):
        # We enforce a fixed size in the View via setUniformItemSizes,
        # but the delegate should nominally agree.
        return QSize(option.rect.width(), 18)
