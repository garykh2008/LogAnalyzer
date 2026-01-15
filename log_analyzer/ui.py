from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QListView,
                               QLabel, QFileDialog, QMenu, QStatusBar, QAbstractItemView, QApplication,
                               QHBoxLayout, QToolButton, QSizePolicy, QDockWidget, QTreeWidget, QTreeWidgetItem, QHeaderView,
                               QMessageBox, QPushButton, QStackedLayout, QFrame,
                               QSpinBox, QSizeGrip)
from PySide6.QtGui import QAction, QFont, QColor, QKeySequence, QIcon, QFontMetrics, QFontInfo
from PySide6.QtCore import Qt, QSettings, QTimer, QEvent, QSize, QItemSelectionModel, QRect
from .models import LogModel
from .theme_manager import ThemeManager
from .controllers import LogController, FilterController, SearchController

from .toast import Toast
from .delegates import LogDelegate, FilterDelegate
from .filter_dialog import FilterDialog

from .notes_manager import NotesManager
from .resources import get_svg_icon
from .utils import adjust_color_for_theme, set_windows_title_bar_color
import os
import sys
import bisect

from .components import CustomTitleBar, DimmerOverlay, BadgeToolButton, ClickableLabel, LoadingSpinner, SearchOverlay
from .modern_dialog import ModernDialog
from .modern_messagebox import ModernMessageBox
from .scrollbar_map import SearchScrollBar
from .preferences_dialog import PreferencesDialog
from .config import get_config


class FilterTreeWidget(QTreeWidget):
    def __init__(self, on_drop_callback=None, parent=None):
        super().__init__(parent)
        self.on_drop_callback = on_drop_callback

    def dropEvent(self, event):
        super().dropEvent(event)
        if self.on_drop_callback:
            self.on_drop_callback()


class GoToLineDialog(ModernDialog):
    def __init__(self, parent=None, max_line=1):
        super().__init__(parent, title="Go to Line", fixed_size=(300, 220))

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(f"Enter line number (1 - {max_line:,}):")
        layout.addWidget(label)

        self.spin_box = QSpinBox()
        self.spin_box.setRange(1, max_line)
        self.spin_box.setValue(1)
        self.spin_box.setButtonSymbols(QSpinBox.NoButtons)
        self.spin_box.setFixedHeight(32)
        layout.addWidget(self.spin_box)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_ok = QPushButton("Go")
        self.btn_ok.setDefault(True)
        # Assuming we are in dark mode by default or we can check parent.is_dark_mode if passed
        # For simplicity, we use white for primary button icon as per CSS
        self.btn_ok.setIcon(get_svg_icon("arrow-right", "#ffffff"))
        self.btn_ok.setLayoutDirection(Qt.RightToLeft) # Icon on the right
        self.btn_ok.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)

        self.setContentLayout(layout)

        self.spin_box.setFocus()
        self.spin_box.selectAll()

    def get_line(self):
        return self.spin_box.value()


