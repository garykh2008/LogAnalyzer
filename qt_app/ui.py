from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QListView,
                               QLabel, QFileDialog, QMenuBar, QMenu, QStatusBar, QAbstractItemView, QApplication,
                               QHBoxLayout, QLineEdit, QToolButton, QComboBox, QSizePolicy)
from PySide6.QtGui import QAction, QFont, QPalette, QColor, QKeySequence, QCursor, QIcon
from PySide6.QtCore import Qt, QSettings, QTimer, Slot, QModelIndex
from .models import LogModel
from .engine_wrapper import get_engine
from .toast import Toast
from .delegates import LogDelegate
import os
import time
import sys
import ctypes
import bisect

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Log Analyzer (PySide6)")
        self.resize(1200, 800)

        # Settings
        self.settings = QSettings("LogAnalyzer", "QtApp")
        # Load theme preference (default to True/Dark)
        self.is_dark_mode = self.settings.value("dark_mode", True, type=bool)
        self.last_status_message = "Ready"

        # Search State
        self.current_engine = None
        self.search_results = []
        self.current_match_index = -1
        self.search_history = []

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Search Bar (Hidden by default) ---
        self.search_widget = QWidget()
        self.search_layout = QHBoxLayout(self.search_widget)
        self.search_layout.setContentsMargins(5, 5, 5, 5)
        self.search_layout.setSpacing(5)

        self.search_input = QComboBox()
        self.search_input.setEditable(True)
        self.search_input.setPlaceholderText("Find...")
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_input.setInsertPolicy(QComboBox.InsertAtTop)
        # Handle Enter key in combo box line edit
        self.search_input.lineEdit().returnPressed.connect(self.find_next)

        self.btn_prev = QToolButton()
        self.btn_prev.setText("<")
        self.btn_prev.setToolTip("Previous (F2)")
        self.btn_prev.clicked.connect(self.find_previous)

        self.btn_next = QToolButton()
        self.btn_next.setText(">")
        self.btn_next.setToolTip("Next (F3)")
        self.btn_next.clicked.connect(self.find_next)

        self.btn_close_search = QToolButton()
        self.btn_close_search.setText("X")
        self.btn_close_search.setToolTip("Close (Esc)")
        self.btn_close_search.clicked.connect(self.hide_search_bar)

        self.search_info_label = QLabel("")
        self.search_info_label.setFixedWidth(120)
        self.search_info_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.search_layout.addWidget(QLabel("Find:"))
        self.search_layout.addWidget(self.search_input)
        self.search_layout.addWidget(self.btn_prev)
        self.search_layout.addWidget(self.btn_next)
        self.search_layout.addWidget(self.search_info_label)
        self.search_layout.addWidget(self.btn_close_search)

        layout.addWidget(self.search_widget)
        self.search_widget.hide()

        # Log List View
        self.list_view = QListView()
        self.model = LogModel()
        self.list_view.setModel(self.model)

        # Set Delegate
        self.delegate = LogDelegate(self.list_view)
        self.list_view.setItemDelegate(self.delegate)

        # 1. Multi-selection
        self.list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self.show_context_menu)

        # Performance Settings
        self.list_view.setUniformItemSizes(True)
        self.list_view.setLayoutMode(QListView.Batched)
        self.list_view.setBatchSize(100)

        # Font
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.list_view.setFont(font)

        layout.addWidget(self.list_view)

        # Status Bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Persistent Status Label
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_bar.addWidget(self.status_label, 1)

        # Toast notification
        self.toast = Toast(self)

        # Menu
        self._create_menu()

        # Load History
        self._load_search_history()

        # Styling
        self.apply_theme()

    def _create_menu(self):
        menu_bar = self.menuBar()

        # File Menu
        file_menu = menu_bar.addMenu("&File")

        open_action = QAction("&Open Log...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # View Menu
        view_menu = menu_bar.addMenu("&View")

        # Theme Toggle
        toggle_theme_action = QAction("Toggle Dark/Light Mode", self)
        toggle_theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(toggle_theme_action)

        # Find Action
        find_action = QAction("&Find...", self)
        find_action.setShortcut(QKeySequence.Find) # Ctrl+F
        find_action.triggered.connect(self.show_search_bar)
        self.addAction(find_action)
        view_menu.addAction(find_action)

        # Find Next/Prev Global Shortcuts
        next_action = QAction("Find Next", self)
        next_action.setShortcut("F3")
        next_action.triggered.connect(self.find_next)
        self.addAction(next_action)

        prev_action = QAction("Find Previous", self)
        prev_action.setShortcut("F2")
        prev_action.triggered.connect(self.find_previous)
        self.addAction(prev_action)

        # Clear Search Shortcut (Esc)
        # Note: Esc usually handled by event filter or override if specific widget has focus
        escape_action = QAction("Clear Search", self)
        escape_action.setShortcut("Esc")
        escape_action.triggered.connect(self.hide_search_bar)
        self.addAction(escape_action)

        # Copy Action (Global shortcut)
        copy_action = QAction("&Copy", self)
        copy_action.setShortcut(QKeySequence.Copy) # Ctrl+C
        copy_action.triggered.connect(self.copy_selection)

        # Add to window AND list_view to ensure it catches focus
        self.addAction(copy_action)
        self.list_view.addAction(copy_action)

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(copy_action)

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.settings.setValue("dark_mode", self.is_dark_mode)
        self.apply_theme()

    def update_status_bar(self, message):
        self.last_status_message = message
        self.status_label.setText(message)

    def _set_windows_title_bar_color(self, is_dark):
        if sys.platform != "win32": return
        try:
            hwnd = int(self.winId())
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(1 if is_dark else 0)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value)
            )
        except Exception: pass

    def apply_theme(self):
        if self.is_dark_mode:
            bg_color = "#1e1e1e"
            fg_color = "#d4d4d4"
            selection_bg = "#264f78"
            selection_fg = "#ffffff"
            hover_bg = "#2a2d2e"
            scrollbar_bg = "#1e1e1e"
            scrollbar_handle = "#424242"
            scrollbar_hover = "#4f4f4f"
            menu_bg = "#252526"
            menu_fg = "#cccccc"
            menu_sel = "#094771"
            bar_bg = "#007acc"
            bar_fg = "#ffffff"
            input_bg = "#3c3c3c"
            input_fg = "#cccccc"
        else:
            bg_color = "#ffffff"
            fg_color = "#000000"
            selection_bg = "#add6ff"
            selection_fg = "#000000"
            hover_bg = "#e8e8e8"
            scrollbar_bg = "#f3f3f3"
            scrollbar_handle = "#c1c1c1"
            scrollbar_hover = "#a8a8a8"
            menu_bg = "#f3f3f3"
            menu_fg = "#333333"
            menu_sel = "#0060c0"
            bar_bg = "#007acc"
            bar_fg = "#ffffff"
            input_bg = "#ffffff"
            input_fg = "#000000"

        self.delegate.set_hover_color(hover_bg)
        self.list_view.viewport().update()
        self._set_windows_title_bar_color(self.is_dark_mode)
        self.update_status_bar(self.last_status_message)

        style = f"""
        QMainWindow {{ background-color: {bg_color}; color: {fg_color}; }}
        QWidget {{ color: {fg_color}; }}
        QMenuBar {{ background-color: {menu_bg}; color: {menu_fg}; }}
        QMenuBar::item {{ background-color: transparent; padding: 4px 8px; }}
        QMenuBar::item:selected {{ background-color: {selection_bg}; color: {selection_fg}; }}
        QMenu {{ background-color: {menu_bg}; color: {menu_fg}; border: 1px solid #454545; }}
        QMenu::item {{ padding: 5px 30px 5px 20px; background-color: transparent; }}
        QMenu::item:selected {{ background-color: {menu_sel}; color: #ffffff; }}
        QListView {{ background-color: {bg_color}; color: {fg_color}; border: none; outline: 0; }}
        QListView::item {{ padding: 0px 4px; border-bottom: 0px solid transparent; }}
        QListView::item:selected {{ background-color: {selection_bg}; color: {selection_fg}; }}
        QStatusBar {{ background-color: {bar_bg}; color: {bar_fg}; }}
        QStatusBar::item {{ border: none; }}
        QStatusBar QLabel {{ color: {bar_fg}; background-color: transparent; }}
        QScrollBar:vertical {{ border: none; background: {scrollbar_bg}; width: 14px; margin: 0px; }}
        QScrollBar::handle:vertical {{ background: {scrollbar_handle}; min-height: 20px; }}
        QScrollBar::handle:vertical:hover {{ background: {scrollbar_hover}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

        /* Search Bar Styling */
        QComboBox {{ background-color: {input_bg}; color: {input_fg}; border: 1px solid #555; padding: 2px; }}
        QComboBox QAbstractItemView {{ background-color: {menu_bg}; color: {menu_fg}; selection-background-color: {menu_sel}; }}
        QToolButton {{ background-color: {input_bg}; color: {input_fg}; border: 1px solid #555; }}
        QToolButton:hover {{ background-color: {hover_bg}; }}
        """
        self.setStyleSheet(style)

    def open_file_dialog(self):
        last_dir = self.settings.value("last_dir", "")
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Log File", last_dir, "Log Files (*.log *.txt);;All Files (*)")
        if filepath:
            self.load_log(filepath)

    def load_log(self, filepath):
        self.update_status_bar(f"Loading {filepath}...")
        start_time = time.time()
        self.settings.setValue("last_dir", os.path.dirname(filepath))

        self.current_engine = get_engine(filepath)
        self.model.set_engine(self.current_engine)

        end_time = time.time()
        duration = end_time - start_time

        count = self.current_engine.line_count()
        self.setWindowTitle(f"{os.path.basename(filepath)} - Log Analyzer")
        self.update_status_bar(f"Shows {count:,} lines (Total {count:,})")
        self.toast.show_message(f"Loaded {count:,} lines in {duration:.3f}s", duration=4000)

        # Reset search
        self.search_results = []
        self.current_match_index = -1
        self.search_info_label.setText("")

    def show_context_menu(self, pos):
        menu = QMenu(self)
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.copy_selection)
        menu.addAction(copy_action)
        menu.exec_(self.list_view.mapToGlobal(pos))

    def copy_selection(self):
        indexes = self.list_view.selectionModel().selectedIndexes()
        if not indexes: return
        indexes.sort(key=lambda x: x.row())
        text_lines = []
        for index in indexes:
            line = self.model.data(index, Qt.DisplayRole)
            if line: text_lines.append(line)
        if text_lines:
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(text_lines))
            self.toast.show_message(f"Copied {len(text_lines)} lines", duration=3000)

    def resizeEvent(self, event):
        if not self.toast.isHidden():
             txt = self.toast.label.text()
             self.toast.show_message(txt, duration=self.toast.timer.remainingTime())
        super().resizeEvent(event)

    # --- Search Logic ---

    def show_search_bar(self):
        if self.search_widget.isHidden():
            self.search_widget.show()
            self.search_input.setFocus()
            self.search_input.lineEdit().selectAll()
        else:
            self.search_input.setFocus()
            self.search_input.lineEdit().selectAll()

    def hide_search_bar(self):
        self.search_widget.hide()
        self.delegate.set_search_query(None)
        self.list_view.viewport().update()
        self.search_info_label.setText("")
        # Return focus to list view
        self.list_view.setFocus()

    def _update_search_history(self, query):
        if query in self.search_history:
            self.search_history.remove(query)
        self.search_history.insert(0, query)
        self.search_history = self.search_history[:10] # Max 10

        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.addItems(self.search_history)
        self.search_input.setCurrentText(query)
        self.search_input.blockSignals(False)

        # Save history
        self.settings.setValue("search_history", self.search_history)

    def _load_search_history(self):
        hist = self.settings.value("search_history", [])
        if hist:
            self.search_history = [str(x) for x in hist]
            self.search_input.addItems(self.search_history)
            self.search_input.setCurrentIndex(-1)

    def _perform_search(self, query):
        if not query or not self.current_engine: return

        self.toast.show_message(f"Searching for '{query}'...", duration=1000)
        self.update_status_bar("Searching...")
        QApplication.processEvents() # Force UI update before blocking search

        # Perform Search (Rust Backend)
        # Assuming simple case-insensitive substring search for now as per delegates logic
        results = self.current_engine.search(query, False, False) # query, regex=False, case=False

        self.search_results = results
        self.current_match_index = -1

        # Update Delegate to Highlight
        self.delegate.set_search_query(query)
        self.list_view.viewport().update()

        self.update_status_bar(f"Found {len(results):,} matches")

        # If matches found, jump to first one visible or just the first one
        if results:
            self._jump_to_match(0)
        else:
            self.search_info_label.setText("No results")
            self.toast.show_message("No results found", duration=2000)

    def _jump_to_match(self, result_index):
        if not self.search_results or result_index < 0 or result_index >= len(self.search_results):
            return

        self.current_match_index = result_index
        row_idx = self.search_results[result_index]

        # Scroll to item
        index = self.model.index(row_idx, 0)
        if index.isValid():
            # Center the row
            self.list_view.scrollTo(index, QAbstractItemView.PositionAtCenter)
            # Select it
            self.list_view.setCurrentIndex(index)

        # Update Info Label
        self.search_info_label.setText(f"{result_index + 1} / {len(self.search_results)}")

    def find_next(self):
        query = self.search_input.currentText()
        if not query: return

        # New Search Check
        if self.delegate.search_query != query or not self.search_results:
            self._update_search_history(query)
            self._perform_search(query)
            return

        # Navigate
        if not self.search_results: return

        # If we are already at a match, find the next one relative to current selection
        # But for simplicity, we just increment our internal index
        next_idx = self.current_match_index + 1
        if next_idx >= len(self.search_results):
            next_idx = 0 # Wrap
            self.toast.show_message("Wrapped to top", duration=1000)

        self._jump_to_match(next_idx)

    def find_previous(self):
        query = self.search_input.currentText()
        if not query: return

        # New Search Check
        if self.delegate.search_query != query or not self.search_results:
            self._update_search_history(query)
            self._perform_search(query)
            return

        if not self.search_results: return

        prev_idx = self.current_match_index - 1
        if prev_idx < 0:
            prev_idx = len(self.search_results) - 1 # Wrap
            self.toast.show_message("Wrapped to bottom", duration=1000)

        self._jump_to_match(prev_idx)
