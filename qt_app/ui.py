from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QListView,
                               QLabel, QFileDialog, QMenuBar, QMenu, QStatusBar)
from PySide6.QtGui import QAction, QFont, QPalette, QColor
from PySide6.QtCore import Qt
from .models import LogModel
from .engine_wrapper import get_engine
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Log Analyzer (PySide6)")
        self.resize(1200, 800)

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header / Toolbar Area (Optional, using Menu for now)

        # Log List View
        self.list_view = QListView()
        self.model = LogModel()
        self.list_view.setModel(self.model)

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

        # Menu
        self._create_menu()

        # Styling
        self._apply_theme()

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
        # Placeholder for future features

    def _apply_theme(self):
        # VS Code Dark Theme Colors
        bg_color = "#1e1e1e"
        fg_color = "#d4d4d4"
        selection_bg = "#264f78"
        scrollbar_bg = "#1e1e1e"
        scrollbar_handle = "#424242"

        style = f"""
        QMainWindow {{
            background-color: {bg_color};
        }}
        QMenuBar {{
            background-color: #333333;
            color: #cccccc;
        }}
        QMenuBar::item:selected {{
            background-color: #505050;
        }}
        QMenu {{
            background-color: #252526;
            color: #cccccc;
            border: 1px solid #454545;
        }}
        QMenu::item:selected {{
            background-color: #094771;
        }}
        QListView {{
            background-color: {bg_color};
            color: {fg_color};
            border: none;
            outline: 0;
        }}
        QListView::item {{
            padding: 2px;
        }}
        QListView::item:selected {{
            background-color: {selection_bg};
            color: #ffffff;
        }}
        QStatusBar {{
            background-color: #007acc;
            color: #ffffff;
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
            background: #4f4f4f;
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
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Log File", "", "Log Files (*.log *.txt);;All Files (*)")
        if filepath:
            self.load_log(filepath)

    def load_log(self, filepath):
        self.status_bar.showMessage(f"Loading {filepath}...")

        # Assuming the Engine load is blocking for now, but Rust is fast.
        # In a real app, we might want to thread this instantiation if it takes time.
        engine = get_engine(filepath)
        self.model.set_engine(engine)

        count = engine.line_count()
        self.setWindowTitle(f"{os.path.basename(filepath)} - Log Analyzer")
        self.status_bar.showMessage(f"Loaded {count:,} lines from {filepath}")
