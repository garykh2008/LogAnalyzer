from PySide6.QtWidgets import (QDockWidget, QTreeWidget, QTreeWidgetItem, QHeaderView, 
                               QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QDialog, 
                               QTextEdit, QLabel, QMessageBox, QMenu)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QColor, QAction
from .utils import adjust_color_for_theme, set_windows_title_bar_color
import os
import re
import json

class NoteDialog(QDialog):
    # ... [Keep NoteDialog as is] ...
    def __init__(self, parent=None, initial_text="", line_num=0):
        super().__init__(parent)
        self.setWindowTitle(f"Note for Line {line_num}")
        self.resize(400, 200)
        self.note_content = None

        layout = QVBoxLayout(self)
        
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(initial_text)
        self.text_edit.setFontPointSize(11)
        layout.addWidget(self.text_edit)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_save)
        btn_layout.addWidget(btn_cancel)
        layout.addLayout(btn_layout)
        
        self.text_edit.setFocus()

    def save(self):
        self.note_content = self.text_edit.toPlainText().strip()
        self.accept()

class NotesManager(QObject):
    # Signals to notify MainWindow to refresh view (e.g. highlight lines)
    notes_updated = Signal()
    navigation_requested = Signal(int) # raw_index

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.notes = {} # {(filepath, raw_index): content}
        self.is_dark_mode = True
        self.notes_dirty = False
        
        self.setup_ui()

    def setup_ui(self):
        self.dock = QDockWidget("Notes", self.main_window)
        self.dock.setObjectName("NotesDock")
        self.dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Line", "Timestamp", "Content"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        
        # Column resizing
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tree.header().setSectionResizeMode(2, QHeaderView.Stretch)

        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.tree)

        # Bottom Bar for Actions
        btn_bar = QWidget()
        btn_layout = QHBoxLayout(btn_bar)
        btn_layout.setContentsMargins(5, 5, 5, 5)
        
        self.btn_save = QPushButton("Save Notes")
        self.btn_save.clicked.connect(self.quick_save)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_save)
        
        layout.addWidget(btn_bar)

        self.dock.setWidget(container)
        self.main_window.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.hide()

    def set_theme(self, is_dark):
        self.is_dark_mode = is_dark
        if self.dock.isFloating():
            set_windows_title_bar_color(self.dock.winId(), is_dark)
        # Force a style refresh on internal widgets
        self.tree.viewport().update()

    
    def has_unsaved_changes(self):
        return self.notes_dirty

    def load_notes_for_file(self, log_filepath):
        """Automatically called when a log is loaded."""
        if not log_filepath: return
        
        # Reset dirty flag on load
        self.notes_dirty = False
        
        base, _ = os.path.splitext(log_filepath)
        note_path = base + ".note"
        
        # Clear existing view
        self.notes.clear() # Clear memory for single-file mode logic
        
        if os.path.exists(note_path):
            try:
                with open(note_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Note file format: {"index": "content"}
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
            # No note file, clear view
            self.refresh_list()
            self.notes_updated.emit()

    def quick_save(self):
        log_filepath = self.main_window.current_log_path
        if not log_filepath: return
        
        base, _ = os.path.splitext(log_filepath)
        note_path = base + ".note"
        
        # Filter notes for this file
        data_to_save = {}
        for (fp, idx), content in self.notes.items():
            if fp == log_filepath:
                data_to_save[str(idx)] = content
        
        try:
            with open(note_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=4, sort_keys=True)
            self.notes_dirty = False
            self.main_window.toast.show_message(f"Notes saved to {os.path.basename(note_path)}")   
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Could not save notes: {e}")

    def export_to_text(self, filepath):
        current_fp = self.main_window.current_log_path
        if not current_fp or not filepath: return

        file_notes = []
        for (fp, idx), content in self.notes.items():
            if fp == current_fp:
                file_notes.append((idx, content))
        file_notes.sort(key=lambda x: x[0])

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                ts_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?|\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+|\b\d{1,2}:\d{2}:\d{2}\.\d+\s+(?:AM|PM)\b|\b\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\b)')
                
                for idx, content in file_notes:
                    ts = ""
                    if self.main_window.current_engine:
                        line = self.main_window.current_engine.get_line(idx)
                        if line:
                            match = ts_pattern.search(line)
                            if match: ts = match.group(1)
                    
                    clean_content = content.replace("\n", " ")
                    f.write(f"{idx + 1}\t{ts}\t{clean_content}\n")
            
            self.main_window.toast.show_message(f"Exported to {os.path.basename(filepath)}")
        except Exception as e:
            QMessageBox.critical(self.main_window, "Error", f"Export failed: {e}")

    def add_note(self, raw_index, timestamp, filepath):
        key = (filepath, raw_index)
        current_text = self.notes.get(key, "")
        
        dialog = NoteDialog(self.main_window, current_text, raw_index + 1)
        # Apply title bar theme
        set_windows_title_bar_color(dialog.winId(), self.is_dark_mode)
        
        if dialog.exec():
            content = dialog.note_content
            if content:
                self.notes[key] = content
            else:
                if key in self.notes:
                    del self.notes[key]
            
            self.notes_dirty = True
            self.refresh_list()
            self.notes_updated.emit()

    def delete_note(self, raw_index, filepath):
        key = (filepath, raw_index)
        if key in self.notes:
            del self.notes[key]
            self.notes_dirty = True
            self.refresh_list()
            self.notes_updated.emit()

    def refresh_list(self):
        self.tree.clear()
        current_fp = self.main_window.current_log_path
        if not current_fp: return

        file_notes = []
        for (fp, idx), content in self.notes.items():
            if fp == current_fp:
                file_notes.append((idx, content))
        
        file_notes.sort(key=lambda x: x[0])

        ts_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?|\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+|\b\d{1,2}:\d{2}:\d{2}\.\d+\s+(?:AM|PM)\b|\b\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\b)')

        for idx, content in file_notes:
            ts = ""
            if self.main_window.current_engine:
                line = self.main_window.current_engine.get_line(idx)
                if line:
                    match = ts_pattern.search(line)
                    if match: ts = match.group(1)

            item = QTreeWidgetItem(self.tree)
            item.setText(0, str(idx + 1))
            item.setText(1, ts)
            item.setText(2, content.replace("\n", " "))
            item.setData(0, Qt.UserRole, idx)

    def on_item_double_clicked(self, item, column):
        idx = item.data(0, Qt.UserRole)
        self.navigation_requested.emit(idx)

    def show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item: return
        
        idx = item.data(0, Qt.UserRole)
        menu = QMenu(self.tree)
        
        edit_action = QAction("Edit Note", self.tree)
        edit_action.triggered.connect(lambda: self.add_note(idx, "", self.main_window.current_log_path))
        menu.addAction(edit_action)
        
        del_action = QAction("Delete Note", self.tree)
        del_action.triggered.connect(lambda: self.delete_note(idx, self.main_window.current_log_path))
        menu.addAction(del_action)
        
        menu.exec_(self.tree.mapToGlobal(pos))

    def toggle_view(self):
        if self.dock.isHidden():
            self.dock.show()
        else:
            self.dock.hide()
