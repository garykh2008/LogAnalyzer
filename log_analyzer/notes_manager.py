from PySide6.QtWidgets import (QDockWidget, QTreeWidget, QTreeWidgetItem, QHeaderView, 
                               QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QDialog, 
                               QTextEdit, QLabel, QMessageBox, QMenu, QToolButton, QStyledItemDelegate)
from PySide6.QtCore import Qt, Signal, QObject, QSize
from PySide6.QtGui import QColor, QAction, QFont, QFontInfo
from .utils import adjust_color_for_theme, set_windows_title_bar_color
from .resources import get_svg_icon
from .modern_dialog import ModernDialog
from .modern_messagebox import ModernMessageBox
import os
import re
import json

class NoteLineDelegate(QStyledItemDelegate):
    def __init__(self, bg_color, fg_color, border_color, parent=None):
        super().__init__(parent)
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.border_color = border_color

    def paint(self, painter, option, index):
        if index.column() == 0:
            painter.fillRect(option.rect, self.bg_color)
            
            # Draw borders for separation
            painter.setPen(self.border_color)
            r = option.rect
            # Right vertical border
            painter.drawLine(r.right(), r.top(), r.right(), r.bottom())
            # Bottom horizontal border
            painter.drawLine(r.left(), r.bottom(), r.right(), r.bottom())
            
            painter.setPen(self.fg_color)
            # Add small horizontal padding
            text_rect = option.rect.adjusted(5, 0, -5, 0)
            painter.drawText(text_rect, Qt.AlignCenter, str(index.data()))
        else:
            super().paint(painter, option, index)

class NoteDialog(ModernDialog):
    def __init__(self, parent=None, initial_text="", line_num=0):
        super().__init__(parent, title=f"Note for Line {line_num}", fixed_size=(400, 240))
        self.note_content = None

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.text_edit = QTextEdit()
        # Remove hardcoded font, will inherit from stylesheet
        self.text_edit.setPlainText(initial_text)
        layout.addWidget(self.text_edit)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 10, 0, 0)
        btn_save = QPushButton("Save")
        btn_save.setDefault(True)
        btn_save.clicked.connect(self.save)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        self.setContentLayout(layout)
        self.text_edit.setFocus()

    def save(self):
        self.note_content = self.text_edit.toPlainText().strip()
        self.accept()

