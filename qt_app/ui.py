from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QListView,
                               QLabel, QFileDialog, QMenuBar, QMenu, QStatusBar, QAbstractItemView, QApplication,
                               QHBoxLayout, QLineEdit, QToolButton, QComboBox, QSizePolicy, QGraphicsDropShadowEffect,
                               QGraphicsOpacityEffect, QCheckBox, QDockWidget, QTreeWidget, QTreeWidgetItem, QHeaderView,
                               QDialog, QMessageBox, QScrollBar, QPushButton, QStackedLayout, QInputDialog, QFrame,
                               QSplitter)
from PySide6.QtGui import QAction, QFont, QPalette, QColor, QKeySequence, QCursor, QIcon, QShortcut, QWheelEvent, QFontMetrics, QFontInfo
from PySide6.QtCore import Qt, QSettings, QTimer, Slot, QModelIndex, QEvent, QPropertyAnimation, QSize
from .models import LogModel
from .engine_wrapper import get_engine
from .toast import Toast
from .delegates import LogDelegate, FilterDelegate
from .filter_dialog import FilterDialog

from .notes_manager import NotesManager
from .resources import get_svg_icon
from .utils import adjust_color_for_theme, load_tat_filters, save_tat_filters, set_windows_title_bar_color
import os
import time
import sys
import ctypes
import bisect

class FilterTreeWidget(QTreeWidget):
    def __init__(self, on_drop_callback=None, parent=None):
        super().__init__(parent)
        self.on_drop_callback = on_drop_callback

    def dropEvent(self, event):
        super().dropEvent(event)
        if self.on_drop_callback:
            self.on_drop_callback()

