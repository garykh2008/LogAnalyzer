from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex

class LogModel(QAbstractListModel):
    def __init__(self, engine=None):
        super().__init__()
        self.engine = engine

    def set_engine(self, engine):
        self.beginResetModel()
        self.engine = engine
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        if not self.engine:
            return 0
        return self.engine.line_count()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not self.engine:
            return None

        if role == Qt.DisplayRole:
            # Format: "LineNum  Content"
            # We could do line numbers in the view (row delegate) for better perf,
            # but for simplicity, let's return just content here.
            return self.engine.get_line(index.row())

        return None
