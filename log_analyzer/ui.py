from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QListView,
                               QLabel, QFileDialog, QMenu, QStatusBar, QAbstractItemView, QApplication,
                               QHBoxLayout, QToolButton, QSizePolicy, QDockWidget, QTreeWidget, QTreeWidgetItem, QHeaderView,
                               QMessageBox, QPushButton, QStackedLayout, QFrame,
                               QSpinBox, QSizeGrip)
from PySide6.QtGui import QAction, QFont, QColor, QKeySequence, QIcon, QFontMetrics, QFontInfo
from PySide6.QtCore import Qt, QSettings, QTimer, QEvent, QSize, QItemSelectionModel, QRect
from .models import LogModel
from .theme_manager import theme_manager
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
import webbrowser

from .components import CustomTitleBar, DimmerOverlay, BadgeToolButton, ClickableLabel, LoadingSpinner, SearchOverlay
from .modern_dialog import ModernDialog
from .modern_messagebox import ModernMessageBox
from .scrollbar_map import SearchScrollBar
from .preferences_dialog import PreferencesDialog
from .config import get_config

# --- Template Imports ---
from .native_window import NativeWindowMixin, apply_window_rounding
from .icon_manager import icon_manager
from .notification_manager import notification_manager


class FilterTreeWidget(QTreeWidget):
    def __init__(self, on_drop_callback=None, parent=None):
        super().__init__(parent)
        self.on_drop_callback = on_drop_callback

    def dropEvent(self, event):
        super().dropEvent(event)
        if self.on_drop_callback:
            self.on_drop_callback()


class LogListView(QListView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.suppress_scroll = False

    def scrollTo(self, index, hint=QAbstractItemView.EnsureVisible):
        if self.suppress_scroll:
            return
        super().scrollTo(index, hint)


class GoToLineDialog(ModernDialog):
    def __init__(self, parent=None, max_line=1):
        super().__init__(parent, title="Go to Line", fixed_size=(300, 220))
        
        # Apply window rounding for Windows 11 look
        apply_window_rounding(self.winId())

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
        self.btn_ok.setIcon(icon_manager.load_icon("arrow-right", "#ffffff", 16))
        self.btn_ok.setLayoutDirection(Qt.RightToLeft) 
        self.btn_ok.clicked.connect(self.accept)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)

        self.setContentLayout(layout)

        self.spin_box.setFocus()
        self.spin_box.selectAll()

    def get_line(self):
        return self.spin_box.value()


