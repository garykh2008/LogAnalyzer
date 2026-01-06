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
import sys
import ctypes

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

        # Persistent Status Label (prevents menu hover from clearing the message)
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        # Add some padding to the label itself if needed, or via QSS
        self.status_bar.addWidget(self.status_label, 1) # Stretch=1 to take space

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

    def update_status_bar(self, message):
        self.last_status_message = message
        # Use setText on the persistent label instead of showMessage
        self.status_label.setText(message)

    def _set_windows_title_bar_color(self, is_dark):
        """
        Uses ctypes to set the Windows 10/11 title bar color preference.
        """
        if sys.platform != "win32":
            return

        try:
            hwnd = int(self.winId())
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 10 2004 build 19041+)
            # Prior to that, DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20h1 = 19
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            value = ctypes.c_int(1 if is_dark else 0)

            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(value),
                ctypes.sizeof(value)
            )
        except Exception as e:
            print(f"Failed to set title bar color: {e}")

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
            menu_fg = "#cccccc"
            menu_sel = "#094771"
            bar_bg = "#007acc"
            bar_fg = "#ffffff"
        else:
            # VS Code Light Theme Colors
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

        # Update Delegate Hover Color
        self.delegate.set_hover_color(hover_bg)
        self.list_view.viewport().update()

        # Apply Title Bar Color (Windows)
        self._set_windows_title_bar_color(self.is_dark_mode)

        # Restore status bar text
        self.update_status_bar(self.last_status_message)

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
            color: {menu_fg};
        }}
        QMenuBar::item {{
            background-color: transparent;
            padding: 4px 8px;
        }}
        QMenuBar::item:selected {{
            background-color: {selection_bg};
            color: {selection_fg};
        }}
        QMenu {{
            background-color: {menu_bg};
            color: {menu_fg};
            border: 1px solid #454545;
        }}
        QMenu::item {{
            padding: 5px 30px 5px 20px;
            background-color: transparent;
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
        QStatusBar::item {{
            border: none;
        }}
        QStatusBar QLabel {{
            color: {bar_fg};
            background-color: transparent;
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
        self.update_status_bar(f"Loading {filepath}...")

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
        self.update_status_bar(f"Shows {count:,} lines (Total {count:,})")

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