class MainWindow(QMainWindow):
    VERSION = "V2.0"
    APP_NAME = "Log Analyzer"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{self.APP_NAME} (PySide6)")
        
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "loganalyzer.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(1200, 800)

        self.settings = QSettings("LogAnalyzer", "QtApp")
        self.is_dark_mode = self.settings.value("dark_mode", True, type=bool)
        self.setAcceptDrops(True)
        self.last_status_message = "Ready"
        self.current_filter_file = None

        # --- Multi-Log Management ---
        self.loaded_logs = {} # {path: engine}
        self.log_order = [] # Ordered paths
        self.current_active_log = None # Selected path or MERGED_VIEW_ID

        self.current_engine = None
        self.search_results = []
        self.current_match_index = -1
        self.search_history = []
        self.filters = []
        self.show_filtered_only = False

        self.filters_modified = False
        self.selected_filter_index = -1
        self.selected_raw_index = -1
        self.current_log_path = None
        self.filters_dirty_cache = True 
        self.cached_filter_results = None 
        self.is_scrolling = False
        
        self.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks | QMainWindow.AllowTabbedDocks)

        self.list_view = QListView()
        self.model = LogModel()
        self.list_view.setModel(self.model)

        self.delegate = LogDelegate(self.list_view)
        self.list_view.setItemDelegate(self.delegate)

        self.list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self.show_context_menu)
        self.list_view.doubleClicked.connect(self.on_log_double_clicked)

        self.notes_manager = NotesManager(self)
        self.model.set_notes_ref(self.notes_manager.notes)
        self.notes_manager.notes_updated.connect(self.on_notes_updated)
        self.notes_manager.navigation_requested.connect(self.jump_to_raw_index)

        self.list_view.setUniformItemSizes(False) # Allow variable widths for horizontal scrolling


        # --- Activity Bar ---
        self.activity_bar = self.addToolBar("Activity Bar")
        self.activity_bar.setObjectName("activity_bar")
        self.activity_bar.setMovable(False)
        self.activity_bar.setAllowedAreas(Qt.LeftToolBarArea)
        self.activity_bar.setOrientation(Qt.Vertical)
        self.activity_bar.setIconSize(QSize(28, 28))
        self.addToolBar(Qt.LeftToolBarArea, self.activity_bar)

        self.btn_side_loglist = QToolButton()
        self.btn_side_loglist.setCheckable(True)
        self.btn_side_loglist.setFixedSize(48, 48)
        self.btn_side_loglist.setToolTip("Log Files (Ctrl+Shift+L)")
        self.btn_side_loglist.clicked.connect(lambda: self.toggle_sidebar(2))

        self.btn_side_filter = QToolButton()
        self.btn_side_filter.setCheckable(True)
        self.btn_side_filter.setFixedSize(48, 48)
        self.btn_side_filter.setToolTip("Filters (Ctrl+Shift+F)")
        self.btn_side_filter.clicked.connect(lambda: self.toggle_sidebar(0))

        self.btn_side_notes = QToolButton()
        self.btn_side_notes.setCheckable(True)
        self.btn_side_notes.setFixedSize(48, 48)
        self.btn_side_notes.setToolTip("Notes (Ctrl+Shift+N)")
        self.btn_side_notes.clicked.connect(lambda: self.toggle_sidebar(1))

        self.activity_bar.addWidget(self.btn_side_loglist)
        self.activity_bar.addWidget(self.btn_side_filter)
        self.activity_bar.addWidget(self.btn_side_notes)

        # --- Log List Dock ---
        self.log_list_dock = QDockWidget("LOG FILES", self)
        self.log_list_dock.setObjectName("LogListDock")
        self.log_list_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.log_list_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        
        self.log_tree = FilterTreeWidget(on_drop_callback=self.on_log_reordered)
        self.log_tree.setHeaderHidden(True) # Hide "File" header
        self.log_tree.setRootIsDecorated(False)
        self.log_tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.log_tree.setDefaultDropAction(Qt.MoveAction)
        self.log_tree.setDropIndicatorShown(True)
        self.log_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.log_tree.itemClicked.connect(self.on_log_tree_clicked)
        self.log_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.log_tree.customContextMenuRequested.connect(self.show_log_list_context_menu)
        
        from .delegates import LogListDelegate
        self.log_list_delegate = LogListDelegate(self.log_tree)
        self.log_list_delegate.close_requested.connect(self._remove_log_file)
        self.log_tree.setItemDelegate(self.log_list_delegate)

        self.log_list_dock.setWidget(self.log_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.log_list_dock)
        self.log_list_dock.visibilityChanged.connect(lambda visible: self.btn_side_loglist.setChecked(visible))
        self.log_list_dock.topLevelChanged.connect(lambda floating: set_windows_title_bar_color(self.log_list_dock.winId(), self.is_dark_mode))
        self.log_list_dock.hide()

        # --- Filter Dock ---
        self.filter_dock = QDockWidget("FILTERS", self)
        self.filter_dock.setObjectName("FilterDock")
        self.filter_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.filter_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        
        self.filter_tree = FilterTreeWidget(on_drop_callback=self.on_filter_tree_reordered)
        self.filter_tree.setItemDelegate(FilterDelegate(self.filter_tree))
        self.filter_tree.setIndentation(0)

        self.filter_tree.setHeaderLabels(["", "Pattern", "Hits  "])
        
        header = self.filter_tree.header()
        header.setMinimumSectionSize(0)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.resizeSection(0, 25) 
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.filter_tree.setRootIsDecorated(False)
        self.filter_tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.filter_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.filter_tree.setDefaultDropAction(Qt.MoveAction)
        self.filter_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.filter_tree.customContextMenuRequested.connect(self.show_filter_menu)
        self.filter_tree.itemDoubleClicked.connect(self.edit_selected_filter)
        self.filter_tree.itemChanged.connect(self.on_filter_item_changed)
        self.filter_tree.itemClicked.connect(self.on_filter_item_clicked)
        self.filter_tree.currentItemChanged.connect(lambda curr, prev: self.on_filter_item_clicked(curr, 0))
        self.filter_tree.installEventFilter(self)


        self.filter_dock.setWidget(self.filter_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.filter_dock)
        self.filter_dock.visibilityChanged.connect(lambda visible: self.btn_side_filter.setChecked(visible))
        self.filter_dock.topLevelChanged.connect(lambda floating: set_windows_title_bar_color(self.filter_dock.winId(), self.is_dark_mode))
        self.filter_dock.hide()

        # --- Notes Dock ---
        self.notes_dock = self.notes_manager.dock
        self.notes_dock.setWindowTitle("NOTES")
        self.notes_dock.setObjectName("NotesDock")
        self.notes_dock.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        self.notes_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.notes_dock)
        self.notes_dock.visibilityChanged.connect(lambda visible: self.btn_side_notes.setChecked(visible))
        self.notes_dock.topLevelChanged.connect(lambda floating: set_windows_title_bar_color(self.notes_dock.winId(), self.is_dark_mode))
        self.notes_dock.hide()

        # Virtual Viewport Setup
        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.v_scrollbar = QScrollBar(Qt.Vertical)
        self.v_scrollbar.valueChanged.connect(self.on_scrollbar_value_changed)
        self.list_view.installEventFilter(self)
        
        self.list_view.selectionModel().currentChanged.connect(self.on_view_selection_changed)

        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.list_view.setFont(font)

        # --- Main Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.central_layout = QVBoxLayout(central_widget)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.central_layout.setSpacing(0)

        self.central_area = QWidget()
        self.central_stack = QStackedLayout(self.central_area)
        self.central_layout.addWidget(self.central_area)
        
        # Page 0: Welcome
        self.welcome_label = QLabel("Drag & Drop Log File Here\nor use File > Open Log", self.central_area)
        self.welcome_label.setAlignment(Qt.AlignCenter)
        font_welcome = QFont("Inter", 14)
        if not QFontInfo(font_welcome).exactMatch() and QFontInfo(font_welcome).family() != "Inter":
            font_welcome = QFont("Segoe UI", 14)
        self.welcome_label.setFont(font_welcome)
        self.welcome_label.setStyleSheet("color: #888888;")
        self.central_stack.addWidget(self.welcome_label)

        # Page 1: List View Container
        list_container = QWidget(self.central_area)
        list_layout = QHBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)
        list_layout.addWidget(self.list_view)
        list_layout.addWidget(self.v_scrollbar)
        self.central_stack.addWidget(list_container)
        
        self.central_stack.setCurrentIndex(0)

        # --- Search Bar ---
        self.search_widget = QWidget(self.central_area)
        self.search_widget.setObjectName("search_widget")
        self.search_layout = QHBoxLayout(self.search_widget)
        self.search_layout.setContentsMargins(5, 5, 5, 5)
        self.search_layout.setSpacing(5)

        self.search_input = QComboBox()
        self.search_input.setEditable(True)
        self.search_input.setPlaceholderText("Find...")
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_input.lineEdit().returnPressed.connect(self.find_next)
        
        # Install event filter for Esc key handling
        self.search_input.installEventFilter(self)
        self.search_input.lineEdit().installEventFilter(self)

        self.btn_prev = QToolButton()
        self.btn_prev.setFixedSize(26, 24)
        self.btn_next = QToolButton()
        self.btn_next.setFixedSize(26, 24)
        
        self.chk_case = QToolButton()
        self.chk_case.setCheckable(True)
        self.chk_case.setFixedSize(26, 24)
        self.chk_case.setToolTip("Match Case")
        self.chk_case.toggled.connect(self.on_search_case_changed)

        self.chk_wrap = QToolButton()
        self.chk_wrap.setToolTip("Wrap Search")
        self.chk_wrap.setCheckable(True)
        self.chk_wrap.setFixedSize(26, 24)
        self.chk_wrap.setChecked(True)

        self.btn_close_search = QToolButton()
        self.btn_close_search.clicked.connect(self.hide_search_bar)

        self.search_info_label = QLabel("")
        self.search_info_label.setMinimumWidth(40)
        self.search_info_label.setAlignment(Qt.AlignCenter)

        self.search_layout.addWidget(self.search_input)
        self.search_layout.addWidget(self.chk_case)
        self.search_layout.addWidget(self.chk_wrap)
        self.search_layout.addWidget(self.btn_prev)
        self.search_layout.addWidget(self.btn_next)
        self.search_layout.addWidget(self.search_info_label)
        self.search_layout.addWidget(self.btn_close_search)

        self.search_widget.setFixedWidth(550)
        self.search_widget.hide()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.status_bar.addWidget(self.status_label, 1)

        self.toast = Toast(self)
        self._create_menu()

        # 1. Restore saved geometry and layout state (remembers positions)
        has_saved_state = False
        if self.settings.value("window_geometry"):
            self.restoreGeometry(self.settings.value("window_geometry"))
        if self.settings.value("window_state"):
            has_saved_state = self.restoreState(self.settings.value("window_state"))

        # 2. Set default Tabify relationship ONLY if no saved state exists
        if not has_saved_state:
            self.tabifyDockWidget(self.log_list_dock, self.filter_dock)
            self.tabifyDockWidget(self.filter_dock, self.notes_dock)

        self.apply_theme()
        self.btn_prev.clicked.connect(self.find_previous)
        self.btn_next.clicked.connect(self.find_next)
        
        # 3. Force all docks hidden on startup (overrides visibility from restoreState)
        self.log_list_dock.hide()
        self.filter_dock.hide()
        self.notes_dock.hide()

    def _create_menu(self):
        menu_bar = self.menuBar()
        
        file_menu = menu_bar.addMenu("&File")
        self.open_action = QAction("&Open Log...", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(self.open_action)

        self.recent_menu = file_menu.addMenu("Open Recent")
        self.recent_menu.setIcon(get_svg_icon("folder"))
        self.update_recent_menu()

        file_menu.addSeparator()
        self.load_filters_action = QAction("Load Filters...", self)
        self.load_filters_action.triggered.connect(self.import_filters)
        file_menu.addAction(self.load_filters_action)

        self.save_filters_action = QAction("Save Filters", self)
        self.save_filters_action.triggered.connect(self.quick_save_filters)
        file_menu.addAction(self.save_filters_action)

        self.save_filters_as_action = QAction("Save Filters As...", self)
        self.save_filters_as_action.triggered.connect(self.save_filters_as)
        file_menu.addAction(self.save_filters_as_action)

        file_menu.addSeparator()
        self.exit_action = QAction("E&xit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close_app)
        file_menu.addAction(self.exit_action)

        edit_menu = menu_bar.addMenu("&Edit")
        self.copy_action = QAction("&Copy", self)
        self.copy_action.setShortcut(QKeySequence.Copy)
        self.copy_action.triggered.connect(self.copy_selection)
        edit_menu.addAction(self.copy_action)

        edit_menu.addSeparator()
        self.find_action = QAction("&Find...", self)
        self.find_action.setShortcut(QKeySequence.Find)
        self.find_action.triggered.connect(self.show_search_bar)
        edit_menu.addAction(self.find_action)

        self.goto_action = QAction("Go to Line...", self)
        self.goto_action.setShortcut("Ctrl+G")
        self.goto_action.triggered.connect(self.show_goto_dialog)
        edit_menu.addAction(self.goto_action)

        view_menu = menu_bar.addMenu("&View")
        self.toggle_log_sidebar_action = QAction("Log Files", self)
        self.toggle_log_sidebar_action.setShortcut("Ctrl+Shift+L")
        self.toggle_log_sidebar_action.triggered.connect(lambda: self.toggle_sidebar(2))
        view_menu.addAction(self.toggle_log_sidebar_action)

        self.toggle_filter_sidebar_action = QAction("Filters", self)
        self.toggle_filter_sidebar_action.setShortcut("Ctrl+Shift+F")
        self.toggle_filter_sidebar_action.triggered.connect(lambda: self.toggle_sidebar(0))
        view_menu.addAction(self.toggle_filter_sidebar_action)
        
        self.toggle_notes_sidebar_action = QAction("Notes", self)
        self.toggle_notes_sidebar_action.setShortcut("Ctrl+Shift+N")
        self.toggle_notes_sidebar_action.triggered.connect(lambda: self.toggle_sidebar(1))
        view_menu.addAction(self.toggle_notes_sidebar_action)

        view_menu.addSeparator()
        self.show_filtered_action = QAction("Show Filtered Only", self)
        self.show_filtered_action.setShortcut("Ctrl+H")
        self.show_filtered_action.setCheckable(True)
        self.show_filtered_action.triggered.connect(self.toggle_show_filtered_only)
        view_menu.addAction(self.show_filtered_action)

        view_menu.addSeparator()
        self.toggle_theme_action = QAction("Toggle Dark/Light Mode", self)
        self.toggle_theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(self.toggle_theme_action)

        notes_menu = menu_bar.addMenu("&Notes")
        self.add_note_action = QAction("Add/Edit Note", self)
        self.add_note_action.setShortcut("C")
        self.add_note_action.triggered.connect(self.add_note_at_current)
        notes_menu.addAction(self.add_note_action)
        
        self.remove_note_action = QAction("Remove Note", self)
        self.remove_note_action.triggered.connect(self.remove_note_at_current)
        notes_menu.addAction(self.remove_note_action)
        
        notes_menu.addSeparator()
        self.save_notes_action = QAction("Save Notes", self)
        self.save_notes_action.triggered.connect(self.notes_manager.quick_save)
        notes_menu.addAction(self.save_notes_action)
        
        self.export_notes_action = QAction("Export Notes to Text...", self)
        self.export_notes_action.triggered.connect(self.export_notes_to_text)
        notes_menu.addAction(self.export_notes_action)

        self.next_action = QAction("Find Next", self)
        self.next_action.setShortcut("F3")
        self.next_action.triggered.connect(self.find_next)
        self.addAction(self.next_action)
        
        self.prev_action = QAction("Find Previous", self)
        self.prev_action.setShortcut("F2")
        self.prev_action.triggered.connect(self.find_previous)
        self.addAction(self.prev_action)

        help_menu = menu_bar.addMenu("&Help")
        self.shortcuts_action = QAction("Keyboard Shortcuts", self)
        self.shortcuts_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(self.shortcuts_action)
        self.doc_action = QAction("Documentation", self)
        self.doc_action.triggered.connect(self.open_documentation)
        help_menu.addAction(self.doc_action)
        help_menu.addSeparator()
        self.about_action = QAction("About", self)
        self.about_action.triggered.connect(self.show_about)
        help_menu.addAction(self.about_action)

    def add_note_at_current(self):
        idx = self.list_view.currentIndex()
        if idx.isValid():
            abs_row = self.model.viewport_start + idx.row()
            raw_index = abs_row
            if self.show_filtered_only and self.model.filtered_indices:
                if abs_row < len(self.model.filtered_indices):
                    raw_index = self.model.filtered_indices[abs_row]
            self.notes_manager.add_note(raw_index, "", self.current_log_path)

    def remove_note_at_current(self):
        idx = self.list_view.currentIndex()
        if idx.isValid():
            abs_row = self.model.viewport_start + idx.row()
            raw_index = abs_row
            if self.show_filtered_only and self.model.filtered_indices:
                if abs_row < len(self.model.filtered_indices):
                    raw_index = self.model.filtered_indices[abs_row]
            self.notes_manager.delete_note(raw_index, self.current_log_path)

    def toggle_show_filtered_only(self):
        self.show_filtered_only = self.show_filtered_action.isChecked()
        self.recalc_filters()
        
        # Trigger re-search to update results count and matches for visibility change
        query = self.search_input.currentText()
        if query and not self.search_widget.isHidden():
            self._perform_search(query)

    def toggle_sidebar(self, index):
        docks = [self.filter_dock, self.notes_dock, self.log_list_dock]
        if index < 0 or index >= len(docks): return
        
        target = docks[index]
        peers = self.tabifiedDockWidgets(target)
        
        # Check if target is the currently active/visible tab in its area
        is_active = target.isVisible() and not target.visibleRegion().isEmpty()
        
        if peers:
            # Case: Tabbed/Overlapped
            if is_active:
                # Collapse the whole group
                target.hide()
                for p in peers: p.hide()
            else:
                # Switch to this tab
                target.show()
                target.raise_()
        else:
            # Case: Separate/Tiled or Single
            if target.isVisible():
                target.hide()
            else:
                target.show()
                target.raise_()

    def eventFilter(self, obj, event):
        if obj == self.list_view and event.type() == QEvent.Resize:
            self.update_scrollbar_range()
            return False
        if obj == self.list_view and event.type() == QEvent.Wheel:
            delta = event.angleDelta().y()
            self.v_scrollbar.setValue(self.v_scrollbar.value() + (-delta / 40))
            return True
        
        # Handle key events for both Log View and Filter Tree
        if event.type() == QEvent.KeyPress:
            key = event.key()
            mod = event.modifiers()
            
            # Global Esc to close search bar
            if key == Qt.Key_Escape and not self.search_widget.isHidden():
                self.hide_search_bar()
                return True

            if (mod & Qt.ControlModifier):
                if key == Qt.Key_Left:
                    self.navigate_filter_hit(reverse=True)
                    return True
                elif key == Qt.Key_Right:
                    self.navigate_filter_hit(reverse=False)
                    return True

            if obj == self.list_view:
                if key == Qt.Key_Return or key == Qt.Key_Enter:
                    if not self.search_widget.isHidden():
                        self.find_next()
                        return True
                elif key == Qt.Key_Down:
                    idx = self.list_view.currentIndex()
                    if idx.isValid() and idx.row() >= self.model.rowCount() - 1:
                        self.v_scrollbar.setValue(self.v_scrollbar.value() + 1)
                        return True
                elif key == Qt.Key_Up:
                    idx = self.list_view.currentIndex()
                    if idx.isValid() and idx.row() <= 0:
                        self.v_scrollbar.setValue(self.v_scrollbar.value() - 1)
                        return True
                elif key == Qt.Key_PageDown:
                    self.v_scrollbar.setValue(self.v_scrollbar.value() + self.v_scrollbar.pageStep())
                    return True
                elif key == Qt.Key_PageUp:
                    self.v_scrollbar.setValue(self.v_scrollbar.value() - self.v_scrollbar.pageStep())
                    return True
                elif key == Qt.Key_Home:
                    self.v_scrollbar.setValue(0)
                    self.list_view.setCurrentIndex(self.model.index(0, 0))
                    return True
                elif key == Qt.Key_End:
                    self.v_scrollbar.setValue(self.v_scrollbar.maximum())
                    last = self.model.rowCount() - 1
                    if last >= 0: self.list_view.setCurrentIndex(self.model.index(last, 0))
                    return True
                elif key == Qt.Key_C and mod == Qt.NoModifier:
                    self.add_note_at_current()
                    return True
        return super().eventFilter(obj, event)


    def apply_theme(self):
        self.notes_manager.set_theme(self.is_dark_mode)
        self.model.set_theme_mode(self.is_dark_mode)
        app = QApplication.instance()

        if self.is_dark_mode:
            bg_color, fg_color, selection_bg, selection_fg = "#1e1e1e", "#d4d4d4", "#264f78", "#ffffff"
            hover_bg, scrollbar_bg, scrollbar_handle = "#2a2d2e", "#1e1e1e", "#424242"
            scrollbar_hover, menu_bg, menu_fg, menu_sel = "#4f4f4f", "#252526", "#cccccc", "#094771"
            menu_sel_fg = "#ffffff"
            bar_bg, bar_fg, input_bg, input_fg = "#007acc", "#ffffff", "#3c3c3c", "#cccccc"
            float_bg, float_border, dock_title_bg, tree_bg = "#252526", "#3c3c3c", "#2d2d2d", "#252526"
            tab_bg, tab_fg, tab_sel_bg = "#2d2d2d", "#858585", "#1e1e1e"
            activity_bg, sidebar_bg = "#333333", "#252526"
            header_bg = "#1e1e1e"
            dialog_bg, dialog_fg = "#252526", "#cccccc"
            checkbox_active = "#007acc"
        else:
            bg_color, fg_color, selection_bg, selection_fg = "#ffffff", "#000000", "#add6ff", "#000000"
            hover_bg, scrollbar_bg, scrollbar_handle = "#e8e8e8", "#f3f3f3", "#c1c1c1"
            scrollbar_hover, menu_bg, menu_fg, menu_sel = "#a8a8a8", "#f3f3f3", "#333333", "#add6ff"
            menu_sel_fg = "#000000"
            bar_bg, bar_fg, input_bg, input_fg = "#007acc", "#ffffff", "#ffffff", "#000000"
            float_bg, float_border, dock_title_bg, tree_bg = "#f3f3f3", "#bbbbbb", "#e1e1e1", "#f3f3f3"
            tab_bg, tab_fg, tab_sel_bg = "#e1e1e1", "#666666", "#ffffff"
            activity_bg, sidebar_bg = "#f0f0f0", "#f8f8f8"
            header_bg = "#e5e5e5"
            dialog_bg, dialog_fg = "#f3f3f3", "#000000"
            checkbox_active = "#40a9ff"

        self.delegate.set_hover_color(hover_bg)
        self.list_view.viewport().update()
        self._set_windows_title_bar_color(self.is_dark_mode)
        for widget in QApplication.topLevelWidgets():
            if widget.isWindow(): set_windows_title_bar_color(widget.winId(), self.is_dark_mode)
        self.update_status_bar(self.last_status_message)

        style = f"""
        QWidget {{ font-family: "Inter", "Segoe UI", "Microsoft JhengHei UI", sans-serif; }}
        QMainWindow, QDialog, QMessageBox, QDockWidget {{ background-color: {bg_color}; color: {fg_color}; }}
        QWidget {{ color: {fg_color}; font-size: 12px; }}
        #activity_bar {{ background-color: {activity_bg}; border: none; spacing: 10px; padding-top: 5px; }}
        #activity_bar QToolButton {{ background-color: transparent; border: none; border-left: 3px solid transparent; border-radius: 0px; margin: 0px; font-size: 12px; }}
        #activity_bar QToolButton:hover {{ background-color: {hover_bg}; }}
        #activity_bar QToolButton:checked {{ border-left: 3px solid {bar_bg}; background-color: {hover_bg}; }}
        QDockWidget#FilterDock, QDockWidget#NotesDock, QDockWidget#LogListDock {{ color: {fg_color}; font-family: "Inter SemiBold", "Inter", "Segoe UI"; font-weight: normal; titlebar-close-icon: none; titlebar-normal-icon: none; }}
        QDockWidget#FilterDock::title, QDockWidget#NotesDock::title, QDockWidget#LogListDock::title {{ background: {sidebar_bg}; padding: 10px; border: none; }}
        #FilterDock QWidget, #NotesDock QWidget, #LogListDock QWidget {{ background-color: {sidebar_bg}; }}
        #FilterDock QTreeWidget, #NotesDock QTreeWidget, #LogListDock QTreeWidget {{ background-color: {sidebar_bg}; border: none; }}
        QMenuBar {{ background-color: {menu_bg}; color: {menu_fg}; border-bottom: 1px solid {float_border}; padding: 2px; }}
        QMenuBar::item {{ background-color: transparent; padding: 4px 10px; border-radius: 4px; }}
        QMenuBar::item:selected {{ background-color: {hover_bg}; color: {selection_fg}; }}
        QMenu {{ background-color: {menu_bg}; color: {menu_fg}; border: 1px solid {float_border}; border-radius: 4px; padding: 4px; }}
        QMenu::item {{ padding: 6px 25px 6px 20px; border-radius: 3px; }}
        QMenu::item:selected {{ background-color: {menu_sel}; color: {menu_sel_fg}; }}
        QMenu::separator {{ height: 1px; background: {float_border}; margin: 4px 8px; }}
        QListView {{ background-color: {bg_color}; color: {fg_color}; border: none; outline: 0; font-size: 11pt; font-family: "JetBrains Mono", "Consolas", monospace; }}
        QListView::item:selected {{ background-color: {selection_bg}; color: {selection_fg}; }}
                QTreeWidget {{ background-color: {tree_bg}; border: none; color: {fg_color}; outline: 0; }}
                QTreeWidget::item {{ padding: 4px; border: none; }}
                QTreeWidget::item:selected {{ background-color: {selection_bg}; color: {selection_fg}; }}
                QTreeWidget::item:hover {{ background-color: {hover_bg}; color: {fg_color}; }}
                
                QHeaderView {{ background-color: {header_bg}; border: none; border-bottom: 1px solid {float_border}; }}
                QHeaderView::section {{ background-color: {header_bg}; color: {fg_color}; border: none; border-right: none; padding: 6px 8px; font-family: "Inter SemiBold", "Inter", "Segoe UI"; font-weight: normal; text-align: left; }}
                QHeaderView::section:first {{ padding-left: 0px; padding-right: 0px; text-align: center; }}
                QHeaderView::section:last {{ padding-right: 4px; }}
                QHeaderView::section:horizontal {{ border-right: 1px solid transparent; }} /* Fix for some qt styles needing a border property to reset */
        
        QTabBar {{ height: 0px; width: 0px; background: transparent; }}
        QTabBar::tab {{ height: 0px; width: 0px; padding: 0px; margin: 0px; border: none; }}
        QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{ background-color: {input_bg}; color: {input_fg}; border: 1px solid {float_border}; border-radius: 4px; padding: 4px 8px; }}
        QPushButton {{ background-color: {menu_bg}; color: {fg_color}; border: 1px solid {float_border}; padding: 6px 16px; border-radius: 4px; }}
        QPushButton:hover {{ background-color: {hover_bg}; border: 1px solid {menu_sel}; }}
        QToolButton {{ background-color: transparent; color: {input_fg}; border: 1px solid transparent; border-radius: 4px; padding: 2px; }}
        QToolButton:hover {{ background-color: {hover_bg}; border: 1px solid {float_border}; }}
        QToolButton:checked {{ background-color: {selection_bg}; color: {selection_fg}; border: 1px solid {menu_sel}; }}
        QStatusBar {{ background-color: {menu_bg}; color: {menu_fg}; border-top: 1px solid {float_border}; }}
        QScrollBar:vertical {{ border: none; background: transparent; width: 10px; margin: 0px; }}
        QScrollBar::handle:vertical {{ background: {scrollbar_handle}; min-height: 20px; border-radius: 5px; }}
        QScrollBar::handle:vertical:hover {{ background: {scrollbar_hover}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; background: transparent; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        QScrollBar:horizontal {{ border: none; background: transparent; height: 10px; margin: 0px; }}
        QScrollBar::handle:horizontal {{ background: {scrollbar_handle}; min-width: 20px; border-radius: 5px; }}
        QScrollBar::handle:horizontal:hover {{ background: {scrollbar_hover}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; background: transparent; }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
        QAbstractScrollArea::corner {{ background: transparent; border: none; }}
        #search_widget {{ background-color: {float_bg}; border: 1px solid {float_border}; border-top: none; border-bottom-left-radius: 6px; border-bottom-right-radius: 6px; }}

        #search_widget QLabel {{ color: {input_fg}; background-color: transparent; }}
        """

        cb_border = "#555555" if not self.is_dark_mode else float_border
        cb_style = """
        QCheckBox { spacing: 8px; }
        QCheckBox::indicator, QTreeView::indicator { 
            width: 14px; height: 14px; border-radius: 3px; 
            border: 1px solid %s; background: %s; margin: 0px; padding: 0px;
        }
        QTreeView::indicator { subcontrol-origin: padding; subcontrol-position: center; }
        QCheckBox::indicator:checked, QTreeView::indicator:checked { 
            background: %s; 
            image: url("data:image/svg+xml,%%3Csvg xmlns='http://www.w3.org/2000/svg' width='24' height='24' viewBox='0 0 24 24' fill='none' stroke='white' stroke-width='4' stroke-linecap='round' stroke-linejoin='round'%%3E%%3Cpolyline points='20 6 9 17 4 12'%%3E%%3C/polyline%%3E%%3C/svg%%3E");
        }
        QCheckBox::indicator:hover, QTreeView::indicator:hover { border: 1px solid %s; }
        """ % (cb_border, input_bg, checkbox_active, menu_sel)
        
        style += cb_style
        app.setStyleSheet(style)

        # Refresh SVG Icons with current theme color
        icon_color = fg_color
        self.btn_side_loglist.setIcon(get_svg_icon("file-text", icon_color))
        self.btn_side_filter.setIcon(get_svg_icon("filter", icon_color))
        self.btn_side_notes.setIcon(get_svg_icon("book-open", icon_color))
        self.btn_prev.setIcon(get_svg_icon("chevron-up", icon_color))
        self.btn_next.setIcon(get_svg_icon("chevron-down", icon_color))
        self.chk_case.setIcon(get_svg_icon("case-sensitive", icon_color))
        self.chk_wrap.setIcon(get_svg_icon("wrap", icon_color))
        self.btn_close_search.setIcon(get_svg_icon("x-close", icon_color))
        
        self.open_action.setIcon(get_svg_icon("file-text", icon_color))
        self.recent_menu.setIcon(get_svg_icon("folder", icon_color))
        self.load_filters_action.setIcon(get_svg_icon("filter", icon_color))
        self.save_filters_action.setIcon(get_svg_icon("save", icon_color))
        self.save_filters_as_action.setIcon(get_svg_icon("save", icon_color))
        self.exit_action.setIcon(get_svg_icon("log-out", icon_color))
        
        self.copy_action.setIcon(get_svg_icon("copy", icon_color))
        self.find_action.setIcon(get_svg_icon("search", icon_color))
        self.goto_action.setIcon(get_svg_icon("hash", icon_color))
        
        self.toggle_log_sidebar_action.setIcon(get_svg_icon("file-text", icon_color))
        self.toggle_filter_sidebar_action.setIcon(get_svg_icon("filter", icon_color))
        self.toggle_notes_sidebar_action.setIcon(get_svg_icon("book-open", icon_color))
        self.show_filtered_action.setIcon(get_svg_icon("eye", icon_color))
        self.toggle_theme_action.setIcon(get_svg_icon("sun-moon", icon_color))
        
        self.add_note_action.setIcon(get_svg_icon("plus", icon_color))
        self.remove_note_action.setIcon(get_svg_icon("trash", icon_color))
        self.save_notes_action.setIcon(get_svg_icon("save", icon_color))
        self.export_notes_action.setIcon(get_svg_icon("external-link", icon_color))
        
        self.shortcuts_action.setIcon(get_svg_icon("keyboard", icon_color))
        self.doc_action.setIcon(get_svg_icon("external-link", icon_color))
        self.about_action.setIcon(get_svg_icon("info", icon_color))

    def open_file_dialog(self):
        last_dir = self.settings.value("last_dir", "")
        filepaths, _ = QFileDialog.getOpenFileNames(self, "Open Log Files", last_dir, "Log Files (*.log *.txt);;All Files (*)")
        if filepaths: 
            self._clear_all_logs()
            for fp in filepaths:
                self.load_log(fp, is_multiple=True)

    def _clear_all_logs(self):
        self.loaded_logs.clear()
        self.log_order.clear()
        self.update_log_tree()
        self.current_engine = None
        self.current_log_path = None
        self.model.set_engine(None)
        
        # Clear notes and refresh notes view
        self.notes_manager.notes.clear()
        self.notes_manager.refresh_list()
        
        self.welcome_label.show()
        self.central_stack.setCurrentIndex(0)
        self.update_window_title()

    def update_recent_menu(self):
        self.recent_menu.clear()
        recent_files = self.settings.value("recent_files", [], type=list)
        recent_files = [str(f) for f in recent_files if f]
        has_items = False
        for fp in recent_files:
            if not os.path.exists(fp): continue
            has_items = True
            action = QAction(os.path.basename(fp), self)
            action.triggered.connect(lambda checked=False, p=fp: self.load_log(p))
            self.recent_menu.addAction(action)
        if not has_items:
            self.recent_menu.setDisabled(True)
            return
        self.recent_menu.setDisabled(False)
        self.recent_menu.addSeparator()
        clear_action = QAction("Clear List", self)
        clear_action.triggered.connect(self.clear_recent_files)
        self.recent_menu.addAction(clear_action)

    def add_to_recent(self, filepath):
        recent_files = self.settings.value("recent_files", [], type=list)
        filepath = os.path.abspath(filepath)
        if filepath in recent_files: recent_files.remove(filepath)
        recent_files.insert(0, filepath)
        self.settings.setValue("recent_files", recent_files[:10])
        self.update_recent_menu()

    def clear_recent_files(self):
        self.settings.setValue("recent_files", [])
        self.update_recent_menu()

    def load_log(self, filepath, is_multiple=False):
        if not filepath or not os.path.exists(filepath): return
        
        # Check for unsaved notes before loading/switching if needed (optional)
        
        filepath = os.path.abspath(filepath)
        if filepath in self.loaded_logs:
            # Just switch if already loaded
            self._switch_to_log(filepath)
            return

        self.add_to_recent(filepath)
        self.central_stack.setCurrentIndex(1)
        self.welcome_label.hide()
        
        self.update_status_bar(f"Loading {filepath}...")
        start_time = time.time()
        self.settings.setValue("last_dir", os.path.dirname(filepath))
        
        engine = get_engine(filepath)
        self.loaded_logs[filepath] = engine
        self.log_order.append(filepath)
        
        self.update_log_tree()
        self._switch_to_log(filepath)
        
        count = engine.line_count()
        self.toast.show_message(f"Loaded {count:,} lines in {time.time()-start_time:.3f}s", duration=4000)

    def _switch_to_log(self, filepath):
        if filepath not in self.loaded_logs: return
        
        self.current_log_path = filepath
        self.current_engine = self.loaded_logs[filepath]
        self.model.set_engine(self.current_engine, filepath)
        
        self.notes_manager.load_notes_for_file(filepath)
        count = self.current_engine.line_count()
        self.delegate.set_max_line_number(count)
        self.update_window_title()
        self.update_status_bar(f"Shows {count:,} lines")
        
        self.search_results = []
        self.current_match_index = -1
        self.update_scrollbar_range()
        self.v_scrollbar.setValue(0)
        self.filters_dirty_cache = True
        
        # Select in tree
        items = self.log_tree.findItems(os.path.basename(filepath), Qt.MatchExactly)
        for item in items:
            if item.data(0, Qt.UserRole) == filepath:
                self.log_tree.setCurrentItem(item)
                break

        if self.filters: self.recalc_filters()
        else: self.refresh_filter_tree()

    def update_log_tree(self):
        self.log_tree.clear()
        
        for fp in self.log_order:
            item = QTreeWidgetItem(self.log_tree)
            item.setText(0, os.path.basename(fp))
            item.setToolTip(0, fp)
            item.setData(0, Qt.UserRole, fp)
            # Enable dragging, but disable dropping ONTO this item (reordering only)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
            
        if len(self.loaded_logs) > 1:
            self.log_list_dock.show()
            self.log_list_dock.raise_()

    def on_log_reordered(self):
        new_order = []
        root = self.log_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            new_order.append(item.data(0, Qt.UserRole))
        self.log_order = new_order

    def on_log_tree_clicked(self, item, column):
        if not item: return
        path = item.data(0, Qt.UserRole)
        if path:
            self._switch_to_log(path)

    def show_log_list_context_menu(self, pos):
        item = self.log_tree.itemAt(pos)
        menu = QMenu(self)
        ic = "#d4d4d4" if self.is_dark_mode else "#333333"
        
        if item:
            path = item.data(0, Qt.UserRole)
            rem_action = menu.addAction(get_svg_icon("trash", ic), "Remove File")
            rem_action.triggered.connect(lambda: self._remove_log_file(path))
            menu.addSeparator()
        
        clear_action = menu.addAction(get_svg_icon("x-circle", ic), "Clear All")
        clear_action.triggered.connect(self._clear_all_logs)
        menu.exec_(self.log_tree.mapToGlobal(pos))

    def _remove_log_file(self, filepath):
        if filepath in self.loaded_logs:
            # Check for unsaved notes for THIS specific file
            file_notes = {k: v for (fp, k), v in self.notes_manager.notes.items() if fp == filepath}
            if file_notes and self.notes_manager.has_unsaved_changes():
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Unsaved Notes")
                msg_box.setText(f"File '{os.path.basename(filepath)}' has unsaved notes. Save them before removing?")
                msg_box.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                msg_box.setDefaultButton(QMessageBox.Save)
                msg_box.create(); set_windows_title_bar_color(msg_box.winId(), self.is_dark_mode)
                
                res = msg_box.exec()
                if res == QMessageBox.Save:
                    # Save only this file's notes
                    self.notes_manager._save_file_notes(filepath)
                elif res == QMessageBox.Cancel:
                    return

            del self.loaded_logs[filepath]
            self.log_order.remove(filepath)
            self.update_log_tree()
            if self.current_log_path == filepath:
                if self.log_order: self._switch_to_log(self.log_order[0])
                else: self._clear_all_logs()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        icon_color = "#d4d4d4" if self.is_dark_mode else "#333333"
        copy_action = QAction(get_svg_icon("copy", icon_color), "Copy", self)
        copy_action.triggered.connect(self.copy_selection)
        menu.addAction(copy_action)
        menu.addSeparator()
        indexes = self.list_view.selectionModel().selectedIndexes()
        if len(indexes) == 1:
            idx = indexes[0]
            abs_row = self.model.viewport_start + idx.row()
            raw_index = abs_row
            if self.show_filtered_only and self.model.filtered_indices: raw_index = self.model.filtered_indices[abs_row]
            note_action = QAction(get_svg_icon("book-open", icon_color), "Add/Edit Note", self)
            note_action.triggered.connect(lambda: self.notes_manager.add_note(raw_index, "", self.current_log_path))
            menu.addAction(note_action)
        menu.exec_(self.list_view.mapToGlobal(pos))

    def copy_selection(self):
        indexes = self.list_view.selectionModel().selectedIndexes()
        if not indexes: return
        indexes.sort(key=lambda x: x.row())
        text_lines = [self.model.data(idx, Qt.DisplayRole) for idx in indexes if idx.isValid()]
        if text_lines:
            QApplication.clipboard().setText("\n".join(text_lines))
            self.toast.show_message(f"Copied {len(text_lines)} lines")

    def resizeEvent(self, event):
        self.update_scrollbar_range()
        if not self.search_widget.isHidden():
            cw = self.centralWidget()
            self.search_widget.move(cw.width() - self.search_widget.width() - 20, 0)
        super().resizeEvent(event)

    def show_search_bar(self):
        if self.search_widget.isHidden():
            self.search_widget.show(); self.search_widget.raise_(); self.resizeEvent(None)
            self.search_input.setFocus(); self.search_input.lineEdit().selectAll()
        else: self.search_input.setFocus()

    def hide_search_bar(self):
        self.search_widget.hide()
        self.delegate.set_search_query(None, False)
        self.search_results = []
        self.search_info_label.setText("")
        self.list_view.viewport().update()
        self.list_view.setFocus()

    def find_next(self):
        query = self.search_input.currentText()
        if not query: return
        if self.delegate.search_query != query or not self.search_results:
            # If search bar is hidden and results are cleared, don't auto-start search on F3
            if self.search_widget.isHidden(): return
            self._perform_search(query)
            return
        curr_raw = self.selected_raw_index
        idx = bisect.bisect_right(self.search_results, curr_raw)
        if idx >= len(self.search_results):
            if self.chk_wrap.isChecked(): idx = 0; self.toast.show_message("Wrapped to top")
            else: return
        
        # Keep focus in search input if it's already there (e.g. Enter pressed)
        keep_focus = self.search_input.lineEdit().hasFocus() or self.search_input.hasFocus()
        self._jump_to_match(idx, focus_list=not keep_focus)

    def find_previous(self):
        query = self.search_input.currentText()
        if not query: return
        if self.delegate.search_query != query or not self.search_results:
            if self.search_widget.isHidden(): return
            self._perform_search(query)
            return
        curr_raw = self.selected_raw_index
        idx = bisect.bisect_left(self.search_results, curr_raw) - 1
        if idx < 0:
            if self.chk_wrap.isChecked(): idx = len(self.search_results)-1; self.toast.show_message("Wrapped to bottom")
            else: return

        # Keep focus in search input if it's already there
        keep_focus = self.search_input.lineEdit().hasFocus() or self.search_input.hasFocus()
        self._jump_to_match(idx, focus_list=not keep_focus)

    def _perform_search(self, query):
        if not query or not self.current_engine: return
        is_case = self.chk_case.isChecked()
        results = self.current_engine.search(query, False, is_case)
        
        # Filter results if viewing filtered only
        if self.show_filtered_only and self.model.filtered_indices:
            visible_set = set(self.model.filtered_indices)
            results = [r for r in results if r in visible_set]
            
        self.search_results = results
        self.delegate.set_search_query(query, is_case)
        self.list_view.viewport().update()
        
        if results: 
            # Determine start index based on current selection
            curr_raw = self.selected_raw_index
            # Find the first match that is >= curr_raw (inclusive if we are exactly on a match? usually next means after)
            # Actually, for initial search (e.g. typing), usually we want the first match *visible* or *after cursor*.
            # If we are already on a line, let's search forward from there.
            idx = bisect.bisect_left(results, curr_raw)
            if idx >= len(results): 
                idx = 0 # Wrap to start if no matches after cursor
            
            # Check focus before jumping
            keep_focus = self.search_input.lineEdit().hasFocus() or self.search_input.hasFocus()
            self._jump_to_match(idx, focus_list=not keep_focus)
        else: 
            self.search_info_label.setText("No results")

    def on_search_case_changed(self):
        query = self.search_input.currentText()
        if query: self._perform_search(query)

    def on_notes_updated(self): self.list_view.viewport().update()

    def jump_to_raw_index(self, raw_index, focus_list=True):
        view_row = raw_index
        if self.show_filtered_only and self.model.filtered_indices:
             idx = bisect.bisect_left(self.model.filtered_indices, raw_index)
             if idx < len(self.model.filtered_indices) and self.model.filtered_indices[idx] == raw_index: view_row = idx
             else: return # Target not visible
             
        vp_size = self.calculate_viewport_size()
        target_scroll = max(0, view_row - (vp_size // 2))
        self.v_scrollbar.setValue(target_scroll)
        
        # Force immediate update of model viewport
        self.on_scrollbar_value_changed(target_scroll)
        QApplication.processEvents()
        
        # Calculate relative index in the current viewport
        rel_row = view_row - target_scroll
        if 0 <= rel_row < self.model.rowCount():
            index = self.model.index(rel_row, 0)
            if index.isValid():
                self.list_view.setCurrentIndex(index)
                self.list_view.scrollTo(index, QAbstractItemView.PositionAtCenter)
                if focus_list: self.list_view.setFocus()
                self.selected_raw_index = raw_index # Ensure state is synced

    def _jump_to_match(self, result_index, focus_list=True):
        if not self.search_results or result_index < 0 or result_index >= len(self.search_results): return
        raw_row = self.search_results[result_index]
        self.jump_to_raw_index(raw_row, focus_list)
        self.search_info_label.setText(f"{result_index + 1} / {len(self.search_results)}")

    def on_filter_tree_reordered(self):
        new_f = []
        root = self.filter_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            idx = item.data(0, Qt.UserRole)
            new_f.append(self.filters[idx])
            item.setData(0, Qt.UserRole, i)
        self.filters = new_f
        self.filters_modified = True; self.filters_dirty_cache = True
        self.update_window_title(); self.recalc_filters()

    def refresh_filter_tree(self):
        self.filter_tree.blockSignals(True)
        self.filter_tree.clear()
        for i, flt in enumerate(self.filters):
            prefix = (" [x]" if flt["is_exclude"] else "") + (" [R]" if flt["is_regex"] else "")
            item = QTreeWidgetItem(self.filter_tree)
            item.setFlags((item.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsDropEnabled)
            item.setCheckState(0, Qt.Checked if flt["enabled"] else Qt.Unchecked)
            item.setText(1, f"{prefix} {flt['text']}".strip())
            item.setText(2, str(flt.get("hits", 0)))
            item.setData(0, Qt.UserRole, i)
            fg = adjust_color_for_theme(flt["fg_color"], False, self.is_dark_mode)
            bg = adjust_color_for_theme(flt["bg_color"], True, self.is_dark_mode)
            item.setForeground(1, QColor(fg)); item.setBackground(1, QColor(bg))
        self.filter_tree.blockSignals(False)

    def on_filter_item_clicked(self, item, column):
        if item: self.selected_filter_index = item.data(0, Qt.UserRole)

    def on_filter_item_changed(self, item, column):
        if column == 0 and item:
            idx = item.data(0, Qt.UserRole)
            if 0 <= idx < len(self.filters):
                st = (item.checkState(0) == Qt.Checked)
                if self.filters[idx]["enabled"] != st:
                    self.filters[idx]["enabled"] = st
                    self.filters_modified = True; self.filters_dirty_cache = True
                    self.update_window_title(); self.recalc_filters()

    def on_log_double_clicked(self, index):
        txt = self.model.data(index, Qt.DisplayRole)
        if txt: self.add_filter_dialog(initial_text=txt.strip())

    def edit_selected_filter(self):
        item = self.filter_tree.currentItem()
        if not item: return
        idx = item.data(0, Qt.UserRole)
        dialog = FilterDialog(self, self.filters[idx])
        if dialog.exec():
            self.filters[idx].update(dialog.get_data())
            self.filters_modified = True; self.filters_dirty_cache = True
            self.update_window_title(); self.refresh_filter_tree(); self.recalc_filters()

    def add_filter_dialog(self, initial_text=""):
        dialog = FilterDialog(self)
        if initial_text: dialog.pattern_edit.setText(initial_text)
        if dialog.exec():
            flt = dialog.get_data(); flt["hits"] = 0
            self.filters.append(flt)
            self.filters_modified = True; self.filters_dirty_cache = True
            self.update_window_title(); self.refresh_filter_tree(); self.recalc_filters()

    def remove_filter(self):
        item = self.filter_tree.currentItem()
        if not item: return
        del self.filters[item.data(0, Qt.UserRole)]
        self.filters_modified = True; self.filters_dirty_cache = True
        self.update_window_title(); self.refresh_filter_tree(); self.recalc_filters()

    def move_filter_top(self):
        item = self.filter_tree.currentItem()
        if not item: return
        idx = item.data(0, Qt.UserRole)
        if idx > 0:
            self.filters.insert(0, self.filters.pop(idx))
            self.filters_modified = True; self.filters_dirty_cache = True
            self.update_window_title(); self.refresh_filter_tree(); self.recalc_filters()

    def move_filter_bottom(self):
        item = self.filter_tree.currentItem()
        if not item: return
        idx = item.data(0, Qt.UserRole)
        if idx < len(self.filters) - 1:
            self.filters.append(self.filters.pop(idx))
            self.filters_modified = True; self.filters_dirty_cache = True
            self.update_window_title(); self.refresh_filter_tree(); self.recalc_filters()

    def show_filter_menu(self, pos):
        item = self.filter_tree.itemAt(pos); menu = QMenu(self)
        ic = "#d4d4d4" if self.is_dark_mode else "#333333"
        menu.addAction(get_svg_icon("plus", ic), "Add Filter", self.add_filter_dialog)
        if item:
            idx = item.data(0, Qt.UserRole)
            menu.addSeparator()
            menu.addAction(get_svg_icon("search", ic), "Edit Filter", self.edit_selected_filter)
            menu.addAction(get_svg_icon("trash", ic), "Remove Filter", self.remove_filter)
            menu.addSeparator()
            menu.addAction(get_svg_icon("chevron-up", ic), "Move to Top", self.move_filter_top)
            menu.addAction(get_svg_icon("chevron-down", ic), "Move to Bottom", self.move_filter_bottom)
            menu.addSeparator()
            en = self.filters[idx]["enabled"]
            act = menu.addAction("Disable" if en else "Enable")
            def togg(): self.filters[idx]["enabled"] = not en; self.filters_dirty_cache = True; self.refresh_filter_tree(); self.recalc_filters()
            act.triggered.connect(togg)
        menu.exec_(self.filter_tree.mapToGlobal(pos))

    def import_filters(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Filters", self.settings.value("last_filter_dir", ""), "TAT (*.tat);;All (*)")
        if path:
            self.settings.setValue("last_filter_dir", os.path.dirname(path))
            loaded = load_tat_filters(path)
            if loaded:
                self.current_filter_file = path  # Update current filter file path
                self.filters = loaded; self.filters_modified = False; self.filters_dirty_cache = True
                self.update_window_title(); self.refresh_filter_tree(); self.recalc_filters()
                
                # Auto-show Filter Panel when filters are loaded
                if self.filter_dock.isHidden():
                    self.filter_dock.show()
                    self.filter_dock.raise_()

    def closeEvent(self, event):
        # Save window state and geometry
        self.settings.setValue("window_geometry", self.saveGeometry())
        self.settings.setValue("window_state", self.saveState())

        # Helper to prompt user
        def prompt_save_changes(title, text):
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle(title)
            msg_box.setText(text)
            msg_box.setIcon(QMessageBox.Question)
            msg_box.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            msg_box.setDefaultButton(QMessageBox.Save)
            
            msg_box.create()
            set_windows_title_bar_color(msg_box.winId(), self.is_dark_mode)
            return msg_box.exec()

        # 1. Check Filters
        if self.filters_modified:
            reply = prompt_save_changes("Unsaved Changes", "Filters have been modified. Do you want to save changes?")
            if reply == QMessageBox.Save:
                saved = False
                if self.current_filter_file:
                    saved = save_tat_filters(self.current_filter_file, self.filters)
                else:
                    self.save_filters_as()
                    saved = not self.filters_modified # Check flag to verify save success

                if saved:
                    self.filters_modified = False
                else:
                    event.ignore(); return
            elif reply == QMessageBox.Discard:
                pass # Proceed
            else:
                event.ignore(); return # Cancel

        # 2. Check Notes
        if self.notes_manager.has_unsaved_changes():
            reply = prompt_save_changes("Unsaved Notes", "Notes have been modified. Do you want to save them for all files?")
            if reply == QMessageBox.Save:
                self.notes_manager.save_all_notes()
                # save_all_notes handles its own errors and sets dirty=False on success
                if self.notes_manager.has_unsaved_changes(): # Still dirty means save failed or cancelled
                     event.ignore(); return
            elif reply == QMessageBox.Discard:
                pass
            else:
                event.ignore(); return

        event.accept()

    def quick_save_filters(self):
        if self.current_filter_file:
            if save_tat_filters(self.current_filter_file, self.filters):
                self.filters_modified = False; self.update_window_title(); self.toast.show_message("Saved")
        else: self.save_filters_as()

    def save_filters_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Filters As", self.settings.value("last_filter_dir", ""), "TAT (*.tat);;All (*)")
        if path:
            self.settings.setValue("last_filter_dir", os.path.dirname(path))
            if save_tat_filters(path, self.filters):
                self.current_filter_file = path; self.filters_modified = False; self.update_window_title(); self.toast.show_message("Saved")

    def export_notes_to_text(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Notes", self.settings.value("last_note_export_dir", ""), "Text (*.txt);;All (*)")
        if path:
            self.settings.setValue("last_note_export_dir", os.path.dirname(path))
            self.notes_manager.export_to_text(path)

    def update_window_title(self):
        p = [os.path.basename(self.current_log_path)] if self.current_log_path else []
        if self.current_filter_file: p.append(("*" if self.filters_modified else "") + os.path.basename(self.current_filter_file))
        elif self.filters_modified: p.append("*Unsaved")
        p.append(f"{self.APP_NAME} {self.VERSION}")
        self.setWindowTitle(" - ".join(p))

    def calculate_viewport_size(self):
        h = self.list_view.viewport().height(); rh = QFontMetrics(self.list_view.font()).height()
        return (h // (rh if rh > 0 else 20)) + 100

    def on_view_selection_changed(self, curr, prev):
        if self.is_scrolling or not curr.isValid(): return
        abs_row = self.model.viewport_start + curr.row()
        raw = abs_row
        if self.show_filtered_only and self.model.filtered_indices:
            if abs_row < len(self.model.filtered_indices): raw = self.model.filtered_indices[abs_row]
        self.selected_raw_index = raw

    def update_scrollbar_range(self):
        if not self.current_engine: return
        total = 0
        if self.show_filtered_only:
            total = len(self.model.filtered_indices) if self.model.filtered_indices is not None else 0
        else:
            total = self.current_engine.line_count()
            
        vp = self.calculate_viewport_size()
        self.v_scrollbar.setRange(0, max(0, total - vp)); self.v_scrollbar.setPageStep(vp)
        self.on_scrollbar_value_changed(self.v_scrollbar.value())

    def navigate_filter_hit(self, reverse=False):
        if not self.current_engine or not self.model.tag_codes: return
        
        # Ensure we have a selected filter index, fallback to current tree item if needed
        if self.selected_filter_index < 0:
            item = self.filter_tree.currentItem()
            if item:
                self.selected_filter_index = item.data(0, Qt.UserRole)
        
        if self.selected_filter_index < 0: return
        
        target_code = -1; curr_j = 0

        for i, f in enumerate(self.filters):
            if f["enabled"]:
                if i == self.selected_filter_index: target_code = curr_j + 2; break
                curr_j += 1
        if target_code == -1: return
        start = self.selected_raw_index if self.selected_raw_index != -1 else self.model.viewport_start
        found = -1
        if reverse:
            for r in range(start - 1, -1, -1):
                if self.model.tag_codes[r] == target_code: found = r; break
        else:
            for r in range(start + 1, len(self.model.tag_codes)):
                if self.model.tag_codes[r] == target_code: found = r; break
        if found != -1: self.selected_raw_index = found; self.jump_to_raw_index(found)

    def recalc_filters(self, force_color_update=False):
        if not self.current_engine: return
        if self.filters_dirty_cache:
            rust_f = [(f["text"], f["is_regex"], f["is_exclude"], False, i) for i, f in enumerate(self.filters) if f["enabled"]]
            try:
                res = self.current_engine.filter(rust_f)
                self.cached_filter_results = (res, rust_f); self.filters_dirty_cache = False
            except: return
        if self.cached_filter_results:
            res, rust_f = self.cached_filter_results
            tag_codes, filtered_indices, subset_counts = res[0], res[1], res[2]
            for j, rf in enumerate(rust_f):
                if j < len(subset_counts): self.filters[rf[4]]["hits"] = subset_counts[j]
            palette = {j+2: (adjust_color_for_theme(self.filters[rf[4]]["fg_color"], False, self.is_dark_mode),
                             adjust_color_for_theme(self.filters[rf[4]]["bg_color"], True, self.is_dark_mode))
                       for j, rf in enumerate(rust_f)}
            self.model.update_filter_result(tag_codes, palette, filtered_indices if self.show_filtered_only else None)
            self.update_scrollbar_range()
            if not force_color_update: self.refresh_filter_tree()
            self.update_status_bar(f"Shows {len(filtered_indices if self.show_filtered_only else range(self.current_engine.line_count())):,} lines")

    def show_goto_dialog(self):
        total = len(self.model.filtered_indices) if self.show_filtered_only else self.current_engine.line_count()
        if total <= 0: return
        val, ok = QInputDialog.getInt(self, "Go to Line", f"Line (1-{total}):", 1, 1, total)
        if ok:
            raw = self.model.filtered_indices[val-1] if self.show_filtered_only else val-1
            self.jump_to_raw_index(raw)

    def show_shortcuts(self):
        shortcuts = [("General", ""), ("Ctrl + O", "Open Log File"), ("Ctrl + Q", "Exit Application"), ("", ""), ("View & Navigation", ""), ("Ctrl + F", "Open Find Bar"), ("Esc", "Close Find Bar / Clear Selection"), ("Ctrl + H", "Toggle Show Filtered Only"), ("F2 / F3", "Find Previous / Next"), ("Ctrl + Left / Right", "Navigate Filter Hits (Selected Filter)"), ("Home / End", "Jump to Start / End of Log"), ("", ""), ("Log View", ""), ("Double-Click", "Create Filter from selected text"), ("'C' key", "Add / Edit Note for current line"), ("Ctrl + C", "Copy selected lines"), ("", ""), ("Filters", ""), ("Delete", "Remove selected filter"), ("Double-Click", "Edit filter properties"), ("Space", "Toggle filter enabled/disabled")]
        dialog = QDialog(self); dialog.setWindowTitle("Keyboard Shortcuts"); dialog.resize(550, 600); layout = QVBoxLayout(dialog)
        tree = QTreeWidget(); tree.setHeaderLabels(["Key", "Description"]); tree.setRootIsDecorated(False); tree.setAlternatingRowColors(True)
        for k, d in shortcuts:
            item = QTreeWidgetItem(tree)
            if not k and not d: continue
            elif not d:
                item.setText(0, k); bg = QColor(60,60,60) if self.is_dark_mode else QColor(230,230,230)
                item.setBackground(0, bg); item.setBackground(1, bg); f = item.font(0); f.setBold(True); item.setFont(0, f)
            else: item.setText(0, k); item.setText(1, d)
        tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents); tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(tree); btn = QPushButton("Close"); btn.clicked.connect(dialog.accept); layout.addWidget(btn); set_windows_title_bar_color(dialog.winId(), self.is_dark_mode); dialog.exec()

    def show_about(self):
        msg_box = QMessageBox(self); msg_box.setWindowTitle("About"); msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(f"<h3>{self.APP_NAME} {self.VERSION}</h3><p>A high-performance log analysis tool built with PySide6 and Rust extension.</p><p>Developer: Gary Hsieh</p>")
        msg_box.setStandardButtons(QMessageBox.Ok); set_windows_title_bar_color(msg_box.winId(), self.is_dark_mode); msg_box.exec()

    def open_documentation(self):
        path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "Doc", f"Log_Analyzer_{self.VERSION}_Docs_EN.html"))
        if os.path.exists(path): import webbrowser; webbrowser.open(f"file://{path}")

    def on_scrollbar_value_changed(self, value):
        self.is_scrolling = True
        try:
            self.model.set_viewport(value, self.calculate_viewport_size())
        finally:
            self.is_scrolling = False

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.settings.setValue("dark_mode", self.is_dark_mode)
        self.apply_theme()
        self.refresh_filter_tree()
        if self.current_engine and self.filters:
            self.recalc_filters(True)

    def update_status_bar(self, message):
        self.status_label.setText(message)

    def _set_windows_title_bar_color(self, is_dark):
        if sys.platform == "win32":
            set_windows_title_bar_color(self.winId(), is_dark)

    def close_app(self):
        self.close()