class MainWindow(QMainWindow):
    VERSION = "V2.1"
    APP_NAME = "Log Analyzer"

    def __init__(self):
        super().__init__()

        # --- Controllers Initialization (MUST BE FIRST) ---
        self.log_controller = LogController()
        self.filter_controller = FilterController()
        self.search_controller = SearchController()

        self.log_controller.log_loaded.connect(self.on_log_loaded)
        self.log_controller.log_closed.connect(self.on_log_closed)

        self.filter_controller.filters_changed.connect(self.on_filters_changed)
        self.filter_controller.filter_results_ready.connect(self.on_filter_results_ready)

        self.search_controller.search_results_ready.connect(self.on_search_results_ready)

        # Frameless Window Setup
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)

        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "loganalyzer.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(1200, 800)

        self.settings = QSettings("LogAnalyzer", "QtApp")
        self.config = get_config() # Initialize ConfigManager
        self.is_dark_mode = self.settings.value("dark_mode", False, type=bool)
        self.setAcceptDrops(True)
        self.last_status_message = "Ready"
        self.current_log_path = None

        # --- Custom Title Bar Integration ---
        # 1. Force creation/retrieval of the native QMenuBar first
        # We store it in self.custom_menu_bar to prevent _create_menu from calling self.menuBar() again
        # (which would create a NEW one and replace our custom title bar as the menu widget)
        self.custom_menu_bar = self.menuBar()

        # 2. Create Custom Title Bar
        self.title_bar = CustomTitleBar(self)
        self.title_bar.setObjectName("title_bar")

        # 3. Inject native QMenuBar into Custom Title Bar
        self.title_bar.layout.insertWidget(1, self.custom_menu_bar, 0, Qt.AlignVCenter)

        # 4. Set Custom Title Bar as the MainWindow's Menu Widget
        self.setMenuWidget(self.title_bar)

        self.log_states = {} # {path: {"scroll": val, "selected_raw": idx}}

        self.show_filtered_only = False

        self.selected_filter_index = -1
        self.selected_raw_index = -1
        self.is_scrolling = False
        self._suppress_search_jump = False

        # Dock Configuration
        if sys.platform == "linux":
            self.setDockOptions(QMainWindow.AllowTabbedDocks)
        else:
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
        self.notes_manager.export_requested.connect(self.export_notes_to_text)
        self.notes_manager.message_requested.connect(lambda msg, t="info": self.toast.show_message(msg, type_str=t))

        self.list_view.setUniformItemSizes(False) # Allow variable widths for horizontal scrolling


        # --- Activity Bar ---
        self.activity_bar = self.addToolBar("Activity Bar")
        self.activity_bar.setObjectName("activity_bar")
        self.activity_bar.setMovable(False)
        self.activity_bar.setAllowedAreas(Qt.LeftToolBarArea)
        self.activity_bar.setOrientation(Qt.Vertical)
        self.activity_bar.setIconSize(QSize(28, 28))
        self.activity_bar.setContextMenuPolicy(Qt.PreventContextMenu)
        self.addToolBar(Qt.LeftToolBarArea, self.activity_bar)

        self.btn_side_loglist = QToolButton()
        self.btn_side_loglist.setCheckable(True)
        self.btn_side_loglist.setFixedSize(48, 48)
        self.btn_side_loglist.setToolTip("Log Files (Ctrl+Shift+L)")
        self.btn_side_loglist.clicked.connect(lambda: self.toggle_sidebar(2))

        self.btn_side_filter = BadgeToolButton()
        self.btn_side_filter.setCheckable(True)
        self.btn_side_filter.setFixedSize(48, 48)
        self.btn_side_filter.setToolTip("Filters (Ctrl+Shift+F)")
        self.btn_side_filter.clicked.connect(lambda: self.toggle_sidebar(0))

        self.btn_side_notes = BadgeToolButton()
        self.btn_side_notes.setCheckable(True)
        self.btn_side_notes.setFixedSize(48, 48)
        self.btn_side_notes.setToolTip("Notes (Ctrl+Shift+N)")
        self.btn_side_notes.clicked.connect(lambda: self.toggle_sidebar(1))

        self.activity_bar.addWidget(self.btn_side_loglist)
        self.activity_bar.addWidget(self.btn_side_filter)
        self.activity_bar.addWidget(self.btn_side_notes)

        # Add Spacer and Settings Button
        empty = QWidget()
        empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.activity_bar.addWidget(empty)

        self.btn_settings = QToolButton()
        self.btn_settings.setFixedSize(48, 48)
        self.btn_settings.setToolTip("Settings")
        self.btn_settings.clicked.connect(self.open_preferences)
        self.activity_bar.addWidget(self.btn_settings)

        # Feature configuration based on platform
        dock_features = QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable
        if sys.platform == "linux":
            dock_features = QDockWidget.NoDockWidgetFeatures

        # --- Log List Dock ---
        self.log_list_dock = QDockWidget("LOG FILES", self)
        self.log_list_dock.setObjectName("LogListDock")
        self.log_list_dock.setFeatures(dock_features)
        self.log_list_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)

        # Custom Title Bar
        self.log_title_bar = QWidget()
        log_title_layout = QHBoxLayout(self.log_title_bar)
        log_title_layout.setContentsMargins(10, 4, 4, 4)
        log_title_layout.setSpacing(4)

        self.log_title_label = QLabel("LOG FILES")
        font = QFont("Inter SemiBold")
        if not QFontInfo(font).exactMatch() and QFontInfo(font).family() != "Inter":
             font.setFamily("Segoe UI")
        font.setBold(True)
        self.log_title_label.setFont(font)

        self.btn_open_log = QToolButton()
        self.btn_open_log.setToolTip("Open Log Files (Ctrl+O)")
        self.btn_open_log.setFixedSize(26, 26)
        self.btn_open_log.clicked.connect(self.open_file_dialog)

        self.btn_clear_logs = QToolButton()
        self.btn_clear_logs.setToolTip("Clear All Logs")
        self.btn_clear_logs.setFixedSize(26, 26)
        self.btn_clear_logs.clicked.connect(lambda: self._clear_all_logs())

        log_title_layout.addWidget(self.log_title_label)
        log_title_layout.addStretch()
        log_title_layout.addWidget(self.btn_open_log)
        log_title_layout.addWidget(self.btn_clear_logs)

        self.log_list_dock.setTitleBarWidget(self.log_title_bar)

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
        self.filter_dock.setFeatures(dock_features)
        self.filter_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)

        # Custom Title Bar
        self.filter_title_bar = QWidget()
        filter_title_layout = QHBoxLayout(self.filter_title_bar)
        filter_title_layout.setContentsMargins(10, 4, 4, 4)
        filter_title_layout.setSpacing(4)

        self.filter_title_label = QLabel("FILTERS")
        font = QFont("Inter SemiBold")
        if not QFontInfo(font).exactMatch() and QFontInfo(font).family() != "Inter":
             font.setFamily("Segoe UI")
        font.setBold(True)
        self.filter_title_label.setFont(font)

        self.btn_add_filter = QToolButton()
        self.btn_add_filter.setToolTip("Add Filter")
        self.btn_add_filter.setFixedSize(26, 26)
        self.btn_add_filter.clicked.connect(lambda: self.add_filter_dialog())

        filter_title_layout.addWidget(self.filter_title_label)
        filter_title_layout.addStretch()
        filter_title_layout.addWidget(self.btn_add_filter)

        self.filter_dock.setTitleBarWidget(self.filter_title_bar)

        self.filter_tree = FilterTreeWidget(on_drop_callback=self.on_filter_tree_reordered)
        self.filter_delegate = FilterDelegate(self.filter_tree)
        self.filter_tree.setItemDelegate(self.filter_delegate)
        self.filter_tree.setIndentation(0)
        self.filter_tree.setHeaderHidden(True)

        self.filter_tree.setColumnCount(3)
        # self.filter_tree.setHeaderLabels(["", "Pattern", "Hits  "])

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
        self.notes_dock.setFeatures(dock_features)
        self.notes_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.notes_dock)
        self.notes_dock.visibilityChanged.connect(lambda visible: self.btn_side_notes.setChecked(visible))
        self.notes_dock.topLevelChanged.connect(lambda floating: set_windows_title_bar_color(self.notes_dock.winId(), self.is_dark_mode))
        self.notes_dock.hide()

        # Virtual Viewport Setup
        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.v_scrollbar = SearchScrollBar(Qt.Vertical)
        self.v_scrollbar.valueChanged.connect(self.on_scrollbar_value_changed)
        self.list_view.installEventFilter(self)

        self.list_view.selectionModel().currentChanged.connect(self.on_view_selection_changed)

        # Font is set via self.apply_editor_font call later in __init__

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
        self.welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(self.welcome_widget)
        welcome_layout.setAlignment(Qt.AlignCenter)
        welcome_layout.setSpacing(20)

        self.welcome_icon = QLabel()
        self.welcome_icon.setFixedSize(80, 80)
        self.welcome_icon.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(self.welcome_icon, 0, Qt.AlignCenter)

        self.welcome_label = QLabel("Drag & Drop Log File Here\nor use File > Open Log")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        font_welcome = QFont("Inter", 14)
        if not QFontInfo(font_welcome).exactMatch() and QFontInfo(font_welcome).family() != "Inter":
            font_welcome = QFont("Segoe UI", 14)
        self.welcome_label.setFont(font_welcome)
        self.welcome_label.setStyleSheet("color: #888888;")
        welcome_layout.addWidget(self.welcome_label, 0, Qt.AlignCenter)

        self.central_stack.addWidget(self.welcome_widget)

        # Page 1: List View Container
        list_container = QWidget(self.central_area)
        list_layout = QHBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)
        list_layout.addWidget(self.list_view)
        list_layout.addWidget(self.v_scrollbar)
        self.central_stack.addWidget(list_container)

        self.central_stack.setCurrentIndex(0)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.setSizeGripEnabled(False)

        # Status Bar Content
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(10, 0, 10, 0)
        status_layout.setSpacing(10)

        # Left Side: Spinner & Main Message
        self.spinner = LoadingSpinner(size=14, color="#3794ff")
        self.status_message_label = QLabel("Ready")

        # Right Side: Interactive Sections
        self.status_mode_label = ClickableLabel("Full Log")
        self.status_mode_label.setToolTip("Toggle Filtered View (Ctrl+H)")
        self.status_mode_label.clicked.connect(self.toggle_show_filtered_only_from_status)

        self.status_count_label = ClickableLabel("0 lines")
        self.status_count_label.setToolTip("Go to Line (Ctrl+G)")
        self.status_count_label.clicked.connect(self.show_goto_dialog)

        self.status_pos_label = ClickableLabel("Ln 1")
        self.status_pos_label.setToolTip("Current Line")

        self.status_enc_label = ClickableLabel("UTF-8")
        self.status_enc_label.setToolTip("File Encoding")

        # Add widgets
        status_layout.addWidget(self.spinner)
        status_layout.addWidget(self.status_message_label)
        status_layout.addStretch()

        # Helper to add separator
        def add_sep():
            sep = QFrame()
            sep.setFrameShape(QFrame.VLine)
            sep.setFrameShadow(QFrame.Sunken)
            sep.setFixedHeight(14)
            sep.setStyleSheet("color: gray;")
            # We will style this properly in theme manager later or use a simple widget
            status_layout.addWidget(sep)

        status_layout.addWidget(self.status_mode_label)
        status_layout.addWidget(self.status_count_label)
        status_layout.addWidget(self.status_pos_label)
        status_layout.addWidget(self.status_enc_label)

        self.status_bar.addWidget(status_container, 1)

        # Add Custom Resize Grip for Frameless Window
        self.size_grip = QSizeGrip(self)
        self.status_bar.addPermanentWidget(self.size_grip)

        self._create_menu()
        self.custom_menu_bar.installEventFilter(self)

        # 1. Restore saved geometry and layout state (remembers positions)
        # Manual geometry handling to support correct "Normal" size restoration
        rect = self.settings.value("window_rect")
        if rect and isinstance(rect, QRect):
            self.setGeometry(rect)
        else:
            self.resize(1200, 800)

        self.last_normal_rect = self.geometry()

        self.should_maximize = self.settings.value("is_maximized", False, type=bool)

        has_saved_state = False
        if self.settings.value("window_state"):
            has_saved_state = self.restoreState(self.settings.value("window_state"))

        # 2. Set default Tabify relationship ONLY if no saved state exists
        if not has_saved_state:
            self.tabifyDockWidget(self.log_list_dock, self.filter_dock)
            self.tabifyDockWidget(self.filter_dock, self.notes_dock)

        # 3. Force all docks hidden on startup (overrides visibility from restoreState)
        self.log_list_dock.hide()
        self.filter_dock.hide()
        self.notes_dock.hide()

        # Overlay Widgets (Initialize LAST to be on top)
        self.dimmer = DimmerOverlay(self)
        self.toast = Toast(self)

        # Search Overlay
        self.search_overlay = SearchOverlay(self.central_area)
        self.search_overlay.findNext.connect(self.find_next)
        self.search_overlay.findPrev.connect(self.find_previous)
        self.search_overlay.searchChanged.connect(self._perform_search)
        self.search_overlay.closed.connect(self._on_search_closed)

        # Config Connections
        self.config.editorFontChanged.connect(self.apply_editor_font)
        self.config.showLineNumbersChanged.connect(self.toggle_line_numbers)
        self.config.editorLineSpacingChanged.connect(self.apply_line_spacing)
        self.config.themeChanged.connect(self.on_config_theme_changed)
        self.config.uiFontSizeChanged.connect(lambda s: self.apply_theme())
        self.config.uiFontFamilyChanged.connect(lambda f: self.apply_theme())

        # Apply initial config state
        self.apply_editor_font(self.config.editor_font_family, self.config.editor_font_size)
        self.toggle_line_numbers(self.config.show_line_numbers)
        self.apply_line_spacing(self.config.editor_line_spacing)

        self.apply_theme()

    @property
    def current_engine(self):
        return self.log_controller.current_engine

    @property
    def loaded_logs(self):
        return self.log_controller.loaded_logs

    @property
    def log_order(self):
        return self.log_controller.log_order

    @property
    def search_results(self):
        return self.search_controller.search_results

    @property
    def search_history(self):
        return self.search_controller.history

    @property
    def filters(self):
        return self.filter_controller.filters

    def open_preferences(self):
        dialog = PreferencesDialog(self)
        dialog.exec()

    def on_filters_changed(self):
        self.refresh_filter_tree()
        self.update_window_title()
        # Invalidate per-file cache logic?
        # Controller manages global cache dirty state.
        # But we also have `log_states[path]["filter_cache"]`.
        # When filters change, we should invalidate ALL per-file caches.
        self._invalidate_all_filter_caches(mark_modified=False) # Controller marks modified already
        self.recalc_filters()

    def on_filter_results_ready(self, res, rust_f):
        tag_codes, filtered_indices = res[0], res[1]

        # UI calculates colors
        palette = {j+2: (adjust_color_for_theme(self.filters[rf[4]]["fg_color"], False, self.is_dark_mode),
                         adjust_color_for_theme(self.filters[rf[4]]["bg_color"], True, self.is_dark_mode))
                   for j, rf in enumerate(rust_f)}

        self.model.update_filter_result(tag_codes, palette, filtered_indices if self.show_filtered_only else None)
        self.update_scrollbar_range()

        # Update filtered search results based on new visibility
        self.update_filtered_search_results()

        self.refresh_filter_tree()

        # Cache the result for the current file
        if self.current_log_path:
            if self.current_log_path not in self.log_states:
                self.log_states[self.current_log_path] = {}
            self.log_states[self.current_log_path]["filter_cache"] = (res, rust_f)

        count = len(filtered_indices) if filtered_indices else 0
        if self.show_filtered_only:
             self.toast.show_message(f"Filtered: {count:,} lines")

        self.update_status_bar()

        enabled_count = sum(1 for f in self.filters if f["enabled"])
        self.btn_side_filter.set_badge(enabled_count)

        # Refresh tree to show hit counts (controller updated them)
        self.refresh_filter_tree()

    def apply_editor_font(self, family, size):
        # Update via stylesheet to override global app stylesheet inheritance
        self.list_view.setStyleSheet(f"font-family: \"{family}\"; font-size: {size}pt;")

        font = QFont(family, size)
        font.setStyleHint(QFont.Monospace)
        self.list_view.setFont(font)
        # Update layout since row heights might change
        self.list_view.viewport().update()
        self.update_scrollbar_range()

    def toggle_line_numbers(self, show):
        self.delegate.set_show_line_numbers(show)
        self.list_view.viewport().update()

    def _create_menu(self):
        # Use the menu bar we already embedded in the custom title bar
        menu_bar = self.custom_menu_bar

        file_menu = menu_bar.addMenu("&File")
        ThemeManager.apply_menu_theme(file_menu)
        self.open_action = QAction("&Open Log...", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(self.open_action)

        self.recent_menu = file_menu.addMenu("Open Recent")
        ThemeManager.apply_menu_theme(self.recent_menu)
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
        ThemeManager.apply_menu_theme(edit_menu)
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
        ThemeManager.apply_menu_theme(view_menu)
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
        ThemeManager.apply_menu_theme(notes_menu)
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
        ThemeManager.apply_menu_theme(help_menu)
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

        mode_str = "Filtered View" if self.show_filtered_only else "Full Log View"
        count = 0
        if self.show_filtered_only and self.model.filtered_indices:
            count = len(self.model.filtered_indices)
        elif not self.show_filtered_only and self.current_engine:
            count = self.current_engine.line_count()
        self.toast.show_message(f"{mode_str}: {count:,} lines")

        # Trigger re-search to update results count and matches for visibility change
        if hasattr(self, 'search_overlay'):
            query = self.search_overlay.input.text()
            if query and not self.search_overlay.isHidden():
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
                if sys.platform != "linux":
                    target.raise_()

    def eventFilter(self, obj, event):
        if obj == self.custom_menu_bar:
            if event.type() == QEvent.MouseButtonDblClick:
                if not self.custom_menu_bar.actionAt(event.pos()):
                    self.title_bar.toggle_max_restore()
                    return True
            elif event.type() == QEvent.MouseButtonPress:
                if not self.custom_menu_bar.actionAt(event.pos()) and event.button() == Qt.LeftButton:
                    self._menu_bar_click_pos = event.globalPosition().toPoint()
            elif event.type() == QEvent.MouseMove:
                if hasattr(self, '_menu_bar_click_pos') and self._menu_bar_click_pos and (event.buttons() & Qt.LeftButton):
                    diff = (event.globalPosition().toPoint() - self._menu_bar_click_pos).manhattanLength()
                    if diff > QApplication.startDragDistance():
                        self.windowHandle().startSystemMove()
                        self._menu_bar_click_pos = None
                        return True
            elif event.type() == QEvent.MouseButtonRelease:
                self._menu_bar_click_pos = None

        if hasattr(self, 'list_view') and obj == self.list_view and event.type() == QEvent.Resize:
            self.update_scrollbar_range()
            return False
        if hasattr(self, 'list_view') and obj == self.list_view and event.type() == QEvent.Wheel:
            modifiers = event.modifiers()
            delta = event.angleDelta().y()

            if modifiers & Qt.ControlModifier:
                # Zoom In/Out
                if delta > 0:
                    new_size = min(36, self.config.editor_font_size + 1)
                else:
                    new_size = max(8, self.config.editor_font_size - 1)

                if new_size != self.config.editor_font_size:
                    self.config.set_editor_font(self.config.editor_font_family, new_size)
                    # self.apply_editor_font is connected to config change signal
                return True
            else:
                self.v_scrollbar.setValue(self.v_scrollbar.value() + (-delta / 40))
                return True

        # Handle key events for both Log View and Filter Tree
        if event.type() == QEvent.KeyPress:
            key = event.key()
            mod = event.modifiers()

            # Global Esc to close search bar
            if hasattr(self, 'search_overlay') and key == Qt.Key_Escape and not self.search_overlay.isHidden():
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
                    if hasattr(self, 'search_overlay') and not self.search_overlay.isHidden():
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

    def on_config_theme_changed(self, theme):
        is_dark = (theme == "Dark")
        if self.is_dark_mode != is_dark:
            self.is_dark_mode = is_dark
            self.settings.setValue("dark_mode", self.is_dark_mode)
            self.apply_theme()
            self.refresh_filter_tree()
            if self.current_engine and self.filters:
                self.recalc_filters(True)

    def apply_line_spacing(self, spacing):
        self.delegate.set_line_spacing(spacing)
        # Force QListView to recalculate layout/size hints
        self.list_view.model().layoutChanged.emit()
        self.list_view.viewport().update()
        self.update_scrollbar_range()

    def apply_theme(self):
        if not hasattr(self, 'theme_manager'):
            self.theme_manager = ThemeManager()

        self.theme_manager.set_theme(self.is_dark_mode)

        # Propagate theme to children
        self.notes_manager.set_theme(self.is_dark_mode)
        self.model.set_theme_mode(self.is_dark_mode)
        if hasattr(self, 'toast'): self.toast.set_theme(self.is_dark_mode)
        if hasattr(self, 'search_overlay'): self.search_overlay.apply_theme(self.is_dark_mode)

        # Get Palette & Config
        p = self.theme_manager.palette
        ui_font_size = self.config.ui_font_size
        ui_font_family = self.config.ui_font_family

        # Update Delegates and View
        self.delegate.set_hover_color(p['hover_qcolor'])
        self.delegate.set_theme_config(p['log_gutter_bg'], p['log_gutter_fg'], p['log_border'])
        self.v_scrollbar.set_theme(self.is_dark_mode)

        # Welcome Label Scaling
        if hasattr(self, 'welcome_label'):
            f = self.welcome_label.font()
            f.setFamily(ui_font_family)
            f.setPixelSize(ui_font_size + 8)
            self.welcome_label.setFont(f)

        self.list_view.viewport().update()

        # Update Window Controls Icons
        # Use 'titlebar_fg' for window controls to ensure visibility on title bar background
        icon_c = p['titlebar_fg']
        self.title_bar.btn_min.setIcon(get_svg_icon("window-minimize", icon_c))
        self.title_bar.btn_close.setIcon(get_svg_icon("x-close", icon_c))
        self.update_maximize_icon()

        # Style Custom Title Bar
        self.title_bar.setStyleSheet(self.theme_manager.get_title_bar_style(ui_font_family, ui_font_size))
        self.title_bar.btn_close.setStyleSheet(self.theme_manager.get_close_btn_style())

        self._set_windows_title_bar_color(self.is_dark_mode)
        for widget in QApplication.topLevelWidgets():
            if widget.isWindow(): set_windows_title_bar_color(widget.winId(), self.is_dark_mode)
        self.update_status_bar(self.last_status_message)

        # Apply Global QSS
        app = QApplication.instance()
        app.setStyleSheet(self.theme_manager.get_stylesheet(ui_font_family, ui_font_size))

        # Update Welcome Icon
        welcome_icon_color = "#888888" # Subdued color for welcome screen
        self.welcome_icon.setPixmap(get_svg_icon("activity", welcome_icon_color, size=80).pixmap(80, 80))

        # Style Docks (Filters & Logs)
        self.filter_title_bar.setStyleSheet(self.theme_manager.get_dock_title_style())
        self.filter_tree.setStyleSheet(self.theme_manager.get_dock_list_style(self.is_dark_mode))
        self.filter_delegate.set_theme_config(p['dock_border'])

        self.log_title_bar.setStyleSheet(self.theme_manager.get_dock_title_style())
        self.log_tree.setStyleSheet(self.theme_manager.get_dock_list_style(self.is_dark_mode))
        self.log_list_delegate.set_theme_config(p['dock_border'])

        # Refresh Icons (Use fg_color for general UI icons)
        general_icon_c = p['fg_color']

        self.btn_add_filter.setIcon(get_svg_icon("plus", general_icon_c))
        self.btn_open_log.setIcon(get_svg_icon("file-text", general_icon_c))
        self.btn_clear_logs.setIcon(get_svg_icon("x-circle", general_icon_c))

        self.btn_side_loglist.setIcon(get_svg_icon("file-text", general_icon_c))
        self.btn_side_filter.setIcon(get_svg_icon("filter", general_icon_c))
        self.btn_side_notes.setIcon(get_svg_icon("book-open", general_icon_c))
        self.btn_settings.setIcon(get_svg_icon("settings", general_icon_c))

        self.open_action.setIcon(get_svg_icon("file-text", general_icon_c))
        self.recent_menu.setIcon(get_svg_icon("folder", general_icon_c))
        self.load_filters_action.setIcon(get_svg_icon("filter", general_icon_c))
        self.save_filters_action.setIcon(get_svg_icon("save", general_icon_c))
        self.save_filters_as_action.setIcon(get_svg_icon("save", general_icon_c))
        self.exit_action.setIcon(get_svg_icon("log-out", general_icon_c))

        self.copy_action.setIcon(get_svg_icon("copy", general_icon_c))
        self.find_action.setIcon(get_svg_icon("search", general_icon_c))
        self.goto_action.setIcon(get_svg_icon("hash", general_icon_c))
        
        self.toggle_log_sidebar_action.setIcon(get_svg_icon("file-text", general_icon_c))
        self.toggle_filter_sidebar_action.setIcon(get_svg_icon("filter", general_icon_c))
        self.toggle_notes_sidebar_action.setIcon(get_svg_icon("book-open", general_icon_c))
        self.show_filtered_action.setIcon(get_svg_icon("eye", general_icon_c))
        self.toggle_theme_action.setIcon(get_svg_icon("sun-moon", general_icon_c))

        self.add_note_action.setIcon(get_svg_icon("plus", general_icon_c))
        self.remove_note_action.setIcon(get_svg_icon("trash", general_icon_c))
        self.save_notes_action.setIcon(get_svg_icon("save", general_icon_c))
        self.export_notes_action.setIcon(get_svg_icon("external-link", general_icon_c))

        self.shortcuts_action.setIcon(get_svg_icon("keyboard", general_icon_c))
        self.doc_action.setIcon(get_svg_icon("external-link", general_icon_c))
        self.about_action.setIcon(get_svg_icon("info", general_icon_c))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        if files:
            for fp in files:
                if os.path.exists(fp):
                    self.load_log(fp, is_multiple=True)

    def open_file_dialog(self):
        last_dir = self.settings.value("last_dir", "")
        filepaths, _ = QFileDialog.getOpenFileNames(self, "Open Log Files", last_dir, "Log Files (*.log *.txt);;All Files (*)")
        if filepaths:
            for fp in filepaths:
                self.load_log(fp, is_multiple=True)

    def load_tat_filter_from_cli(self, path):
        """Internal helper for CLI to load filters without GUI interaction."""
        self.filter_controller.load_from_file(path)

    def load_logs_from_cli(self, file_list):
        """Internal helper for CLI to load multiple logs at once."""
        if not file_list: return
        for fp in file_list:
            if os.path.exists(fp):
                self.load_log(fp, is_multiple=True)

    def _clear_all_logs(self, check_unsaved=True):
        # 1. Check for unsaved notes before clearing everything
        if check_unsaved and self.notes_manager.has_unsaved_changes():
            res = ModernMessageBox.question(self, "Unsaved Notes",
                                            "There are unsaved notes. Save them for all files before clearing?",
                                            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                            QMessageBox.Save)

            if res == QMessageBox.Save:
                if not self.notes_manager.save_all_notes():
                    return # Save failed or cancelled inside save_all_notes
            elif res == QMessageBox.Cancel:
                return

        # 2. Proceed with clearing
        self.log_controller.clear_all_logs()
        self.log_states.clear()
        self.update_log_tree()
        self.current_log_path = None
        self.model.set_engine(None)

        # Clear notes and refresh notes view
        self.notes_manager.notes.clear()
        self.notes_manager.dirty_files.clear() # Reset dirty state
        self.notes_manager.loaded_files.clear() # Reset loaded state
        self.notes_manager.set_current_log_path(None)

        # Reset badges
        self.btn_side_notes.set_badge(0)
        self.btn_side_filter.set_badge(0)
        
        # Reset Filter Hits
        self.filter_controller.reset_hits()
        self.refresh_filter_tree()

        self.welcome_widget.show()
        self.central_stack.setCurrentIndex(0)
        self.update_window_title()
        self.update_status_bar("Ready")
        if hasattr(self, 'status_pos_label'):
            self.status_pos_label.setText("Ln 0")

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

    def on_log_loaded(self, filepath):
        self.central_stack.setCurrentIndex(1)
        self.welcome_widget.hide()

        self.update_log_tree()
        self._switch_to_log(filepath)

        count = self.current_engine.line_count()
        self.toast.show_message(f"Loaded {count:,} lines", duration=4000, type_str="success")
        self.hide_busy()

    def on_log_closed(self, filepath):
        if filepath in self.log_states: del self.log_states[filepath]
        self.update_log_tree()

        # If no logs left, clear UI
        if not self.loaded_logs:
            self._clear_all_logs(check_unsaved=False)
        else:
            # Switch to the new current log (controller already updated current_log_path)
            if self.log_controller.current_log_path:
                self._switch_to_log(self.log_controller.current_log_path)

    def load_log(self, filepath, is_multiple=False):
        if not filepath or not os.path.exists(filepath): return

        filepath = os.path.abspath(filepath)

        if filepath in self.loaded_logs:
            self._switch_to_log(filepath)
            return

        self.add_to_recent(filepath)
        self.update_status_bar(f"Loading {filepath}...")
        self.show_busy()
        self.settings.setValue("last_dir", os.path.dirname(filepath))

        # Use QTimer to allow UI to render the busy state before blocking load
        QTimer.singleShot(10, lambda: self._execute_load(filepath))

    def _execute_load(self, filepath):
        if not self.log_controller.load_log(filepath):
            self.hide_busy()
            self.toast.show_message(f"Failed to load {filepath}", type_str="error")

    def _switch_to_log(self, filepath):
        if filepath not in self.loaded_logs: return

        # Save current state before switching
        if self.current_log_path and self.current_log_path in self.loaded_logs:
            if self.current_log_path not in self.log_states:
                self.log_states[self.current_log_path] = {}
            self.log_states[self.current_log_path].update({
                "scroll": self.v_scrollbar.value(),
                "selected_raw": self.selected_raw_index
            })

        self.log_controller.set_current_log(filepath)
        self.current_log_path = filepath
        # self.current_engine is now a property, no assignment needed
        self.model.set_engine(self.current_engine, filepath)

        self.notes_manager.load_notes_for_file(filepath)
        self.notes_manager.set_current_log_path(filepath)
        count = self.current_engine.line_count()
        self.delegate.set_max_line_number(count)
        self.update_window_title()
        self.update_status_bar(f"Shows {count:,} lines")

        note_count = sum(1 for (fp, ln) in self.notes_manager.notes if fp == filepath)
        self.btn_side_notes.set_badge(note_count)

        # Restore State (Pre-fetch selected_raw for correct search indexing)
        state = self.log_states.get(filepath, {})
        scroll_pos = state.get("scroll", 0)
        selected_raw = state.get("selected_raw", -1)

        # Update internal state immediately so search calculation uses the correct index
        self.selected_raw_index = selected_raw

        self.update_scrollbar_range()

        # Restore filter cache state for the new file
        if "filter_cache" in state:
            self.filter_controller.set_cache(state["filter_cache"])
        else:
            # No cache for this file, force recalculation
            self.filter_controller.invalidate_cache(mark_modified=False)

        # Select in tree
        items = self.log_tree.findItems(os.path.basename(filepath), Qt.MatchExactly)
        for item in items:
            if item.data(0, Qt.UserRole) == filepath:
                self.log_tree.setCurrentItem(item)
                break

        if self.filters: self.recalc_filters()
        else: self.refresh_filter_tree()

        # Handle Search State: Auto-search if overlay is open, otherwise clear
        # Moved after filter calc to ensure filtered_indices are up-to-date
        self.current_match_index = -1
        query = self.search_overlay.input.text()
        if not self.search_overlay.isHidden() and query:
            is_case = self.search_overlay.btn_case.isChecked()
            self._suppress_search_jump = True
            self.search_controller.perform_search(self.current_engine, query, is_case)
            self._suppress_search_jump = False
        else:
            self.search_controller.perform_search(self.current_engine, "") # Clear controller state
            self.filtered_search_results = []
            self.v_scrollbar.set_search_results([], 1)
            self.search_overlay.set_results_info("")

        # Restore UI Scroll and Selection Visuals
        self.v_scrollbar.setValue(scroll_pos)
        if selected_raw != -1:
            self._restore_selection_ui(selected_raw)

        # Restore focus to search input if overlay is active
        if not self.search_overlay.isHidden():
            self.search_overlay.input.setFocus()

    def _restore_selection_ui(self, raw_index):
        """Internal helper to set the selection highlight without necessarily re-centering."""
        view_row = raw_index
        if self.show_filtered_only and self.model.filtered_indices:
             import bisect
             idx = bisect.bisect_left(self.model.filtered_indices, raw_index)
             if idx < len(self.model.filtered_indices) and self.model.filtered_indices[idx] == raw_index:
                 view_row = idx
             else: return # Not visible

        rel_row = view_row - self.model.viewport_start
        if 0 <= rel_row < self.model.rowCount():
            model_idx = self.model.index(rel_row, 0)
            self.list_view.setCurrentIndex(model_idx)

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
            path = item.data(0, Qt.UserRole)
            new_order.append(path)

            # Ensure highlight follows the current log file
            if self.current_log_path and path == self.current_log_path:
                self.log_tree.setCurrentItem(item)

        self.log_controller.log_order = new_order

    def on_log_tree_clicked(self, item, column):
        if not item: return
        path = item.data(0, Qt.UserRole)
        if path:
            self._switch_to_log(path)

    def show_log_list_context_menu(self, pos):
        item = self.log_tree.itemAt(pos)
        menu = QMenu(self)
        ThemeManager.apply_menu_theme(menu)
        ic = "#d4d4d4" if self.is_dark_mode else "#333333"

        if item:
            path = item.data(0, Qt.UserRole)
            rem_action = menu.addAction(get_svg_icon("trash", ic), "Remove File")
            rem_action.triggered.connect(lambda: self._remove_log_file(path))
            menu.addSeparator()

        clear_action = menu.addAction(get_svg_icon("x-circle", ic), "Clear All")
        clear_action.triggered.connect(lambda: self._clear_all_logs())
        menu.exec_(self.log_tree.mapToGlobal(pos))

    def _remove_log_file(self, filepath):
        if filepath in self.loaded_logs:
            # Check for unsaved notes for THIS specific file
            file_notes = {k: v for (fp, k), v in self.notes_manager.notes.items() if fp == filepath}
            if file_notes and self.notes_manager.has_unsaved_changes():
                res = ModernMessageBox.question(self, "Unsaved Notes",
                                                f"File '{os.path.basename(filepath)}' has unsaved notes. Save them before removing?",
                                                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                                QMessageBox.Save)

                if res == QMessageBox.Save:
                    # Save only this file's notes
                    self.notes_manager._save_file_notes(filepath)
                elif res == QMessageBox.Cancel:
                    return

            self.notes_manager.close_file(filepath)
            self.log_controller.close_log(filepath)
            # UI updates via on_log_closed signal

    def show_context_menu(self, pos):
        menu = QMenu(self)
        ThemeManager.apply_menu_theme(menu)
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
        if not self.isMaximized():
            self.last_normal_rect = self.geometry()

        self.update_scrollbar_range()

        if hasattr(self, 'search_overlay') and not self.search_overlay.isHidden():
            cw = self.centralWidget()
            self.search_overlay.move(cw.width() - self.search_overlay.width() - 20, 10)

        if hasattr(self, 'dimmer') and self.dimmer.isVisible():
            self.dimmer.resize(self.size())

        if hasattr(self, 'toast'):
            self.toast.resize_to_parent()
            self.toast.raise_()

        super().resizeEvent(event)

    def moveEvent(self, event):
        if not self.isMaximized():
            self.last_normal_rect = self.geometry()
        super().moveEvent(event)

    def show_dimmer(self):
        self.dimmer.show()

    def hide_dimmer(self):
        self.dimmer.hide()


    def show_search_bar(self):
        self.search_overlay.show_overlay()
        self.resizeEvent(None)

    def hide_search_bar(self):
        self.search_overlay.hide_overlay()

    def _on_search_closed(self):
        self.delegate.set_search_query(None, False)
        # Clear filtered results visually but keep controller state?
        # Usually closing search clears highlights.
        self.search_controller.perform_search(self.current_engine, "") # Clear
        self.filtered_search_results = []
        self.v_scrollbar.set_search_results([], 1)
        self.list_view.viewport().update()
        self.list_view.setFocus()

    def find_next(self, query=None, is_case=None, is_wrap=None):
        if isinstance(query, bool): query = None
        if query is None:
            query = self.search_overlay.input.text()
            is_case = self.search_overlay.btn_case.isChecked()
            is_wrap = self.search_overlay.btn_wrap.isChecked()

        if not query: return
        if self.delegate.search_query != query or not self.filtered_search_results:
            if self.search_overlay.isHidden(): return
            self._perform_search(query, is_case)
            return

        curr_raw = self.selected_raw_index
        idx = bisect.bisect_right(self.filtered_search_results, curr_raw)
        if idx >= len(self.filtered_search_results):
            if is_wrap:
                idx = 0; self.toast.show_message("Wrapped to top", type_str="warning")
            else: return

        keep_focus = self.search_overlay.input.hasFocus()
        self._jump_to_match(idx, focus_list=not keep_focus)

    def find_previous(self, query=None, is_case=None, is_wrap=None):
        if isinstance(query, bool): query = None
        if query is None:
            query = self.search_overlay.input.text()
            is_case = self.search_overlay.btn_case.isChecked()
            is_wrap = self.search_overlay.btn_wrap.isChecked()

        if not query: return
        if self.delegate.search_query != query or not self.filtered_search_results:
            if self.search_overlay.isHidden(): return
            self._perform_search(query, is_case)
            return

        curr_raw = self.selected_raw_index
        idx = bisect.bisect_left(self.filtered_search_results, curr_raw) - 1
        if idx < 0:
            if is_wrap:
                idx = len(self.filtered_search_results)-1; self.toast.show_message("Wrapped to bottom", type_str="warning")
            else: return

        keep_focus = self.search_overlay.input.hasFocus()
        self._jump_to_match(idx, focus_list=not keep_focus)

    def _perform_search(self, query, is_case=None):
        if is_case is None:
            is_case = self.search_overlay.btn_case.isChecked()
        self.search_controller.perform_search(self.current_engine, query, is_case)

    def on_search_results_ready(self, results, query):
        # results argument is raw results from controller

        # Get case sensitivity from overlay as it's the source of truth for UI state
        is_case = self.search_overlay.btn_case.isChecked()
        self.delegate.set_search_query(query, is_case)
        self.list_view.viewport().update()

        self.update_filtered_search_results()

        if self.filtered_search_results:
            # Jump to first visible result relative to current selection
            idx = bisect.bisect_left(self.filtered_search_results, self.selected_raw_index)
            if idx >= len(self.filtered_search_results): idx = 0

            self.search_overlay.set_results_info(f"{idx + 1} / {len(self.filtered_search_results)}")

            if not self._suppress_search_jump:
                keep_focus = self.search_overlay.input.hasFocus()
                target_raw = self.filtered_search_results[idx]
                self.jump_to_raw_index(target_raw, focus_list=not keep_focus)
        else:
            self.search_overlay.set_results_info("No results")

    def _jump_to_match(self, result_index, focus_list=True):
        if not self.search_results or result_index < 0 or result_index >= len(self.search_results): return
        raw_row = self.search_results[result_index]
        self.jump_to_raw_index(raw_row, focus_list)
        self.search_overlay.set_results_info(f"{result_index + 1} / {len(self.search_results)}")


    def on_notes_updated(self):
        self.list_view.viewport().update()
        if self.current_log_path:
            count = sum(1 for (fp, ln) in self.notes_manager.notes if fp == self.current_log_path)
            self.btn_side_notes.set_badge(count)

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
                # Explicitly clear selection and select ONLY the target row
                # to avoid issues when Ctrl key is held down during shortcuts.
                self.list_view.selectionModel().setCurrentIndex(index, QItemSelectionModel.ClearAndSelect)
                self.list_view.scrollTo(index, QAbstractItemView.PositionAtCenter)
                if focus_list: self.list_view.setFocus()
                self.selected_raw_index = raw_index # Ensure state is synced

    def _jump_to_match(self, result_index, focus_list=True):
        if not self.filtered_search_results or result_index < 0 or result_index >= len(self.filtered_search_results): return
        raw_row = self.filtered_search_results[result_index]
        self.jump_to_raw_index(raw_row, focus_list)
        if hasattr(self, 'search_overlay'):
            self.search_overlay.set_results_info(f"{result_index + 1} / {len(self.filtered_search_results)}")

    @property
    def filters_modified(self):
        return self.filter_controller.filters_modified

    @property
    def current_filter_file(self):
        return self.filter_controller.current_filter_file

    def _invalidate_all_filter_caches(self, mark_modified=True):
        """Clears filter cache for all loaded logs because filter rules have changed."""
        for state in self.log_states.values():
            if "filter_cache" in state:
                del state["filter_cache"]
        # Controller handles its own cache state

    def on_filter_tree_reordered(self):
        new_f = []
        root = self.filter_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            idx = item.data(0, Qt.UserRole)
            new_f.append(self.filters[idx])
            item.setData(0, Qt.UserRole, i)
        self.filter_controller.set_filters(new_f)

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
                self.filter_controller.toggle_filter(idx, st)

    def on_log_double_clicked(self, index):
        txt = self.model.data(index, Qt.DisplayRole)
        if txt: self.add_filter_dialog(initial_text=txt.strip())

    def edit_selected_filter(self):
        item = self.filter_tree.currentItem()
        if not item: return
        idx = item.data(0, Qt.UserRole)
        dialog = FilterDialog(self, self.filters[idx])
        if dialog.exec():
            self.filter_controller.update_filter(idx, dialog.get_data())

    def add_filter_dialog(self, initial_text=""):
        dialog = FilterDialog(self)
        if initial_text: dialog.pattern_edit.setText(initial_text)
        if dialog.exec():
            self.filter_controller.add_filter(dialog.get_data())

    def remove_filter(self):
        item = self.filter_tree.currentItem()
        if not item: return
        self.filter_controller.remove_filter(item.data(0, Qt.UserRole))

    def move_filter_top(self):
        item = self.filter_tree.currentItem()
        if not item: return
        self.filter_controller.move_filter(item.data(0, Qt.UserRole), 0)

    def move_filter_bottom(self):
        item = self.filter_tree.currentItem()
        if not item: return
        idx = item.data(0, Qt.UserRole)
        self.filter_controller.move_filter(idx, len(self.filters) - 1)

    def show_filter_menu(self, pos):
        item = self.filter_tree.itemAt(pos)
        menu = QMenu(self)
        ThemeManager.apply_menu_theme(menu)
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
            act.triggered.connect(lambda: self.filter_controller.toggle_filter(idx, not en))
        menu.exec_(self.filter_tree.mapToGlobal(pos))

    def import_filters(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Filters", self.settings.value("last_filter_dir", ""), "TAT (*.tat);;All (*)")
        if path:
            self.settings.setValue("last_filter_dir", os.path.dirname(path))
            if self.filter_controller.load_from_file(path):
                self.toast.show_message("Filters Loaded", type_str="success")

                # Auto-show Filter Panel when filters are loaded
                if self.filter_dock.isHidden():
                    self.filter_dock.show()
                    self.filter_dock.raise_()

    def closeEvent(self, event):
        # Helper to prompt user
        def prompt_save_changes(title, text):
            return ModernMessageBox.question(self, title, text,
                                             QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                             QMessageBox.Save)

        # 1. Check Filters
        if self.filters_modified:
            reply = prompt_save_changes("Unsaved Changes", "Filters have been modified. Do you want to save changes?")
            if reply == QMessageBox.Save:
                saved = False
                if self.current_filter_file:
                    saved = self.filter_controller.save_to_file(self.current_filter_file)
                else:
                    saved = self.save_filters_as()

                if saved:
                    # self.filters_modified = False # Controller handles this
                    pass
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
                if not self.notes_manager.save_all_notes():
                     event.ignore(); return
            elif reply == QMessageBox.Discard:
                pass
            else:
                event.ignore(); return

        # Save Window State (Moved to end to avoid saving if cancelled)
        is_max = self.isMaximized()
        self.settings.setValue("is_maximized", is_max)

        if not is_max:
            self.settings.setValue("window_rect", self.geometry())
        elif hasattr(self, 'last_normal_rect') and self.last_normal_rect:
            self.settings.setValue("window_rect", self.last_normal_rect)

        self.settings.setValue("window_state", self.saveState())

        event.accept()

    def quick_save_filters(self):
        if self.current_filter_file:
            if self.filter_controller.save_to_file(self.current_filter_file):
                self.update_window_title()
                self.toast.show_message("Saved", type_str="success")
        else: self.save_filters_as()

    def save_filters_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Filters As", self.settings.value("last_filter_dir", ""), "TAT (*.tat);;All (*)")
        if path:
            self.settings.setValue("last_filter_dir", os.path.dirname(path))
            if self.filter_controller.save_to_file(path):
                self.update_window_title()
                self.toast.show_message("Saved", type_str="success")
                return True
        return False

    def export_notes_to_text(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Notes", self.settings.value("last_note_export_dir", ""), "Text (*.txt);;All (*)")
        if path:
            self.settings.setValue("last_note_export_dir", os.path.dirname(path))
            self.notes_manager.export_to_text(path, self.current_engine)

    def update_window_title(self):
        p = [os.path.basename(self.current_log_path)] if self.current_log_path else []
        if self.current_filter_file: p.append(("*" if self.filters_modified else "") + os.path.basename(self.current_filter_file))
        elif self.filters_modified: p.append("*Unsaved")
        p.append(f"{self.APP_NAME} {self.VERSION}")
        title = " - ".join(p)
        self.setWindowTitle(title)
        self.title_bar.title_label.setText(title)

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

        if hasattr(self, 'status_pos_label'):
            self.status_pos_label.setText(f"Ln {raw + 1}")

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
        self.show_busy()
        try:
            self.filter_controller.apply_filters(self.current_engine)
        finally:
            self.hide_busy()

    def update_filtered_search_results(self):
        raw_results = self.search_controller.search_results
        if self.show_filtered_only and self.model.filtered_indices:
            visible_set = set(self.model.filtered_indices)
            self.filtered_search_results = [r for r in raw_results if r in visible_set]
        else:
            self.filtered_search_results = list(raw_results)

        total = len(self.model.filtered_indices) if self.show_filtered_only and self.model.filtered_indices else (self.current_engine.line_count() if self.current_engine else 0)
        self.v_scrollbar.set_search_results(self.filtered_search_results, total)

    def show_goto_dialog(self):
        total = self.current_engine.line_count() if self.current_engine else 0
        if total <= 0: return

        dialog = GoToLineDialog(self, total)
        set_windows_title_bar_color(dialog.winId(), self.is_dark_mode)

        if dialog.exec():
            val = dialog.get_line()
            target_raw = val - 1

            if self.show_filtered_only and self.model.filtered_indices:
                import bisect
                idx = bisect.bisect_left(self.model.filtered_indices, target_raw)

                # Check if exact match exists in filtered view
                if idx < len(self.model.filtered_indices) and self.model.filtered_indices[idx] == target_raw:
                    self.jump_to_raw_index(target_raw)
                else:
                    # Target line is hidden, switch to Full View
                    self.show_filtered_action.setChecked(False)
                    self.toggle_show_filtered_only()
                    self.jump_to_raw_index(target_raw)
                    self.toast.show_message(f"Line {val} was hidden. Switched to Full Log View.", type_str="info")
            else:
                self.jump_to_raw_index(target_raw)

    def show_shortcuts(self):
        shortcuts = [("General", ""), ("Ctrl + O", "Open Log File"), ("Ctrl + Q", "Exit Application"), ("", ""), ("View & Navigation", ""), ("Ctrl + F", "Open Find Bar"), ("Esc", "Close Find Bar / Clear Selection"), ("Ctrl + H", "Toggle Show Filtered Only"), ("F2 / F3", "Find Previous / Next"), ("Ctrl + Left / Right", "Navigate Filter Hits (Selected Filter)"), ("Home / End", "Jump to Start / End of Log"), ("", ""), ("Log View", ""), ("Double-Click", "Create Filter from selected text"), ("'C' key", "Add / Edit Note for current line"), ("Ctrl + C", "Copy selected lines"), ("", ""), ("Filters", ""), ("Delete", "Remove selected filter"), ("Double-Click", "Edit filter properties"), ("Space", "Toggle filter enabled/disabled")]

        dialog = ModernDialog(self, title="Keyboard Shortcuts", fixed_size=(550, 600))
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        tree = QTreeWidget()
        tree.setHeaderLabels(["Key", "Description"])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        # Apply slight styling to tree for dialog
        tree.setStyleSheet("border: none;")

        for k, d in shortcuts:
            item = QTreeWidgetItem(tree)
            if not k and not d: continue
            elif not d:
                item.setText(0, k); bg = QColor(60,60,60) if self.is_dark_mode else QColor(230,230,230)
                item.setBackground(0, bg); item.setBackground(1, bg); f = item.font(0); f.setBold(True); item.setFont(0, f)
            else: item.setText(0, k); item.setText(1, d)
        tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        tree.header().setSectionResizeMode(1, QHeaderView.Stretch)

        layout.addWidget(tree)

        btn = QPushButton("Close")
        btn.clicked.connect(dialog.accept)
        # Add button container
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(btn)
        btn_layout.setContentsMargins(10, 10, 10, 10)

        layout.addLayout(btn_layout)

        dialog.setContentLayout(layout)
        dialog.exec()

    def show_about(self):
        ModernMessageBox.information(self, "About", f"<h3>{self.APP_NAME} {self.VERSION}</h3><p>A high-performance log analysis tool built with PySide6 and Rust extension.</p><p>Developer: Gary Hsieh</p>")

    def open_documentation(self):
        path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "Doc", f"Log_Analyzer_{self.VERSION}_Docs_EN.html"))
        if os.path.exists(path): import webbrowser; webbrowser.open(f"file://{path}")

    def on_scrollbar_value_changed(self, value):
        self.is_scrolling = True
        try:
            self.model.set_viewport(value, self.calculate_viewport_size())

            # Sync visual selection
            if self.selected_raw_index != -1:
                target_row = -1

                if self.show_filtered_only and self.model.filtered_indices:
                    idx = bisect.bisect_left(self.model.filtered_indices, self.selected_raw_index)
                    if idx < len(self.model.filtered_indices) and self.model.filtered_indices[idx] == self.selected_raw_index:
                        target_row = idx - value
                else:
                    target_row = self.selected_raw_index - value

                if 0 <= target_row < self.model.rowCount():
                    idx = self.model.index(target_row, 0)
                    self.list_view.selectionModel().setCurrentIndex(idx, QItemSelectionModel.ClearAndSelect)
                else:
                    self.list_view.selectionModel().clearSelection()
        finally:
            self.is_scrolling = False

    def toggle_theme(self):
        new_theme = "Light" if self.is_dark_mode else "Dark"
        self.config.theme = new_theme

    def toggle_show_filtered_only_from_status(self):
        self.show_filtered_action.setChecked(not self.show_filtered_action.isChecked())
        self.toggle_show_filtered_only()

    def update_status_bar(self, message=None):
        if message:
            self.status_message_label.setText(message)

        if not hasattr(self, 'status_mode_label'): return

        total_count = self.current_engine.line_count() if self.current_engine else 0

        if not self.current_engine:
            self.status_mode_label.setText("No Log")
            self.status_count_label.setText("0 lines")
            return

        mode_text = "Filtered" if self.show_filtered_only else "Full Log"
        self.status_mode_label.setText(mode_text)

        if self.show_filtered_only:
            filtered_count = len(self.model.filtered_indices) if self.model.filtered_indices else 0
            self.status_count_label.setText(f"{filtered_count:,} / {total_count:,} lines")
        else:
            self.status_count_label.setText(f"{total_count:,} lines")

    def _set_windows_title_bar_color(self, is_dark):
        if sys.platform == "win32":
            set_windows_title_bar_color(self.winId(), is_dark)

    def showEvent(self, event):
        super().showEvent(event)
        # Workaround for frameless window restore issue on Windows
        if getattr(self, 'should_maximize', False):
            QTimer.singleShot(0, self.showMaximized)
        self.update_maximize_icon()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            self.update_maximize_icon()
        super().changeEvent(event)

    def update_maximize_icon(self):
        if not hasattr(self, 'title_bar'): return

        is_max = self.isMaximized()
        icon_name = "window-restore" if is_max else "window-maximize"

        # Get color from current theme manager
        fg = self.theme_manager.get_color('titlebar_fg') if hasattr(self, 'theme_manager') else "#cccccc"

        self.title_bar.btn_max.setIcon(get_svg_icon(icon_name, fg))
        self.title_bar.btn_max.setToolTip("Restore" if is_max else "Maximize")

    def show_busy(self):
        self.spinner.start()
        QApplication.processEvents()

    def hide_busy(self):
        self.spinner.stop()

    def close_app(self):
        self.close()


