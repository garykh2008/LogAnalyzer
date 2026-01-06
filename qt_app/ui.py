from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QListView,
                               QLabel, QFileDialog, QMenuBar, QMenu, QStatusBar, QAbstractItemView, QApplication)
from PySide6.QtGui import QAction, QFont, QPalette, QColor, QKeySequence, QCursor
from PySide6.QtCore import Qt, QSettings, QTimer
from .models import LogModel
from .engine_wrapper import get_engine
from .toast import Toast
from .delegates import LogDelegate
import os
import time

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Log Analyzer (PySide6)")
        self.resize(1200, 800)

        # Settings
        self.settings = QSettings("LogAnalyzer", "QtApp")
        # Load theme preference (default to True/Dark)
        self.is_dark_mode = self.settings.value("dark_mode", True, type=bool)

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

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
        self.status_bar.showMessage("Ready")

        # Toast notification
        self.toast = Toast(self)

        # Menu
        self._create_menu()

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

    def apply_theme(self):
        if self.is_dark_mode:
            # VS Code Dark Theme Colors
            bg_color = "#1e1e1e"
            fg_color = "#d4d4d4"
            selection_bg = "#264f78"
            selection_fg = "#ffffff"
            hover_bg = "#2a2d2e"
            scrollbar_bg = "#1e1e1e"
            scrollbar_handle = "#424242"
            scrollbar_hover = "#4f4f4f"
            menu_bg = "#252526"
            menu_sel = "#094771"
            bar_bg = "#007acc"
            bar_fg = "#ffffff"
        else:
            # VS Code Light Theme Colors (Approximate)
            bg_color = "#ffffff"
            fg_color = "#000000"
            selection_bg = "#add6ff"
            selection_fg = "#000000"
            hover_bg = "#e8e8e8"
            scrollbar_bg = "#f3f3f3"
            scrollbar_handle = "#c1c1c1"
            scrollbar_hover = "#a8a8a8"
            menu_bg = "#f3f3f3"
            menu_sel = "#0060c0" # Native-ish highlight
            bar_bg = "#007acc" # VS Code usually keeps blue status bar, or purple
            bar_fg = "#ffffff"

        # Update Delegate Hover Color
        self.delegate.set_hover_color(hover_bg)

        # We need to manually trigger a repaint of the list view to apply delegate changes immediately
        self.list_view.viewport().update()

        style = f"""
        QMainWindow {{
            background-color: {bg_color};
            color: {fg_color};
        }}
        QWidget {{
            color: {fg_color};
        }}
        QMenuBar {{
            background-color: {menu_bg};
            color: {fg_color};
        }}
        QMenuBar::item:selected {{
            background-color: {selection_bg};
            color: {selection_fg};
        }}
        QMenu {{
            background-color: {menu_bg};
            color: {fg_color};
            border: 1px solid #454545;
        }}
        QMenu::item:selected {{
            background-color: {menu_sel};
            color: #ffffff;
        }}
        QListView {{
            background-color: {bg_color};
            color: {fg_color};
            border: none;
            outline: 0;
        }}
        QListView::item {{
            padding: 0px 4px;
            border-bottom: 0px solid transparent;
        }}
        QListView::item:selected {{
            background-color: {selection_bg};
            color: {selection_fg};
        }}
        QStatusBar {{
            background-color: {bar_bg};
            color: {bar_fg};
        }}
        /* Scrollbar Styling */
        QScrollBar:vertical {{
            border: none;
            background: {scrollbar_bg};
            width: 14px;
            margin: 0px;
        }}
        QScrollBar::handle:vertical {{
            background: {scrollbar_handle};
            min-height: 20px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {scrollbar_hover};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}
        """
        self.setStyleSheet(style)

    def open_file_dialog(self):
        # 3. App Memory: Load last directory
        last_dir = self.settings.value("last_dir", "")

        filepath, _ = QFileDialog.getOpenFileName(self, "Open Log File", last_dir, "Log Files (*.log *.txt);;All Files (*)")
        if filepath:
            self.load_log(filepath)

    def load_log(self, filepath):
        self.status_bar.showMessage(f"Loading {filepath}...")

        start_time = time.time()

        # Save last directory
        self.settings.setValue("last_dir", os.path.dirname(filepath))

        engine = get_engine(filepath)
        self.model.set_engine(engine)

        end_time = time.time()
        duration = end_time - start_time

        count = engine.line_count()
        self.setWindowTitle(f"{os.path.basename(filepath)} - Log Analyzer")

        # Status Bar Update (Shows xxx lines (Total xxx))
        # Currently no filtering, so Shows == Total
        self.status_bar.showMessage(f"Shows {count:,} lines (Total {count:,})")

        # 4. Toast Notification
        self.toast.show_message(f"Loaded {count:,} lines in {duration:.3f}s", duration=4000)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.copy_selection)
        menu.addAction(copy_action)
        menu.exec_(self.list_view.mapToGlobal(pos))

    def copy_selection(self):
        indexes = self.list_view.selectionModel().selectedIndexes()
        if not indexes:
            return

        # Sort by row to ensure correct order
        indexes.sort(key=lambda x: x.row())

        text_lines = []
        for index in indexes:
            # We assume data(DisplayRole) returns the string
            line = self.model.data(index, Qt.DisplayRole)
            if line:
                text_lines.append(line)

        if text_lines:
            clipboard = QApplication.clipboard()
            clipboard.setText("\n".join(text_lines))

            # Use Toast for feedback
            self.toast.show_message(f"Copied {len(text_lines)} lines", duration=3000)

    def resizeEvent(self, event):
        # Ensure toast stays positioned on resize
        if not self.toast.isHidden():
             # Re-trigger show logic to update position
             txt = self.toast.label.text()
             self.toast.show_message(txt, duration=self.toast.timer.remainingTime())
        super().resizeEvent(event)