class NotesManager(QObject):
    # Signals to notify MainWindow to refresh view (e.g. highlight lines)
    notes_updated = Signal()
    navigation_requested = Signal(int) # raw_index
    export_requested = Signal()
    message_requested = Signal(str, str) # message, type_str (optional)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.notes = {} # {(filepath, raw_index): content}
        self.current_log_path = None
        self.is_dark_mode = True
        self.dirty_files = set()
        self.loaded_files = set()
        
        self.setup_ui()

    def setup_ui(self):
        self.dock = QDockWidget("Notes", self.parent)
        self.dock.setObjectName("NotesDock")
        self.dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        
        # --- Custom Title Bar ---
        self.title_bar = QWidget()
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(10, 4, 4, 4)
        title_layout.setSpacing(4)
        
        self.title_label = QLabel("NOTES")
        font = QFont("Inter SemiBold")
        if not QFontInfo(font).exactMatch() and QFontInfo(font).family() != "Inter":
             font.setFamily("Segoe UI")
        font.setBold(True) # Fallback
        self.title_label.setFont(font)
        
        self.btn_save = QToolButton()
        self.btn_save.setToolTip("Save Notes (Ctrl+S)")
        self.btn_save.setFixedSize(26, 26)
        self.btn_save.clicked.connect(self.quick_save)
        
        self.btn_export = QToolButton()
        self.btn_export.setToolTip("Export Notes to Text...")
        self.btn_export.setFixedSize(26, 26)
        self.btn_export.clicked.connect(self.export_requested.emit)
        
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.btn_save)
        title_layout.addWidget(self.btn_export)
        
        self.dock.setTitleBarWidget(self.title_bar)

        # --- Content ---
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(2) # Line, Content
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(False) # We will manually color lines
        self.tree.setIndentation(0)
        
        # Column resizing
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setMinimumSectionSize(60)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)

        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.tree)

        self.dock.setWidget(container)
        # Dock addition is handled by the parent (MainWindow)
        self.dock.hide()

    def set_current_log_path(self, path):
        self.current_log_path = path
        self.refresh_list()

    def set_theme(self, is_dark):
        self.is_dark_mode = is_dark
        if self.dock.isFloating():
            set_windows_title_bar_color(self.dock.winId(), is_dark)
        
        # Get Palette and styles from ThemeManager if available
        theme_manager = getattr(self.parent, 'theme_manager', None)
        if theme_manager:
            p = theme_manager.palette
            icon_color = p['fg_color']
            header_style = theme_manager.get_dock_title_style()
            tree_style = theme_manager.get_dock_list_style(is_dark)
            line_bg = p['dock_content_bg']
            line_fg = p['log_gutter_fg']
            border_color = p['dock_border']
        else:
            # Fallback colors
            icon_color = "#d4d4d4" if is_dark else "#333333"
            header_bg = "#2d2d2d" if is_dark else "#e1e1e1"
            header_style = f"background-color: {header_bg};"
            content_bg = "#252526" if is_dark else "#f3f3f3"
            tree_style = f"QTreeWidget {{ background-color: {content_bg}; color: {icon_color}; border: none; }}"
            line_bg = content_bg
            line_fg = "#858585" if is_dark else "#237893"
            border_color = "#404040" if is_dark else "#e5e5e5"
        
        # Update Icons
        self.btn_save.setIcon(get_svg_icon("save", icon_color))
        self.btn_export.setIcon(get_svg_icon("external-link", icon_color))
        
        # Update UI Elements
        self.title_bar.setStyleSheet(header_style)
        self.tree.setStyleSheet(tree_style)
        
        # Set Delegate for Line Column
        self.tree.setItemDelegate(NoteLineDelegate(QColor(line_bg), QColor(line_fg), QColor(border_color), self.tree))
        
        # Re-populate list
        self.refresh_list()

    
    def has_unsaved_changes(self):
        return len(self.dirty_files) > 0

    def close_file(self, filepath):
        """Cleans up internal state when a file is closed."""
        if filepath in self.dirty_files:
            self.dirty_files.remove(filepath)
        if filepath in self.loaded_files:
            self.loaded_files.remove(filepath)

    def load_notes_for_file(self, log_filepath):
        """Automatically called when a log is loaded for the first time."""
        if not log_filepath: return
        
        if log_filepath in self.loaded_files:
            self.refresh_list()
            return

        self.loaded_files.add(log_filepath)

        base, _ = os.path.splitext(log_filepath)
        note_path = base + ".note"
        
        if os.path.exists(note_path):
            try:
                with open(note_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for str_idx, content in data.items():
                        try:
                            idx = int(str_idx)
                            self.notes[(log_filepath, idx)] = content
                        except ValueError: continue
                self.refresh_list()
                self.notes_updated.emit()
            except Exception as e:
                print(f"Error loading notes: {e}")
        else:
            # No note file, just refresh view
            self.refresh_list()
            self.notes_updated.emit()

    def quick_save(self):
        """Saves notes for the current active file only."""
        if not self.current_log_path: return
        self._save_file_notes(self.current_log_path)
        self.message_requested.emit(f"Notes saved for current file", "success")

    def save_all_notes(self):
        """Saves all unsaved notes for all loaded files."""
        if not self.dirty_files:
            return True
            
        # Create a copy since we might modify the set during iteration
        files_to_save = list(self.dirty_files)
        
        success = True
        for fp in files_to_save:
            if not self._save_file_notes(fp):
                success = False
        
        if success:
            self.message_requested.emit("All notes saved", "success")
        return success

    def _save_file_notes(self, log_filepath):
        """Internal helper to save notes for a specific filepath."""
        base, _ = os.path.splitext(log_filepath)
        note_path = base + ".note"
        
        data_to_save = {}
        for (fp, idx), content in self.notes.items():
            if fp == log_filepath:
                data_to_save[str(idx)] = content
        
        try:
            # If no notes for this file and .note exists, maybe delete it? 
            # Reference behavior usually keeps empty files or we can skip.
            if not data_to_save:
                if os.path.exists(note_path):
                    # For now, just save an empty dict or keep existing.
                    # Standard behavior: save empty list.
                    pass
                else: 
                    if log_filepath in self.dirty_files:
                        self.dirty_files.remove(log_filepath)
                    return True

            with open(note_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, sort_keys=True)
            
            if log_filepath in self.dirty_files:
                self.dirty_files.remove(log_filepath)
            return True
        except Exception as e:
            print(f"Error saving notes for {log_filepath}: {e}")
            return False

    def export_to_text(self, filepath, engine=None):
        if not self.current_log_path or not filepath: return

        file_notes = []
        for (fp, idx), content in self.notes.items():
            if fp == self.current_log_path:
                file_notes.append((idx, content))
        file_notes.sort(key=lambda x: x[0])

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                ts_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?|\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+|\b\d{1,2}:\d{2}:\d{2}\.\d+\s+(?:AM|PM)\b|\b\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\b)')
                
                for idx, content in file_notes:
                    ts = ""
                    if engine:
                        line = engine.get_line(idx)
                        if line:
                            match = ts_pattern.search(line)
                            if match: ts = match.group(1)
                    
                    clean_content = content.replace("\n", " ")
                    f.write(f"{idx + 1}\t{ts}\t{clean_content}\n")
            
            self.message_requested.emit(f"Exported to {os.path.basename(filepath)}", "success")
        except Exception as e:
            # We can emit an error signal or just use print for now, or assume parent is QWidget for MessageBox
            if self.parent:
                 ModernMessageBox.critical(self.parent, "Error", f"Export failed: {e}")
            else:
                 print(f"Export failed: {e}")

    def add_note(self, raw_index, timestamp, filepath):
        if not filepath and self.current_log_path:
             filepath = self.current_log_path
             
        key = (filepath, raw_index)
        current_text = self.notes.get(key, "")
        
        dialog = NoteDialog(self.parent, current_text, raw_index + 1)
        
        if dialog.exec():
            content = dialog.note_content
            if content:
                self.notes[key] = content
            else:
                if key in self.notes:
                    del self.notes[key]
            
            self.dirty_files.add(filepath)
            self.refresh_list()
            self.notes_updated.emit()

    def delete_note(self, raw_index, filepath):
        key = (filepath, raw_index)
        if key in self.notes:
            del self.notes[key]
            self.dirty_files.add(filepath)
            self.refresh_list()
            self.notes_updated.emit()

    def refresh_list(self):
        self.tree.clear()
        if not self.current_log_path: return

        file_notes = []
        for (fp, idx), content in self.notes.items():
            if fp == self.current_log_path:
                file_notes.append((idx, content))
        
        file_notes.sort(key=lambda x: x[0])

        ts_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?|\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+|\b\d{1,2}:\d{2}:\d{2}\.\d+\s+(?:AM|PM)\b|\b\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\b)')
        
        engine = getattr(self.parent, 'current_engine', None)

        for idx, content in file_notes:
            ts = ""
            if engine:
                line = engine.get_line(idx)
                if line:
                    match = ts_pattern.search(line)
                    if match: ts = match.group(1)

            item = QTreeWidgetItem(self.tree)
            item.setText(0, str(idx + 1))
            item.setText(1, content.replace("\n", " "))
            item.setData(0, Qt.UserRole, idx)
            
            if ts:
                item.setToolTip(0, ts)
                item.setToolTip(1, ts)

    def on_item_double_clicked(self, item, column):
        idx = item.data(0, Qt.UserRole)
        self.navigation_requested.emit(idx)

    def show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item: return
        
        idx = item.data(0, Qt.UserRole)
        menu = QMenu(self.tree)
        icon_color = "#d4d4d4" if self.is_dark_mode else "#333333"
        
        edit_action = QAction(get_svg_icon("edit", icon_color), "Edit Note", self.tree)
        edit_action.triggered.connect(lambda: self.add_note(idx, "", self.current_log_path))
        menu.addAction(edit_action)
        
        del_action = QAction(get_svg_icon("trash", icon_color), "Delete Note", self.tree)
        del_action.triggered.connect(lambda: self.delete_note(idx, self.current_log_path))
        menu.addAction(del_action)
        
        menu.exec_(self.tree.mapToGlobal(pos))

    def toggle_view(self):
        if self.dock.isHidden():
            self.dock.show()
        else:
            self.dock.hide()
