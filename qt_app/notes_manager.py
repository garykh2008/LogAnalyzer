from PySide6.QtWidgets import (QDockWidget, QTreeWidget, QTreeWidgetItem, QHeaderView, 
                               QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QDialog, 
                               QTextEdit, QLabel, QMessageBox, QMenu)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QColor, QAction
from .utils import adjust_color_for_theme, set_windows_title_bar_color
import os
import re

class NoteDialog(QDialog):
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
        
        self.setup_ui()

    def setup_ui(self):
        self.dock = QDockWidget("Notes", self.main_window)
        self.dock.setObjectName("NotesDock")
        self.dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Line", "Timestamp", "Content"])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        
        # Column resizing
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents) # Line
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents) # Timestamp
        self.tree.header().setSectionResizeMode(2, QHeaderView.Stretch) # Content

        self.tree.itemDoubleClicked.connect(self.on_item_double_clicked)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        self.dock.setWidget(self.tree)
        self.main_window.addDockWidget(Qt.RightDockWidgetArea, self.dock)
        self.dock.hide() # Hidden by default

    def set_theme(self, is_dark):
        self.is_dark_mode = is_dark
        # Update dock title bar color if floating
        if self.dock.isFloating():
            set_windows_title_bar_color(self.dock.winId(), is_dark)
        
        # Update Tree colors if needed (alternating colors handled by style sheet usually)
        # We can refresh the list to apply specific item colors if we implement them
        
    def load_notes_for_file(self, filepath):
        # In a real persistence scenario, we would load from a sidecar file here
        # For now, we just refresh the view based on in-memory notes
        self.refresh_list()

    def add_note(self, raw_index, timestamp, filepath):
        key = (filepath, raw_index)
        current_text = self.notes.get(key, "")
        
        dialog = NoteDialog(self.main_window, current_text, raw_index + 1)
        # Apply theme to dialog
        if self.is_dark_mode:
            dialog.setStyleSheet("QDialog { background-color: #252526; color: #cccccc; } QTextEdit { background-color: #3c3c3c; color: #cccccc; } QPushButton { background-color: #3c3c3c; color: #cccccc; }")
        
        if dialog.exec():
            content = dialog.note_content
            if content:
                self.notes[key] = content
            else:
                if key in self.notes:
                    del self.notes[key]
            
            self.refresh_list()
            self.notes_updated.emit()

    def delete_note(self, raw_index, filepath):
        key = (filepath, raw_index)
        if key in self.notes:
            del self.notes[key]
            self.refresh_list()
            self.notes_updated.emit()

    def refresh_list(self):
        self.tree.clear()
        current_fp = self.main_window.current_log_path
        if not current_fp: return

        # Filter notes for current file
        file_notes = []
        for (fp, idx), content in self.notes.items():
            if fp == current_fp:
                file_notes.append((idx, content))
        
        # Sort by index
        file_notes.sort(key=lambda x: x[0])

        for idx, content in file_notes:
            # Try to get timestamp from engine if possible, otherwise placeholder
            ts = "" 
            # We need access to engine to get line content for timestamp.
            # Assuming main_window has access.
            if self.main_window.current_engine:
                line = self.main_window.current_engine.get_line(idx)
                # Simple regex for timestamp (reuse pattern from loganalyzer if possible)
                # For now, just show line
                pass

            item = QTreeWidgetItem(self.tree)
            item.setText(0, str(idx + 1))
            item.setText(1, ts) # TODO: extracting timestamp
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
