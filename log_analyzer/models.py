from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex
from PySide6.QtGui import QColor

class LogModel(QAbstractListModel):
    def __init__(self, engine=None):
        super().__init__()
        self.engine = engine
        self.filtered_indices = None # None means show all
        self.tag_codes = None # List of ints
        self.filter_palette = {} # {code: (fg, bg)}
        self.notes = {} # Reference to main window notes
        self.current_filepath = None
        self.note_bg_color = QColor("#3a3d41")
        self._total_line_count = 0
        
        # Virtual Viewport State
        self.viewport_start = 0
        self.viewport_size = 200 # Default buffer

    def set_engine(self, engine, filepath=None):
        self.beginResetModel()
        self.engine = engine
        self.current_filepath = filepath
        self.filtered_indices = None
        self.tag_codes = None
        self.filter_palette = {}
        self._total_line_count = self.engine.line_count() if self.engine else 0
        self.viewport_start = 0
        self.endResetModel()

    def set_notes_ref(self, notes_dict):
        self.notes = notes_dict

    def set_theme_mode(self, is_dark):
        self.note_bg_color = QColor("#3a3d41") if is_dark else QColor("#fffbdd")
        self.layoutChanged.emit()

    def set_viewport(self, start, size):
        # Allow size to be slightly larger than visible to avoid flicker
        if self.viewport_start == start and self.viewport_size == size:
            return
        
        self.layoutAboutToBeChanged.emit()
        self.viewport_start = start
        self.viewport_size = size
        self.layoutChanged.emit()

    def set_filtered_indices(self, indices):
        self.beginResetModel()
        self.filtered_indices = indices
        self.viewport_start = 0
        self.endResetModel()

    def set_filter_data(self, tag_codes, palette):
        self.tag_codes = tag_codes
        self.filter_palette = palette
        # Colors might change even if indices don't, but full reset is safest/easiest sync
        # If we want to optimize, we could emit dataChanged, but layoutChanged is enough
        self.layoutChanged.emit()

    def update_filter_result(self, tag_codes, palette, filtered_indices):
        """Atomic update of all filter-related data to trigger only one model reset."""
        self.beginResetModel()
        self.tag_codes = tag_codes
        self.filter_palette = palette
        self.filtered_indices = filtered_indices
        self.viewport_start = 0
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        if not self.engine:
            return 0
        
        total = len(self.filtered_indices) if self.filtered_indices is not None else self._total_line_count
        
        # Virtual count: We only tell Qt we have 'viewport_size' rows (or fewer if near end)
        remaining = total - self.viewport_start
        if remaining < 0: remaining = 0
        return min(self.viewport_size, remaining)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not self.engine:
            return None

        # Map visual row (0..viewport_size) to absolute row
        row_in_viewport = index.row()
        real_row = self.viewport_start + row_in_viewport
        
        # Safety check
        total = len(self.filtered_indices) if self.filtered_indices is not None else self._total_line_count
        if real_row >= total:
            return None

        # Map absolute view row to raw engine index (for filtering)
        raw_index = real_row
        if self.filtered_indices is not None:
            raw_index = self.filtered_indices[real_row]

        if role == Qt.UserRole + 1:
            return raw_index

        if role == Qt.DisplayRole:
            return self.engine.get_line(raw_index)

        # Color Roles
        if role == Qt.ForegroundRole or role == Qt.BackgroundRole:
            # 1. Note Highlight (Background only)
            if role == Qt.BackgroundRole and self.current_filepath:
                if (self.current_filepath, raw_index) in self.notes:
                    return self.note_bg_color

            if self.tag_codes and raw_index < len(self.tag_codes):
                code = self.tag_codes[raw_index]
                if code in self.filter_palette:
                    fg, bg = self.filter_palette[code]
                    if role == Qt.ForegroundRole and fg:
                        return QColor(fg)
                    if role == Qt.BackgroundRole and bg:
                        return QColor(bg)

        return None
