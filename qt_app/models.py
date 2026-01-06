from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex

class LogModel(QAbstractListModel):
    def __init__(self, engine=None):
        super().__init__()
        self.engine = engine
        self.filtered_indices = None # None means show all, [] means show nothing

    def set_engine(self, engine):
        self.beginResetModel()
        self.engine = engine
        self.filtered_indices = None
        self.endResetModel()

    def set_filtered_indices(self, indices):
        self.beginResetModel()
        self.filtered_indices = indices
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        if not self.engine:
            return 0
        if self.filtered_indices is not None:
            return len(self.filtered_indices)
        return self.engine.line_count()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not self.engine:
            return None

        row = index.row()

        # Map view row to raw engine index
        raw_index = row
        if self.filtered_indices is not None:
            if 0 <= row < len(self.filtered_indices):
                raw_index = self.filtered_indices[row]
            else:
                return None

        if role == Qt.DisplayRole:
            return self.engine.get_line(raw_index)

        # We could handle Foreground/Background roles here if we want row-specific coloring based on filters
        # But for high performance, we might let the Delegate handle it using a shared filter map.

        return None
