from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex
from PySide6.QtGui import QColor

class LogModel(QAbstractListModel):
    def __init__(self, engine=None):
        super().__init__()
        self.engine = engine
        self.filtered_indices = None # None means show all
        self.tag_codes = None # List of ints
        self.filter_palette = {} # {code: (fg, bg)}

    def set_engine(self, engine):
        self.beginResetModel()
        self.engine = engine
        self.filtered_indices = None
        self.tag_codes = None
        self.filter_palette = {}
        self.endResetModel()

    def set_filtered_indices(self, indices):
        self.beginResetModel()
        self.filtered_indices = indices
        self.endResetModel()

    def set_filter_data(self, tag_codes, palette):
        self.tag_codes = tag_codes
        self.filter_palette = palette
        # Colors might change even if indices don't, but full reset is safest/easiest sync
        # If we want to optimize, we could emit dataChanged, but layoutChanged is enough
        self.layoutChanged.emit()

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

        # Color Roles
        if role == Qt.ForegroundRole or role == Qt.BackgroundRole:
            if self.tag_codes and raw_index < len(self.tag_codes):
                code = self.tag_codes[raw_index]
                if code in self.filter_palette:
                    fg, bg = self.filter_palette[code]
                    if role == Qt.ForegroundRole and fg:
                        return QColor(fg)
                    if role == Qt.BackgroundRole and bg:
                        return QColor(bg)

        return None