class MainWindow(NativeWindowMixin, QMainWindow):
    VERSION = "V2.2"
    APP_NAME = "Log Analyzer"

    def __init__(self):
        super().__init__()

        self.log_controller = LogController()
        self.filter_controller = FilterController()
        self.search_controller = SearchController()

        self.log_controller.log_loaded.connect(self.on_log_loaded)
        self.log_controller.log_closed.connect(self.on_log_closed)

        self.filter_controller.filters_changed.connect(self.on_filters_changed)
        self.filter_controller.filter_results_ready.connect(self.on_filter_results_ready)

        self.search_controller.search_results_ready.connect(self.on_search_results_ready)

        if sys.platform == "win32":
            self.setup_native_window(title_bar_height=40)
        else:
            self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
            self.setWindowTitle(f"{self.APP_NAME} {self.VERSION}")

        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "loganalyzer.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(1200, 800)

        self.settings = QSettings("LogAnalyzer", "QtApp")
        self.config = get_config() 
        self.is_dark_mode = self.settings.value("dark_mode", False, type=bool)
        self.setAcceptDrops(True)
        self.last_status_message = "Ready"
        self.current_log_path = None

        self.custom_menu_bar = self.menuBar()
        self.custom_menu_bar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        
        self.title_bar = CustomTitleBar(self)
        self.title_bar.setObjectName("title_bar")
        self.title_bar.layout.insertWidget(1, self.custom_menu_bar, 0, Qt.AlignVCenter)
        self.setMenuWidget(self.title_bar)

        self.log_states = {} 

        self.show_filtered_only = False

        self.selected_filter_index = -1
        self.selected_raw_index = -1
        self.is_scrolling = False
        self._suppress_search_jump = False
        self._pending_view_switch_jump = False
        
        # --- View Anchor State ---
        self._anchor_raw = 0
        self._landed_v = -1

        if sys.platform == "linux":
            self.setDockOptions(QMainWindow.AllowTabbedDocks)
        else:
            self.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks | QMainWindow.AllowTabbedDocks)

        self.list_view = LogListView()
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
        self.notes_manager.message_requested.connect(self.on_notes_message)

        self.list_view.setUniformItemSizes(False)


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
        self.btn_side_loglist.clicked.connect(self.on_btn_side_loglist_clicked)

        self.btn_side_filter = BadgeToolButton()
        self.btn_side_filter.setCheckable(True)
        self.btn_side_filter.setFixedSize(48, 48)
        self.btn_side_filter.setToolTip("Filters (Ctrl+Shift+F)")
        self.btn_side_filter.clicked.connect(self.on_btn_side_filter_clicked)

        self.btn_side_notes = BadgeToolButton()
        self.btn_side_notes.setCheckable(True)
        self.btn_side_notes.setFixedSize(48, 48)
        self.btn_side_notes.setToolTip("Notes (Ctrl+Shift+N)")
        self.btn_side_notes.clicked.connect(self.on_btn_side_notes_clicked)

        self.activity_bar.addWidget(self.btn_side_loglist)
        self.activity_bar.addWidget(self.btn_side_filter)
        self.activity_bar.addWidget(self.btn_side_notes)

        empty = QWidget()
        empty.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.activity_bar.addWidget(empty)

        self.btn_settings = QToolButton()
        self.btn_settings.setFixedSize(48, 48)
        self.btn_settings.setToolTip("Settings")
        self.btn_settings.clicked.connect(self.open_preferences)
        self.activity_bar.addWidget(self.btn_settings)

        dock_features = QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetClosable
        if sys.platform == "linux":
            dock_features = QDockWidget.NoDockWidgetFeatures

        # --- Log List Dock ---
        self.log_list_dock = QDockWidget("LOG FILES", self)
        self.log_list_dock.setObjectName("LogListDock")
        self.log_list_dock.setFeatures(dock_features)
        self.log_list_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)

        self.log_title_bar = QWidget()
        log_title_layout = QHBoxLayout(self.log_title_bar)
        log_title_layout.setContentsMargins(10, 4, 4, 4)
        log_title_layout.setSpacing(4)
        self.log_title_label = QLabel("LOG FILES")
        self.log_title_label.setFont(theme_manager.get_font(9.5, QFont.Bold))
        self.btn_open_log = QToolButton()
        self.btn_open_log.setFixedSize(26, 26)
        self.btn_open_log.clicked.connect(self.open_file_dialog)
        self.btn_clear_logs = QToolButton()
        self.btn_clear_logs.setFixedSize(26, 26)
        self.btn_clear_logs.clicked.connect(self._clear_all_logs)
        log_title_layout.addWidget(self.log_title_label)
        log_title_layout.addStretch()
        log_title_layout.addWidget(self.btn_open_log)
        log_title_layout.addWidget(self.btn_clear_logs)
        self.log_list_dock.setTitleBarWidget(self.log_title_bar)

        self.log_tree = FilterTreeWidget(on_drop_callback=self.on_log_reordered)
        self.log_tree.setHeaderHidden(True) 
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
        self.log_list_dock.visibilityChanged.connect(self.on_log_list_dock_visibility_changed)
        self.log_list_dock.topLevelChanged.connect(self._on_dock_interaction)
        self._hide_dock_safely(self.log_list_dock)

        # --- Filter Dock ---
        self.filter_dock = QDockWidget("FILTERS", self)
        self.filter_dock.setObjectName("FilterDock")
        self.filter_dock.setFeatures(dock_features)
        self.filter_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)

        self.filter_title_bar = QWidget()
        filter_title_layout = QHBoxLayout(self.filter_title_bar)
        filter_title_layout.setContentsMargins(10, 4, 4, 4)
        filter_title_layout.setSpacing(4)
        self.filter_title_label = QLabel("FILTERS")
        self.filter_title_label.setFont(theme_manager.get_font(9.5, QFont.Bold))
        self.btn_add_filter = QToolButton()
        self.btn_add_filter.setFixedSize(26, 26)
        self.btn_add_filter.clicked.connect(self.add_filter_dialog)
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
        self.filter_tree.currentItemChanged.connect(self.on_filter_current_item_changed)
        self.filter_tree.installEventFilter(self)

        self.filter_dock.setWidget(self.filter_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.filter_dock)
        self.filter_dock.visibilityChanged.connect(self.on_filter_dock_visibility_changed)
        self.filter_dock.topLevelChanged.connect(self._on_dock_interaction)
        self._hide_dock_safely(self.filter_dock)

        # --- Notes Dock ---
        self.notes_dock = self.notes_manager.dock
        self.notes_dock.setObjectName("NotesDock")
        self.notes_dock.setFeatures(dock_features)
        self.notes_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.notes_dock)
        self.notes_dock.visibilityChanged.connect(self.on_notes_dock_visibility_changed)
        self.notes_dock.topLevelChanged.connect(self._on_dock_interaction)
        self._hide_dock_safely(self.notes_dock)

        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.v_scrollbar = SearchScrollBar(Qt.Vertical)
        self.v_scrollbar.valueChanged.connect(self.on_scrollbar_value_changed)
        self.list_view.installEventFilter(self)

        self.list_view.selectionModel().currentChanged.connect(self.on_view_selection_changed)

        self.central = QWidget()
        self.central.setObjectName("central_widget")
        self.setCentralWidget(self.central)
        self.central_layout = QVBoxLayout(self.central)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.central_layout.setSpacing(0)

        self.central_area = QWidget()
        self.central_stack = QStackedLayout(self.central_area)
        self.central_layout.addWidget(self.central_area)

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
        self.welcome_label.setFont(theme_manager.get_font(14))
        self.welcome_label.setStyleSheet("color: #888888;")
        welcome_layout.addWidget(self.welcome_label, 0, Qt.AlignCenter)

        self.central_stack.addWidget(self.welcome_widget)

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

        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(10, 0, 10, 0)
        status_layout.setSpacing(10)

        self.spinner = LoadingSpinner(size=14, color="#3794ff")
        self.status_message_label = QLabel("Ready")

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

        status_layout.addWidget(self.spinner)
        status_layout.addWidget(self.status_message_label)
        status_layout.addStretch()

        status_layout.addWidget(self.status_mode_label)
        status_layout.addWidget(self.status_count_label)
        status_layout.addWidget(self.status_pos_label)
        status_layout.addWidget(self.status_enc_label)

        self.status_bar.addWidget(status_container, 1)

        self.size_grip = QSizeGrip(self)
        self.status_bar.addPermanentWidget(self.size_grip)

        self._create_menu()
        self.custom_menu_bar.installEventFilter(self)

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

        if not has_saved_state:
            self.tabifyDockWidget(self.log_list_dock, self.filter_dock)
            self.tabifyDockWidget(self.filter_dock, self.notes_dock)

        self._hide_dock_safely(self.log_list_dock)
        self._hide_dock_safely(self.filter_dock)
        self._hide_dock_safely(self.notes_dock)

        self.dimmer = DimmerOverlay(self)
        self.toast = Toast(self)

        self.search_overlay = SearchOverlay(self.central_area)
        self.search_overlay.findNext.connect(self.find_next)
        self.search_overlay.findPrev.connect(self.find_previous)
        self.search_overlay.searchChanged.connect(self._perform_search)
        self.search_overlay.closed.connect(self._on_search_closed)

        self.config.editorFontChanged.connect(self.apply_editor_font)
        self.config.showLineNumbersChanged.connect(self.toggle_line_numbers)
        self.config.editorLineSpacingChanged.connect(self.apply_line_spacing)
        self.config.themeChanged.connect(self.on_config_theme_changed)
        self.config.uiFontSizeChanged.connect(lambda s: self.apply_theme())
        self.config.uiFontFamilyChanged.connect(lambda f: self.apply_theme())

        self.apply_editor_font(self.config.editor_font_family, self.config.editor_font_size)
        self.toggle_line_numbers(self.config.show_line_numbers)
        self.apply_line_spacing(self.config.editor_line_spacing)

        self.apply_theme()

    def on_notes_message(self, msg, t="info"):
        self.toast.show_message(msg, type_str=t)

    def on_btn_side_loglist_clicked(self):
        self.toggle_sidebar(2)

    def on_btn_side_filter_clicked(self):
        self.toggle_sidebar(0)

    def on_btn_side_notes_clicked(self):
        self.toggle_sidebar(1)

    def on_log_list_dock_visibility_changed(self, visible):
        self.btn_side_loglist.setChecked(visible)
        self._refresh_overlay_pos()

    def on_filter_dock_visibility_changed(self, visible):
        self.btn_side_filter.setChecked(visible)
        self._refresh_overlay_pos()

    def on_notes_dock_visibility_changed(self, visible):
        self.btn_side_notes.setChecked(visible)
        self._refresh_overlay_pos()

    def on_filter_current_item_changed(self, curr, prev):
        self.on_filter_item_clicked(curr, 0)

    def _on_dock_interaction(self, floating):
        if floating:
            target = self.sender()
            if target:
                apply_window_rounding(target.winId())
        self.refresh_frame()
        self._refresh_overlay_pos()

    def _refresh_overlay_pos(self):
        if hasattr(self, 'search_overlay') and not self.search_overlay.isHidden():
            QTimer.singleShot(10, lambda: self.resizeEvent(None))

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
        QTimer.singleShot(100, self.refresh_frame)

    def on_filters_changed(self):
        self.refresh_filter_tree()
        self.update_window_title()
        self._invalidate_all_filter_caches(mark_modified=False)
        self.recalc_filters()

    def on_filter_results_ready(self, res, rust_f):
        tag_codes, filtered_indices = res[0], res[1]
        palette = {}
        for j, rf in enumerate(rust_f):
            f_idx = rf[4]
            fg = adjust_color_for_theme(self.filters[f_idx]["fg_color"], False, self.is_dark_mode)
            bg = adjust_color_for_theme(self.filters[f_idx]["bg_color"], True, self.is_dark_mode)
            palette[j+2] = (fg, bg)
            
        self.model.update_filter_result(tag_codes, palette, filtered_indices if self.show_filtered_only else None)
        
        # 1. Update Scrollbar Range (silent)
        self.v_scrollbar.blockSignals(True)
        self.update_scrollbar_range(sync_view=False)
        self.v_scrollbar.blockSignals(False)
        
        self.update_filtered_search_results()
        self.refresh_filter_tree()
        
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
        
        # --- VIEW RESTORE (TO FILTERED) ---
        if self._pending_view_switch_jump and self.show_filtered_only:
            target_v = 0
            if self.model.filtered_indices:
                target_v = bisect.bisect_left(self.model.filtered_indices, self._anchor_raw)
                self._landed_v = target_v
            
            self.v_scrollbar.blockSignals(True)
            self.v_scrollbar.setValue(target_v)
            self.v_scrollbar.blockSignals(False)
            self.on_scrollbar_value_changed(target_v)
            self._pending_view_switch_jump = False

    def apply_editor_font(self, family, size):
        self.list_view.setStyleSheet(f"font-family: \"{family}\"; font-size: {size}pt;")
        font = QFont(family, size)
        font.setStyleHint(QFont.Monospace)
        self.list_view.setFont(font)
        self.list_view.viewport().update()
        self.update_scrollbar_range()

    def toggle_line_numbers(self, show):
        self.delegate.set_show_line_numbers(show)
        self.list_view.viewport().update()

    def _create_menu(self):
        menu_bar = self.custom_menu_bar
        file_menu = menu_bar.addMenu("&File")
        theme_manager.apply_menu_theme(file_menu)
        self.open_action = QAction("&Open Log...", self)
        self.open_action.setShortcut("Ctrl+O")
        self.open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(self.open_action)
        self.recent_menu = file_menu.addMenu("Open Recent")
        theme_manager.apply_menu_theme(self.recent_menu)
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
        theme_manager.apply_menu_theme(edit_menu)
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
        theme_manager.apply_menu_theme(view_menu)
        self.toggle_log_sidebar_action = QAction("Log Files", self)
        self.toggle_log_sidebar_action.setShortcut("Ctrl+Shift+L")
        self.toggle_log_sidebar_action.triggered.connect(self.on_btn_side_loglist_clicked)
        view_menu.addAction(self.toggle_log_sidebar_action)
        self.toggle_filter_sidebar_action = QAction("Filters", self)
        self.toggle_filter_sidebar_action.setShortcut("Ctrl+Shift+F")
        self.toggle_filter_sidebar_action.triggered.connect(self.on_btn_side_filter_clicked)
        view_menu.addAction(self.toggle_filter_sidebar_action)
        self.toggle_notes_sidebar_action = QAction("Notes", self)
        self.toggle_notes_sidebar_action.setShortcut("Ctrl+Shift+N")
        self.toggle_notes_sidebar_action.triggered.connect(self.on_btn_side_notes_clicked)
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
        theme_manager.apply_menu_theme(notes_menu)
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
        self.next_action.triggered.connect(lambda: self.find_next())
        self.addAction(self.next_action)
        
        self.prev_action = QAction("Find Previous", self)
        self.prev_action.setShortcut("F2")
        self.prev_action.triggered.connect(lambda: self.find_previous())
        self.addAction(self.prev_action)
        
        help_menu = menu_bar.addMenu("&Help")
        theme_manager.apply_menu_theme(help_menu)
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
        v_val = self.v_scrollbar.value()
        
        # --- MEMORY PROTECTION: Preserve the origin point ---
        if not self.show_filtered_only:
            # Entering Filtered View: Set the anchor
            self._anchor_raw = v_val
        else:
            # Returning to Full View: Check if user scrolled
            if v_val != self._landed_v:
                # User MOVED in Filtered mode. Update anchor to current visual row's raw index.
                if self.model.filtered_indices and 0 <= v_val < len(self.model.filtered_indices):
                    self._anchor_raw = self.model.filtered_indices[v_val]
                else:
                    self._anchor_raw = v_val
            # If user DID NOT move (v_val == landed_v), we preserve the original anchor_raw.

        self.show_filtered_only = self.show_filtered_action.isChecked()
        self._pending_view_switch_jump = True
        self.recalc_filters()
        
        # --- IMMEDIATE RETURN (TO FULL) ---
        if not self.show_filtered_only:
            target_v = self._anchor_raw
            
            self.v_scrollbar.blockSignals(True)
            self.update_scrollbar_range(sync_view=False)
            self.v_scrollbar.setValue(target_v)
            self.v_scrollbar.blockSignals(False)
            self.on_scrollbar_value_changed(target_v)
            self._pending_view_switch_jump = False

        mode_str = "Filtered View" if self.show_filtered_only else "Full Log View"
        self.toast.show_message(mode_str)

    def _hide_dock_safely(self, dock):
        """Forces a dock to hide by unparenting from layout on Linux to destroy native handles."""
        if not dock: return
        if sys.platform == "linux":
            dock.setFloating(False)
            if dock.titleBarWidget(): dock.titleBarWidget().hide()
            if dock.widget(): dock.widget().hide()
            self.removeDockWidget(dock)
            # FORCE: Unparent to None to destroy the native surface layer completely
            dock.setParent(None)
        dock.hide()

    def _show_dock_safely(self, dock):
        """Forces a dock to show correctly on Linux."""
        if not dock: return
        if sys.platform == "linux":
            self.addDockWidget(Qt.LeftDockWidgetArea, dock)
            if dock.titleBarWidget(): dock.titleBarWidget().show()
            if dock.widget(): dock.widget().show()
        dock.show()
        dock.raise_()

    def _activate_dock(self, target):
        """Intelligently shows a dock by hiding others in the SAME area only (Windows only)."""
        if not target: return
        docks = [self.filter_dock, self.notes_dock, self.log_list_dock]
        
        if sys.platform != "linux":
            # Windows Logic: Only mutual exclude if in same dock area and NOT floating
            target_area = self.dockWidgetArea(target)
            for d in docks:
                if d != target and not d.isFloating() and self.dockWidgetArea(d) == target_area:
                    self._hide_dock_safely(d)
        else:
            # Linux Logic: Strict exclusivity for exposure stability
            for d in docks:
                if d != target: self._hide_dock_safely(d)
        
        self._show_dock_safely(target)

    def _show_dock_exclusive(self, index):
        """Deprecated: Use _activate_dock instead. Maintained for compat."""
        docks = [self.filter_dock, self.notes_dock, self.log_list_dock]
        if 0 <= index < len(docks):
            self._activate_dock(docks[index])

    def toggle_sidebar(self, index):
        docks = [self.filter_dock, self.notes_dock, self.log_list_dock]
        if index < 0 or index >= len(docks):
            return
        target = docks[index]
        
        # Check current visible state carefully on Linux
        is_active = target.isVisible() and not target.isHidden()
        
        if is_active:
            self._hide_dock_safely(target)
        else:
            self._activate_dock(target)
        
        if sys.platform == "linux":
            self.centralWidget().update()
            QApplication.processEvents()



    def eventFilter(self, obj, event):
        if obj == self.custom_menu_bar:
            if event.type() == QEvent.MouseButtonDblClick:
                if not self.custom_menu_bar.actionAt(event.pos()):
                    self.title_bar.toggle_max_restore()
                    return True
        if hasattr(self, 'list_view') and obj == self.list_view and event.type() == QEvent.Resize:
            self.update_scrollbar_range()
            return False
        if hasattr(self, 'list_view') and obj == self.list_view and event.type() == QEvent.Wheel:
            modifiers = event.modifiers()
            delta = event.angleDelta().y()
            if modifiers & Qt.ControlModifier:
                new_size = min(36, max(8, self.config.editor_font_size + (1 if delta > 0 else -1)))
                if new_size != self.config.editor_font_size:
                    self.config.set_editor_font(self.config.editor_font_family, new_size)
                return True
            else:
                # Optimized Scrolling: Use system setting for lines per notch
                lines = QApplication.wheelScrollLines()
                step = (delta / 120) * lines
                self.v_scrollbar.setValue(self.v_scrollbar.value() - step)
                return True
        if event.type() == QEvent.KeyPress:
            key = event.key()
            mod = event.modifiers()
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
                if key in [Qt.Key_Return, Qt.Key_Enter]:
                    if hasattr(self, 'search_overlay') and not self.search_overlay.isHidden():
                        self.find_next()
                        return True
                elif key == Qt.Key_Down:
                    idx = self.list_view.currentIndex()
                    if idx.isValid() and idx.row() >= self.model.rowCount() - 1:
                        # Boundary navigation: faster scroll when holding down
                        self.v_scrollbar.setValue(self.v_scrollbar.value() + 3)
                        return True
                elif key == Qt.Key_Up:
                    idx = self.list_view.currentIndex()
                    if idx.isValid() and idx.row() <= 0:
                        # Boundary navigation: faster scroll when holding up
                        self.v_scrollbar.setValue(self.v_scrollbar.value() - 3)
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
                    QApplication.processEvents() # Ensure viewport update for index mapping
                    last = self.model.rowCount() - 1
                    if last >= 0:
                        self.list_view.setCurrentIndex(self.model.index(last, 0))
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
        self.list_view.model().layoutChanged.emit()
        self.list_view.viewport().update()
        self.update_scrollbar_range()

    def apply_theme(self):
        theme_manager.set_theme("dark_classic" if self.is_dark_mode else "light_classic")
        self.notes_manager.set_theme(self.is_dark_mode)
        self.model.set_theme_mode(self.is_dark_mode)
        if hasattr(self, 'toast'):
            self.toast.set_theme(self.is_dark_mode)
        if hasattr(self, 'search_overlay'):
            self.search_overlay.apply_theme(self.is_dark_mode)
        p = theme_manager.palette
        ui_font_size = self.config.ui_font_size
        ui_font_family = self.config.ui_font_family
        self.delegate.set_hover_color(p['hover_qcolor'])
        self.delegate.set_theme_config(p['log_gutter_bg'], p['log_gutter_fg'], p['log_border'])
        self.v_scrollbar.set_theme(self.is_dark_mode)
        if hasattr(self, 'welcome_label'):
            f = self.welcome_label.font()
            f.setFamily(ui_font_family)
            f.setPixelSize(ui_font_size + 8)
            self.welcome_label.setFont(f)
        self.list_view.viewport().update()
        
        icon_c = p['titlebar_fg']
        self.title_bar.btn_min.setIcon(icon_manager.load_icon("min", icon_c, 16))
        self.title_bar.btn_close.setIcon(icon_manager.load_icon("close", icon_c, 16))
        self.update_maximize_icon()
        self.title_bar.setStyleSheet(theme_manager.get_title_bar_style(ui_font_family, ui_font_size))
        self.title_bar.btn_close.setStyleSheet(theme_manager.get_close_btn_style())
        
        self.apply_mica(dark_mode=self.is_dark_mode)
        for widget in QApplication.topLevelWidgets():
            if widget.isWindow():
                set_windows_title_bar_color(widget.winId(), self.is_dark_mode)
        
        self.update_status_bar(self.last_status_message)
        app = QApplication.instance()
        app.setStyleSheet(theme_manager.get_stylesheet(ui_font_family, ui_font_size))
        
        welcome_icon_color = "#888888" 
        self.welcome_icon.setPixmap(icon_manager.load_pixmap("activity", welcome_icon_color, 80, 80))
        
        # Style standard docks
        for dock in [self.log_list_dock, self.filter_dock, self.notes_dock]:
            if dock.titleBarWidget():
                dock.titleBarWidget().setStyleSheet(theme_manager.get_dock_title_style())
            content = dock.widget()
            if content:
                tree = content.findChild(QTreeWidget)
                if tree:
                    tree.setStyleSheet(theme_manager.get_dock_list_style(self.is_dark_mode))

        general_icon_c = p['fg_color']
        self.btn_add_filter.setIcon(icon_manager.load_icon("plus", general_icon_c, 18))
        self.btn_open_log.setIcon(icon_manager.load_icon("file-text", general_icon_c, 18))
        self.btn_clear_logs.setIcon(icon_manager.load_icon("x-circle", general_icon_c, 18))
        self.btn_side_loglist.setIcon(icon_manager.load_icon("file-text", general_icon_c, 24))
        self.btn_side_filter.setIcon(icon_manager.load_icon("filter", general_icon_c, 24))
        self.btn_side_notes.setIcon(icon_manager.load_icon("edit", general_icon_c, 24))
        self.btn_settings.setIcon(icon_manager.load_icon("settings", general_icon_c, 24))
        
        self.open_action.setIcon(icon_manager.load_icon("file-text", general_icon_c, 16))
        self.recent_menu.setIcon(icon_manager.load_icon("file-text", general_icon_c, 16))
        self.load_filters_action.setIcon(icon_manager.load_icon("filter", general_icon_c, 16))
        self.save_filters_action.setIcon(icon_manager.load_icon("save", general_icon_c, 16))
        self.save_filters_as_action.setIcon(icon_manager.load_icon("save", general_icon_c, 16))
        self.exit_action.setIcon(icon_manager.load_icon("log-out", general_icon_c, 16))
        self.copy_action.setIcon(icon_manager.load_icon("copy", general_icon_c, 16))
        self.find_action.setIcon(icon_manager.load_icon("search", general_icon_c, 16))
        self.goto_action.setIcon(icon_manager.load_icon("hash", general_icon_c, 16))
        self.toggle_log_sidebar_action.setIcon(icon_manager.load_icon("file-text", general_icon_c, 16))
        self.toggle_filter_sidebar_action.setIcon(icon_manager.load_icon("filter", general_icon_c, 16))
        self.toggle_notes_sidebar_action.setIcon(icon_manager.load_icon("edit", general_icon_c, 16))
        self.show_filtered_action.setIcon(icon_manager.load_icon("eye", general_icon_c, 16))
        self.toggle_theme_action.setIcon(icon_manager.load_icon("sun-moon", general_icon_c, 16))
        self.add_note_action.setIcon(icon_manager.load_icon("plus", general_icon_c, 16))
        self.remove_note_action.setIcon(icon_manager.load_icon("trash", general_icon_c, 16))
        self.save_notes_action.setIcon(icon_manager.load_icon("save", general_icon_c, 16))
        self.export_notes_action.setIcon(icon_manager.load_icon("external-link", general_icon_c, 16))
        self.shortcuts_action.setIcon(icon_manager.load_icon("keyboard", general_icon_c, 16))
        self.doc_action.setIcon(icon_manager.load_icon("book-open", general_icon_c, 16))
        self.about_action.setIcon(icon_manager.load_icon("info", general_icon_c, 16))

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for fp in files:
            if os.path.exists(fp):
                self.load_log(fp, is_multiple=True)
    def open_file_dialog(self):
        last_dir = self.settings.value("last_dir", "")
        filepaths, _ = QFileDialog.getOpenFileNames(self, "Open Log Files", last_dir, "Log Files (*.log *.txt);;All Files (*)")
        for fp in filepaths:
            self.load_log(fp, is_multiple=True)
    def load_tat_filter_from_cli(self, path):
        self.filter_controller.load_from_file(path)
    def load_logs_from_cli(self, file_list):
        if not file_list:
            return
        for fp in file_list:
            if os.path.exists(fp):
                self.load_log(fp, is_multiple=True)
    def _clear_all_logs(self):
        if self.notes_manager.has_unsaved_changes():
            res = ModernMessageBox.question(self, "Unsaved Notes", "There are unsaved notes. Save them for all files before clearing?", QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
            if res == QMessageBox.Save:
                if not self.notes_manager.save_all_notes():
                    return
            elif res == QMessageBox.Cancel:
                return
        self.log_controller.clear_all_logs()
        self.log_states.clear()
        self.update_log_tree()
        self.current_log_path = None
        self.model.set_engine(None)
        self.notes_manager.notes.clear()
        self.notes_manager.dirty_files.clear()
        self.notes_manager.loaded_files.clear()
        self.notes_manager.set_current_log_path(None)
        self.btn_side_notes.set_badge(0)
        self.btn_side_filter.set_badge(0)
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
            if not os.path.exists(fp):
                continue
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
        if filepath in recent_files:
            recent_files.remove(filepath)
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
        if filepath in self.log_states:
            del self.log_states[filepath]
        self.update_log_tree()
        if not self.loaded_logs:
            self._clear_all_logs_force()
        else:
            if self.log_controller.current_log_path:
                self._switch_to_log(self.log_controller.current_log_path)
    def _clear_all_logs_force(self):
        self.log_controller.clear_all_logs()
        self.log_states.clear()
        self.update_log_tree()
        self.current_log_path = None
        self.model.set_engine(None)
        self.welcome_widget.show()
        self.central_stack.setCurrentIndex(0)
        self.update_window_title()
        self.update_status_bar("Ready")
    def load_log(self, filepath, is_multiple=False):
        if not filepath or not os.path.exists(filepath):
            return
        filepath = os.path.abspath(filepath)
        if filepath in self.loaded_logs:
            self._switch_to_log(filepath)
            return
        self.add_to_recent(filepath)
        self.update_status_bar(f"Loading {filepath}...")
        self.show_busy()
        self.settings.setValue("last_dir", os.path.dirname(filepath))
        QTimer.singleShot(10, lambda: self._execute_load(filepath))
    def _execute_load(self, filepath):
        if not self.log_controller.load_log(filepath):
            self.hide_busy()
            self.toast.show_message(f"Failed to load {filepath}", type_str="error")
    def _switch_to_log(self, filepath):
        if filepath not in self.loaded_logs:
            return
        if self.current_log_path and self.current_log_path in self.loaded_logs:
            if self.current_log_path not in self.log_states:
                self.log_states[self.current_log_path] = {}
            self.log_states[self.current_log_path]["scroll"] = self.v_scrollbar.value()
            self.log_states[self.current_log_path]["selected_raw"] = self.selected_raw_index
        self.log_controller.set_current_log(filepath)
        self.current_log_path = filepath
        self.model.set_engine(self.current_engine, filepath)
        self.notes_manager.load_notes_for_file(filepath)
        self.notes_manager.set_current_log_path(filepath)
        count = self.current_engine.line_count()
        self.delegate.set_max_line_number(count)
        self.update_window_title()
        self.update_status_bar(f"Shows {count:,} lines")
        count_notes = sum(1 for (fp, ln) in self.notes_manager.notes if fp == filepath)
        self.btn_side_notes.set_badge(count_notes)
        state = self.log_states.get(filepath, {})
        scroll_pos = state.get("scroll", 0)
        selected_raw = state.get("selected_raw", -1)
        self.selected_raw_index = selected_raw
        
        self.v_scrollbar.blockSignals(True)
        self.update_scrollbar_range(sync_view=False)
        self.v_scrollbar.blockSignals(False)
        
        if "filter_cache" in state:
            self.filter_controller.set_cache(state["filter_cache"])
        else:
            self.filter_controller.invalidate_cache(mark_modified=False)
        items = self.log_tree.findItems(os.path.basename(filepath), Qt.MatchExactly)
        for item in items:
            if item.data(0, Qt.UserRole) == filepath:
                self.log_tree.setCurrentItem(item)
        if self.filters:
            self.recalc_filters()
        else:
            self.refresh_filter_tree()
        query = self.search_overlay.input.text()
        if not self.search_overlay.isHidden() and query:
            is_case = self.search_overlay.btn_case.isChecked()
            self._suppress_search_jump = True
            self.search_controller.perform_search(self.current_engine, query, is_case)
            self._suppress_search_jump = False
        else:
            self.search_controller.perform_search(self.current_engine, "")
            self.filtered_search_results = []
            self.v_scrollbar.set_search_results([], 1)
            self.search_overlay.set_results_info("")
        self.v_scrollbar.setValue(scroll_pos)
        self.on_scrollbar_value_changed(scroll_pos)
        if selected_raw != -1:
            self._restore_selection_ui(selected_raw)
        if not self.search_overlay.isHidden():
            self.search_overlay.input.setFocus()
    def _restore_selection_ui(self, raw_index):
        view_row = raw_index
        if self.show_filtered_only and self.model.filtered_indices:
             idx = bisect.bisect_left(self.model.filtered_indices, raw_index)
             if idx < len(self.model.filtered_indices) and self.model.filtered_indices[idx] == raw_index:
                 view_row = idx
             else:
                 return 
        rel_row = view_row - self.model.viewport_start
        if 0 <= rel_row < self.model.rowCount():
            self.list_view.setCurrentIndex(self.model.index(rel_row, 0))
    def update_log_tree(self):
        self.log_tree.clear()
        for fp in self.log_order:
            item = QTreeWidgetItem(self.log_tree)
            item.setText(0, os.path.basename(fp))
            item.setToolTip(0, fp)
            item.setData(0, Qt.UserRole, fp)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled)
        if len(self.loaded_logs) > 1:
            self._show_dock_exclusive(2)
    def on_log_reordered(self):
        new_order = []
        root = self.log_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            path = item.data(0, Qt.UserRole)
            new_order.append(path)
            if self.current_log_path and path == self.current_log_path:
                self.log_tree.setCurrentItem(item)
        self.log_controller.log_order = new_order
    def on_log_tree_clicked(self, item, column):
        if item:
            path = item.data(0, Qt.UserRole)
            if path:
                self._switch_to_log(path)
    def show_log_list_context_menu(self, pos):
        item = self.log_tree.itemAt(pos)
        menu = QMenu(self)
        theme_manager.apply_menu_theme(menu)
        ic = theme_manager.palette['fg_color']
        if item:
            path = item.data(0, Qt.UserRole)
            rem_action = menu.addAction(icon_manager.load_icon("trash", ic, 16), "Remove File")
            rem_action.triggered.connect(lambda: self._remove_log_file(path))
            menu.addSeparator()
        clear_action = menu.addAction(icon_manager.load_icon("x-circle", ic, 16), "Clear All")
        clear_action.triggered.connect(self._clear_all_logs)
        menu.exec_(self.log_tree.mapToGlobal(pos))
    def _remove_log_file(self, filepath):
        if filepath in self.loaded_logs:
            file_notes = {k: v for (fp, k), v in self.notes_manager.notes if fp == filepath}
            if file_notes and self.notes_manager.has_unsaved_changes():
                res = ModernMessageBox.question(self, "Unsaved Notes", f"File '{os.path.basename(filepath)}' has unsaved notes. Save them before removing?", QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
                if res == QMessageBox.Save:
                    self.notes_manager._save_file_notes(filepath)
                elif res == QMessageBox.Cancel:
                    return
            self.notes_manager.close_file(filepath)
            self.log_controller.close_log(filepath)
    def show_context_menu(self, pos):
        menu = QMenu(self)
        theme_manager.apply_menu_theme(menu)
        ic = theme_manager.palette['fg_color']
        copy_action = QAction(icon_manager.load_icon("copy", ic, 16), "Copy", self)
        copy_action.triggered.connect(self.copy_selection)
        menu.addAction(copy_action)
        menu.addSeparator()
        indexes = self.list_view.selectionModel().selectedIndexes()
        if len(indexes) == 1:
            idx = indexes[0]
            abs_row = self.model.viewport_start + idx.row()
            raw_index = abs_row
            if self.show_filtered_only and self.model.filtered_indices:
                raw_index = self.model.filtered_indices[abs_row]
            menu.addAction(icon_manager.load_icon("edit", ic, 16), "Add/Edit Note", lambda: self.notes_manager.add_note(raw_index, "", self.current_log_path))
        menu.exec_(self.list_view.mapToGlobal(pos))
    def copy_selection(self):
        indexes = self.list_view.selectionModel().selectedIndexes()
        if not indexes:
            return
        indexes.sort(key=lambda x: x.row())
        text_lines = []
        for idx in indexes:
            if idx.isValid():
                text = self.model.data(idx, Qt.DisplayRole)
                if text is not None:
                    text_lines.append(text.rstrip('\r\n'))
        if text_lines:
            QApplication.clipboard().setText("\n".join(text_lines))
            self.toast.show_message(f"Copied {len(text_lines)} lines")
    def resizeEvent(self, event):
        if not self.isMaximized():
            self.last_normal_rect = self.geometry()
        self.update_scrollbar_range()
        if hasattr(self, 'search_overlay') and not self.search_overlay.isHidden():
            parent_w = self.central_area.width()
            self.search_overlay.move(parent_w - self.search_overlay.width() - 20, 10)
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
        if sys.platform == "linux":
            # Re-create dimmer every time on Linux to ensure fresh native surface
            self.dimmer = DimmerOverlay(self)
        
        if hasattr(self, 'dimmer'):
            self.dimmer.show()
            self.dimmer.raise_()

    def hide_dimmer(self):
        if hasattr(self, 'dimmer'):
            self.dimmer.hide()
            if sys.platform == "linux":
                # Destroy the native surface completely to prevent residue
                self.dimmer.setParent(None)
                self.dimmer.deleteLater()
                del self.dimmer
                self.repaint()
                QApplication.processEvents()

    def show_search_bar(self): 
        self.search_overlay.show_overlay()
        self.resizeEvent(None)
    def hide_search_bar(self): 
        self.search_overlay.hide_overlay()
    def _on_search_closed(self): 
        self.delegate.set_search_query(None, False)
        self.search_controller.perform_search(self.current_engine, "")
        self.filtered_search_results = []
        self.v_scrollbar.set_search_results([], 1)
        self.list_view.viewport().update()
        self.list_view.setFocus()
    def find_next(self, query=None, is_case=None, is_wrap=None):
        if isinstance(query, bool): query = None
        if query is None:
            query = self.search_overlay.input.text()
        if is_case is None:
            is_case = self.search_overlay.btn_case.isChecked()
        if is_wrap is None:
            is_wrap = self.search_overlay.btn_wrap.isChecked()
        if not query:
            return
        if self.delegate.search_query != query or not self.filtered_search_results:
            if not self.search_overlay.isHidden():
                self._perform_search(query, is_case)
            return
        idx = bisect.bisect_right(self.filtered_search_results, self.selected_raw_index)
        if idx >= len(self.filtered_search_results):
            if is_wrap:
                idx = 0
                self.toast.show_message("Wrapped to top", type_str="warning")
            else:
                return
        self._jump_to_match(idx, focus_list=not self.search_overlay.input.hasFocus())
    def find_previous(self, query=None, is_case=None, is_wrap=None):
        if isinstance(query, bool): query = None
        if query is None:
            query = self.search_overlay.input.text()
        if is_case is None:
            is_case = self.search_overlay.btn_case.isChecked()
        if is_wrap is None:
            is_wrap = self.search_overlay.btn_wrap.isChecked()
        if not query:
            return
        if self.delegate.search_query != query or not self.filtered_search_results:
            if not self.search_overlay.isHidden():
                self._perform_search(query, is_case)
            return
        idx = bisect.bisect_left(self.filtered_search_results, self.selected_raw_index) - 1
        if idx < 0:
            if is_wrap:
                idx = len(self.filtered_search_results) - 1
                self.toast.show_message("Wrapped to bottom", type_str="warning")
            else:
                return
        self._jump_to_match(idx, focus_list=not self.search_overlay.input.hasFocus())
    def _perform_search(self, query, is_case=None): 
        self.search_controller.perform_search(self.current_engine, query, is_case if is_case is not None else self.search_overlay.btn_case.isChecked())
    def on_search_results_ready(self, results, query):
        self.delegate.set_search_query(query, self.search_overlay.btn_case.isChecked())
        self.list_view.viewport().update()
        self.update_filtered_search_results()
        if self.filtered_search_results:
            idx = bisect.bisect_left(self.filtered_search_results, self.selected_raw_index)
            if idx >= len(self.filtered_search_results):
                idx = 0
            self.search_overlay.set_results_info(f"{idx + 1} / {len(self.filtered_search_results)}")
            if not self._suppress_search_jump:
                self.jump_to_raw_index(self.filtered_search_results[idx], focus_list=not self.search_overlay.input.hasFocus())
        else:
            self.search_overlay.set_results_info("No results")
    def _jump_to_match(self, result_index, focus_list=True):
        if not self.filtered_search_results or result_index < 0 or result_index >= len(self.filtered_search_results):
            return
        self.jump_to_raw_index(self.filtered_search_results[result_index], focus_list)
        if hasattr(self, 'search_overlay'):
            self.search_overlay.set_results_info(f"{result_index + 1} / {len(self.filtered_search_results)}")
    def on_notes_updated(self): 
        self.list_view.viewport().update()
        if self.current_log_path:
            count = sum(1 for (fp, ln) in self.notes_manager.notes if fp == self.current_log_path)
            self.btn_side_notes.set_badge(count)
    def jump_to_raw_index(self, raw_index, focus_list=True, strict=True):
        view_row = raw_index
        is_exact = True
        if self.show_filtered_only and self.model.filtered_indices:
             idx = bisect.bisect_left(self.model.filtered_indices, raw_index)
             if idx < len(self.model.filtered_indices) and self.model.filtered_indices[idx] == raw_index:
                 view_row = idx
             else:
                 if strict:
                     return
                 view_row = idx
                 if view_row >= len(self.model.filtered_indices):
                     view_row = max(0, len(self.model.filtered_indices)-1)
                 is_exact = False
        target_scroll = max(0, view_row - (self.calculate_viewport_size() // 2))
        
        self.v_scrollbar.blockSignals(True)
        self.v_scrollbar.setValue(target_scroll)
        self.v_scrollbar.blockSignals(False)
        self.on_scrollbar_value_changed(target_scroll)
        
        QApplication.processEvents()
        if is_exact:
            rel_row = view_row - target_scroll
            if 0 <= rel_row < self.model.rowCount():
                self.list_view.selectionModel().setCurrentIndex(self.model.index(rel_row, 0), QItemSelectionModel.ClearAndSelect)
                self.list_view.scrollTo(self.model.index(rel_row, 0), QAbstractItemView.PositionAtCenter)
                if focus_list:
                    self.list_view.setFocus()
                self.selected_raw_index = raw_index
                
                # Visual Feedback: Flash the row
                if hasattr(self.delegate, 'flash_index'):
                    self.delegate.flash_index(rel_row)
                    self.list_view.viewport().update()
    @property
    def filters_modified(self): 
        return self.filter_controller.filters_modified
    @property
    def current_filter_file(self): 
        return self.filter_controller.current_filter_file
    def _invalidate_all_filter_caches(self, mark_modified=True): 
        for state in self.log_states.values():
            if "filter_cache" in state:
                del state["filter_cache"]
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
            prefix = ""
            if flt["is_exclude"]:
                prefix += " [x]"
            if flt["is_regex"]:
                prefix += " [R]"
            item = QTreeWidgetItem(self.filter_tree)
            item.setFlags((item.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsDropEnabled)
            item.setCheckState(0, Qt.Checked if flt["enabled"] else Qt.Unchecked)
            item.setText(1, f"{prefix} {flt['text']}".strip())
            item.setText(2, str(flt.get("hits", 0)))
            item.setData(0, Qt.UserRole, i)
            fg = adjust_color_for_theme(flt["fg_color"], False, self.is_dark_mode)
            bg = adjust_color_for_theme(self.filters[i]["bg_color"], True, self.is_dark_mode)
            item.setForeground(1, QColor(fg))
            item.setBackground(1, QColor(bg))
        self.filter_tree.blockSignals(False)
    def on_filter_item_clicked(self, item, column): 
        if item:
            self.selected_filter_index = item.data(0, Qt.UserRole)
    def on_filter_item_changed(self, item, column): 
        if column == 0 and item:
            idx = item.data(0, Qt.UserRole)
            if 0 <= idx < len(self.filters):
                st = (item.checkState(0) == Qt.Checked)
                self.filter_controller.toggle_filter(idx, st)
    def on_log_double_clicked(self, index): 
        txt = self.model.data(index, Qt.DisplayRole)
        if txt:
            self.add_filter_dialog(initial_text=txt.strip())
    def edit_selected_filter(self):
        item = self.filter_tree.currentItem()
        if not item:
            return
        idx = item.data(0, Qt.UserRole)
        dialog = FilterDialog(self, self.filters[idx])
        if dialog.exec():
            self.filter_controller.update_filter(idx, dialog.get_data())
    def add_filter_dialog(self, initial_text=""):
        dialog = FilterDialog(self)
        if initial_text:
            dialog.pattern_edit.setText(initial_text)
        if dialog.exec():
            self.filter_controller.add_filter(dialog.get_data())
    def remove_filter(self): 
        item = self.filter_tree.currentItem()
        if item:
            idx = item.data(0, Qt.UserRole)
            self.filter_controller.remove_filter(idx)
    def move_filter_top(self): 
        item = self.filter_tree.currentItem()
        if item:
            idx = item.data(0, Qt.UserRole)
            self.filter_controller.move_filter(idx, 0)
    def move_filter_bottom(self): 
        item = self.filter_tree.currentItem()
        if item:
            idx = item.data(0, Qt.UserRole)
            self.filter_controller.move_filter(idx, len(self.filters)-1)
    def show_filter_menu(self, pos):
        item = self.filter_tree.itemAt(pos)
        menu = QMenu(self)
        theme_manager.apply_menu_theme(menu)
        ic = theme_manager.palette['fg_color']
        menu.addAction(icon_manager.load_icon("plus", ic, 16), "Add Filter", self.add_filter_dialog)
        if item:
            idx = item.data(0, Qt.UserRole)
            menu.addSeparator()
            menu.addAction(icon_manager.load_icon("edit", ic, 16), "Edit Filter", self.edit_selected_filter)
            menu.addAction(icon_manager.load_icon("trash", ic, 16), "Remove Filter", self.remove_filter)
            menu.addSeparator()
            menu.addAction(icon_manager.load_icon("chevron-up", ic, 16), "Move to Top", self.move_filter_top)
            menu.addAction(icon_manager.load_icon("chevron-down", ic, 16), "Move to Bottom", self.move_filter_bottom)
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
                self._show_dock_exclusive(0)
    def closeEvent(self, event):
        if self.filters_modified:
            r = ModernMessageBox.question(self, "Unsaved Changes", "Filters modified. Save?", QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
            if r == QMessageBox.Save:
                saved = self.filter_controller.save_to_file(self.current_filter_file) if self.current_filter_file else self.save_filters_as()
                if not saved:
                    event.ignore()
                    return
            elif r == QMessageBox.Cancel:
                event.ignore()
                return
        if self.notes_manager.has_unsaved_changes():
            r = ModernMessageBox.question(self, "Unsaved Notes", "Notes modified. Save?", QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
            if r == QMessageBox.Save:
                if not self.notes_manager.save_all_notes():
                    event.ignore()
                    return
            elif r == QMessageBox.Cancel:
                event.ignore()
                return
        self.settings.setValue("is_maximized", self.isMaximized())
        self.settings.setValue("window_rect", self.geometry() if not self.isMaximized() else getattr(self, 'last_normal_rect', self.geometry()))
        self.settings.setValue("window_state", self.saveState())
        event.accept()
    def quick_save_filters(self): 
        if self.current_filter_file:
            if self.filter_controller.save_to_file(self.current_filter_file):
                self.update_window_title()
                self.toast.show_message("Saved", type_str="success")
        else:
            self.save_filters_as()
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
            self.notes_manager.export_to_text(path, self.current_engine)
    def update_window_title(self):
        p = []
        if self.current_log_path:
            p.append(os.path.basename(self.current_log_path))
        if self.current_filter_file:
            name = os.path.basename(self.current_filter_file)
            if self.filters_modified: name = "*" + name
            p.append(name)
        elif self.filters_modified:
            p.append("*Unsaved")
        p.append(f"{self.APP_NAME} {self.VERSION}")
        title = " - ".join(p)
        self.setWindowTitle(title)
        self.title_bar.title_label.setText(title)
    def calculate_viewport_size(self):
        h = self.list_view.viewport().height()
        rh = QFontMetrics(self.list_view.font()).height()
        return (h // (rh if rh > 0 else 20)) + 100
    def on_view_selection_changed(self, curr, prev):
        if self.is_scrolling or not curr.isValid():
            return
        abs_row = self.model.viewport_start + curr.row()
        raw = abs_row
        if self.show_filtered_only and self.model.filtered_indices:
            if abs_row < len(self.model.filtered_indices):
                raw = self.model.filtered_indices[abs_row]
        self.selected_raw_index = raw
        if hasattr(self, 'status_pos_label'):
            self.status_pos_label.setText(f"Ln {raw + 1}")
    def update_scrollbar_range(self, sync_view=True):
        if not self.current_engine:
            return
        total = self.current_engine.line_count()
        if self.show_filtered_only and self.model.filtered_indices is not None:
            total = len(self.model.filtered_indices)
        vp = self.calculate_viewport_size()
        self.v_scrollbar.setRange(0, max(0, total - vp))
        self.v_scrollbar.setPageStep(vp)
        if sync_view:
            self.on_scrollbar_value_changed(self.v_scrollbar.value())
    def navigate_filter_hit(self, reverse=False):
        if not self.current_engine or not self.model.tag_codes:
            return
        if self.selected_filter_index < 0:
            item = self.filter_tree.currentItem()
            if item:
                self.selected_filter_index = item.data(0, Qt.UserRole)
        if self.selected_filter_index < 0:
            return
        target_code = -1
        curr_j = 0
        for i, f in enumerate(self.filters):
            if f["enabled"]:
                if i == self.selected_filter_index:
                    target_code = curr_j + 2
                    break
                curr_j += 1
        if target_code == -1:
            return
        start = self.selected_raw_index if self.selected_raw_index != -1 else self.model.viewport_start
        found = -1
        if reverse:
            for r in range(start-1, -1, -1):
                if self.model.tag_codes[r] == target_code:
                    found = r
                    break
        else:
            for r in range(start+1, len(self.model.tag_codes)):
                if self.model.tag_codes[r] == target_code:
                    found = r
                    break
        if found != -1:
            self.selected_raw_index = found
            self.jump_to_raw_index(found)
    def recalc_filters(self, force_color_update=False):
        if self.current_engine:
            self.show_busy()
            self.filter_controller.apply_filters(self.current_engine)
            self.hide_busy()
    def update_filtered_search_results(self):
        raw = self.search_controller.search_results
        if self.show_filtered_only and self.model.filtered_indices:
            vset = set(self.model.filtered_indices)
            self.filtered_search_results = [r for r in raw if r in vset]
        else:
            self.filtered_search_results = list(raw)
        total = self.current_engine.line_count() if self.current_engine else 0
        if self.show_filtered_only and self.model.filtered_indices:
            total = len(self.model.filtered_indices)
        self.v_scrollbar.set_search_results(self.filtered_search_results, total)
    def show_goto_dialog(self):
        total = self.current_engine.line_count() if self.current_engine else 0
        if total <= 0:
            return
        dialog = GoToLineDialog(self, total)
        set_windows_title_bar_color(dialog.winId(), self.is_dark_mode)
        if dialog.exec():
            val = dialog.get_line()
            target_raw = val - 1
            if self.show_filtered_only and self.model.filtered_indices:
                idx = bisect.bisect_left(self.model.filtered_indices, target_raw)
                if idx < len(self.model.filtered_indices) and self.model.filtered_indices[idx] == target_raw:
                    self.jump_to_raw_index(target_raw)
                else:
                    self.show_filtered_action.setChecked(False)
                    self.toggle_show_filtered_only()
                    self.jump_to_raw_index(target_raw)
                    self.toast.show_message(f"Line {val} hidden. Full view.", type_str="info")
            else:
                self.jump_to_raw_index(target_raw)
    def show_shortcuts(self):
        shortcuts = [("General", ""), ("Ctrl + O", "Open Log File"), ("Ctrl + Q", "Exit Application"), ("", ""), ("View & Navigation", ""), ("Ctrl + F", "Open Find Bar"), ("Esc", "Close Find Bar / Clear Selection"), ("Ctrl + H", "Toggle Show Filtered Only"), ("F2 / F3", "Find Previous / Next"), ("Ctrl + Left / Right", "Navigate Filter Hits (Selected Filter)"), ("Home / End", "Jump to Start / End of Log"), ("", ""), ("Log View", ""), ("Double-Click", "Create Filter from selected text"), ("'C' key", "Add / Edit Note for current line"), ("Ctrl + C", "Copy selected lines"), ("", ""), ("Filters", ""), ("Delete", "Remove selected filter"), ("Double-Click", "Edit filter properties"), ("Space", "Toggle filter enabled/disabled")]
        dialog = ModernDialog(self, title="Keyboard Shortcuts", fixed_size=(550, 600))
        
        apply_window_rounding(dialog.winId())

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        tree = QTreeWidget()
        tree.setHeaderLabels(["Key", "Description"])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        tree.setStyleSheet("border: none;")
        for k, d in shortcuts:
            item = QTreeWidgetItem(tree)
            if not d and k:
                item.setText(0, k)
                item.setBackground(0, theme_manager.get_qcolor('bg_secondary'))
                item.setBackground(1, theme_manager.get_qcolor('bg_secondary'))
                f = item.font(0)
                f.setBold(True)
                item.setFont(0, f)
            elif d:
                item.setText(0, k)
                item.setText(1, d)
        tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(tree)
        btn = QPushButton("Close")
        btn.clicked.connect(dialog.accept)
        bl = QHBoxLayout()
        bl.addStretch()
        bl.addWidget(btn)
        bl.setContentsMargins(10, 10, 10, 10)
        layout.addLayout(bl)
        dialog.setContentLayout(layout)
        dialog.exec()
    def show_about(self): 
        ModernMessageBox.information(self, "About", f"<h3>{self.APP_NAME} {self.VERSION}</h3><p>A high-performance log analysis tool built with PySide6 and Rust extension.</p><p>Developer: Gary Hsieh</p>")
    def open_documentation(self): 
        doc_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Doc', f'Log_Analyzer_{self.VERSION}_Docs_EN.html'))
        if os.path.exists(doc_path):
            webbrowser.open(f"file://{doc_path}")
    def on_scrollbar_value_changed(self, value):
        self.is_scrolling = True
        self.list_view.suppress_scroll = True
        try:
            self.model.set_viewport(value, self.calculate_viewport_size())
            if self.selected_raw_index != -1:
                tr = -1
                if self.show_filtered_only and self.model.filtered_indices:
                    idx = bisect.bisect_left(self.model.filtered_indices, self.selected_raw_index)
                    if idx < len(self.model.filtered_indices) and self.model.filtered_indices[idx] == self.selected_raw_index:
                        tr = idx - value
                else:
                    tr = self.selected_raw_index - value
                if 0 <= tr < self.model.rowCount():
                    self.list_view.selectionModel().setCurrentIndex(self.model.index(tr, 0), QItemSelectionModel.ClearAndSelect)
                else:
                    self.list_view.selectionModel().clearSelection()
        finally:
            self.list_view.suppress_scroll = False
            self.is_scrolling = False
    def toggle_theme(self): 
        self.config.theme = "Light" if self.is_dark_mode else "Dark"
    def toggle_show_filtered_only_from_status(self): 
        self.show_filtered_action.setChecked(not self.show_filtered_action.isChecked())
        self.toggle_show_filtered_only()
    def update_status_bar(self, message=None):
        if message:
            self.status_message_label.setText(message)
        if not hasattr(self, 'status_mode_label'):
            return
        total = self.current_engine.line_count() if self.current_engine else 0
        if not self.current_engine:
            self.status_mode_label.setText("No Log")
            self.status_count_label.setText("0 lines")
            return
        self.status_mode_label.setText("Filtered" if self.show_filtered_only else "Full Log")
        if self.show_filtered_only:
            fcount = len(self.model.filtered_indices) if self.model.filtered_indices else 0
            self.status_count_label.setText(f"{fcount:,} / {total:,} lines")
        else:
            self.status_count_label.setText(f"{total:,} lines")
    def _set_windows_title_bar_color(self, is_dark): 
        if sys.platform == "win32":
            set_windows_title_bar_color(self.winId(), is_dark)
    def showEvent(self, event): 
        super().showEvent(event)
        if getattr(self, 'should_maximize', False):
            QTimer.singleShot(0, self.showMaximized)
        self.update_maximize_icon()
    def changeEvent(self, event): 
        if event.type() == QEvent.WindowStateChange:
            self.update_maximize_icon()
        super().changeEvent(event)
    def update_maximize_icon(self):
        if not hasattr(self, 'title_bar'):
            return
        is_max = self.isMaximized()
        fg = theme_manager.get_color('titlebar_fg')
        self.title_bar.btn_max.setIcon(icon_manager.load_icon("restore" if is_max else "max", fg, 16))
        self.title_bar.btn_max.setToolTip("Restore" if is_max else "Maximize")
    def show_busy(self): 
        self.spinner.start()
        QApplication.processEvents()
    def hide_busy(self): 
        self.spinner.stop()
    def close_app(self): 
        self.close()
