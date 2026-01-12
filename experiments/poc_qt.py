from PySide6.QtWidgets import QWidget, QVBoxLayout, QListView, QLabel
from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex
from PySide6.QtGui import QColor, QBrush

class DummyLogEngine:
    def __init__(self, count=1000000):
        self._count = count

    def line_count(self):
        return self._count

    def get_line(self, index):
        if 0 <= index < self._count:
            return f"Log Line {index + 1}: This is a sample log line to demonstrate performance. [TIMESTAMP]"
        return None

class LogModel(QAbstractListModel):
    def __init__(self, engine):
        super().__init__()
        self.engine = engine

    def rowCount(self, parent=QModelIndex()):
        return self.engine.line_count()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        if role == Qt.DisplayRole:
            return self.engine.get_line(index.row())

        return None

class ModernLogViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Modern PySide6 Log Viewer (PoC)")
        self.resize(1000, 600)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header
        self.header = QLabel("  Log Viewer - 1,000,000 Lines (Virtual Scrolling)")
        self.header.setStyleSheet("background-color: #252526; color: #cccccc; padding: 10px; font-weight: bold;")
        layout.addWidget(self.header)

        # List View
        self.list_view = QListView()
        self.model = LogModel(DummyLogEngine())
        self.list_view.setModel(self.model)

        # Performance Tweaks
        self.list_view.setUniformItemSizes(True)  # Crucial for huge lists
        self.list_view.setLayoutMode(QListView.Batched)
        self.list_view.setBatchSize(100)

        layout.addWidget(self.list_view)

        # Styling
        self.apply_dark_theme()

    def apply_dark_theme(self):
        style = """
        QListView {
            background-color: #1e1e1e;
            color: #d4d4d4;
            border: none;
            font-family: Consolas, monospace;
            font-size: 13px;
        }
        QListView::item {
            height: 22px;
            padding-left: 5px;
        }
        QListView::item:selected {
            background-color: #264f78;
            color: #ffffff;
        }
        QListView::item:hover {
            background-color: #2a2d2e;
        }
        QScrollBar:vertical {
            border: none;
            background: #1e1e1e;
            width: 14px;
            margin: 0px 0px 0px 0px;
        }
        QScrollBar::handle:vertical {
            background: #424242;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: #4f4f4f;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            background: none;
            height: 0px;
        }
        """
        self.setStyleSheet(style)

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    window = ModernLogViewer()
    window.show()
    sys.exit(app.exec())
