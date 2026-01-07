from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QListView,
                               QLabel, QFileDialog, QMenuBar, QMenu, QStatusBar, QAbstractItemView, QApplication,
                               QHBoxLayout, QLineEdit, QToolButton, QComboBox, QSizePolicy, QGraphicsDropShadowEffect,
                               QGraphicsOpacityEffect, QCheckBox, QDockWidget, QTreeWidget, QTreeWidgetItem, QHeaderView,
                               QDialog, QMessageBox, QScrollBar, QPushButton, QStackedLayout)
from PySide6.QtGui import QAction, QFont, QPalette, QColor, QKeySequence, QCursor, QIcon, QShortcut, QWheelEvent, QFontMetrics
from PySide6.QtCore import Qt, QSettings, QTimer, Slot, QModelIndex, QEvent, QPropertyAnimation
from .models import LogModel
from .engine_wrapper import get_engine
from .toast import Toast
from .delegates import LogDelegate
from .filter_dialog import FilterDialog
from .notes_manager import NotesManager
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
        # Perform the default drop logic (moving items in the tree visually)
        super().dropEvent(event)
        # Notify parent to sync internal data structure
        if self.on_drop_callback:
            self.on_drop_callback()

class MainWindow(QMainWindow):
    VERSION = "V2.0"
    APP_NAME = "Log Analyzer"

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{self.APP_NAME} (PySide6)")
        
        # Set App Icon
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "loganalyzer.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.resize(1200, 800)

        self.settings = QSettings("LogAnalyzer", "QtApp")
        self.is_dark_mode = self.settings.value("dark_mode", True, type=bool)
        self.last_status_message = "Ready"
        self.current_filter_file = None

        self.current_engine = None
        self.search_results = []
        self.current_match_index = -1
        self.search_history = []
        self.filters = []
        self.show_filtered_only = False

        # State tracking
        self.filters_modified = False
        self.selected_filter_index = -1
        self.current_log_path = None
        self.filters_dirty_cache = True # Indicates if backend needs to re-run filter
        self.cached_filter_results = None # Stores result of last engine.filter()
        self.is_scrolling = False
        
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

        # Managers (Must be init after Model)
        self.notes_manager = NotesManager(self)
        self.model.set_notes_ref(self.notes_manager.notes)
        self.notes_manager.notes_updated.connect(self.on_notes_updated)
        self.notes_manager.navigation_requested.connect(self.jump_to_raw_index)

        self.list_view.setUniformItemSizes(True)
        # self.list_view.setLayoutMode(QListView.Batched) # Removed for virtual viewport optimization
        # self.list_view.setBatchSize(100)

        # Virtual Viewport Setup
        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.v_scrollbar = QScrollBar(Qt.Vertical)
        self.v_scrollbar.valueChanged.connect(self.on_scrollbar_value_changed)
        self.list_view.installEventFilter(self) # For wheel events
        
        # Track selection for reliable navigation
        self.list_view.selectionModel().currentChanged.connect(self.on_view_selection_changed)

        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.list_view.setFont(font)


        central_widget = QWidget()
        self.central_stack = QStackedLayout(central_widget)
        
        # Page 0: Welcome
        self.welcome_label = QLabel("Drag & Drop Log File Here\nor use File > Open Log")
        self.welcome_label.setAlignment(Qt.AlignCenter)
        font_welcome = QFont("Consolas", 14)
        self.welcome_label.setFont(font_welcome)
        self.welcome_label.setStyleSheet("color: #888888;")
        self.central_stack.addWidget(self.welcome_label)

        # Page 1: List View Container
        list_container = QWidget()
        list_layout = QHBoxLayout(list_container)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(0)
        list_layout.addWidget(self.list_view)
        list_layout.addWidget(self.v_scrollbar)
        
        self.central_stack.addWidget(list_container)
        
        # Default to Welcome
        self.central_stack.setCurrentIndex(0)

        self.setCentralWidget(central_widget)


        # --- Filter Panel ---
        self.filter_dock = QDockWidget("Filters", self)
        self.filter_dock.setObjectName("FilterDock")
        self.filter_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)
        # Handle floating dock color
        self.filter_dock.topLevelChanged.connect(lambda is_floating: self._set_windows_title_bar_color(self.is_dark_mode))

        self.filter_tree = FilterTreeWidget(on_drop_callback=self.on_filter_tree_reordered)
        self.filter_tree.setHeaderLabels(["En", "Pattern", "Hits"])
        self.filter_tree.setRootIsDecorated(False) # Remove indentation for column alignment

        # Fixed Widths for metadata columns, Stretch for Pattern
        self.filter_tree.header().setStretchLastSection(False)
        self.filter_tree.header().setSectionResizeMode(0, QHeaderView.Fixed)
        self.filter_tree.header().resizeSection(0, 25)  # Minimized En
        self.filter_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.filter_tree.header().setSectionResizeMode(2, QHeaderView.Fixed)
        self.filter_tree.header().resizeSection(2, 60)  # Fits 7 digits comfortably

        self.filter_tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.filter_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.filter_tree.setDefaultDropAction(Qt.MoveAction)
        self.filter_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.filter_tree.customContextMenuRequested.connect(self.show_filter_menu)
        self.filter_tree.itemDoubleClicked.connect(self.edit_selected_filter)
        self.filter_tree.itemChanged.connect(self.on_filter_item_changed)
        self.filter_tree.itemClicked.connect(self.on_filter_item_clicked)
        self.filter_tree.installEventFilter(self)

        self.filter_dock.setWidget(self.filter_tree)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.filter_dock)

        # --- Search Bar ---
        self.search_widget = QWidget(central_widget)
        self.search_widget.setObjectName("search_widget")
        self.search_layout = QHBoxLayout(self.search_widget)
        self.search_layout.setContentsMargins(5, 5, 5, 5)
        self.search_layout.setSpacing(5)

        self.search_input = QComboBox()
        self.search_input.setEditable(True)
        self.search_input.setPlaceholderText("Find...")
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.search_input.setInsertPolicy(QComboBox.InsertAtTop)
        self.search_input.lineEdit().returnPressed.connect(self.find_next)

        self.shortcut_enter = QShortcut(QKeySequence(Qt.Key_Return), self.search_widget)
        self.shortcut_enter.activated.connect(self.find_next)
        self.shortcut_enter_num = QShortcut(QKeySequence(Qt.Key_Enter), self.search_widget)
        self.shortcut_enter_num.activated.connect(self.find_next)

        self.btn_prev = QToolButton()
        self.btn_prev.setText("▲")
        self.btn_prev.setFixedSize(26, 24)
        self.btn_next = QToolButton()
        self.btn_next.setText("▼")
        self.btn_next.setFixedSize(26, 24)
        
        self.chk_case = QToolButton()
        self.chk_case.setText("Aa")
        self.chk_case.setCheckable(True)
        self.chk_case.setFixedSize(26, 24)
        self.chk_case.setToolTip("Match Case")
        self.chk_case.setFocusPolicy(Qt.NoFocus)
        self.chk_case.toggled.connect(self.on_search_case_changed)

        self.chk_wrap = QToolButton()
        self.chk_wrap.setText("W")
        self.chk_wrap.setToolTip("Wrap Search")
        self.chk_wrap.setCheckable(True)
        self.chk_wrap.setFixedSize(26, 24)
        self.chk_wrap.setFocusPolicy(Qt.NoFocus)
        self.chk_wrap.setChecked(True)

        self.btn_close_search = QToolButton()
        self.btn_close_search.setText("X")
        self.btn_close_search.clicked.connect(self.hide_search_bar)

        self.search_info_label = QLabel("")
        self.search_info_label.setMinimumWidth(40) # Ensure a base width
        self.search_info_label.setContentsMargins(5, 0, 5, 0) # Add horizontal padding
        self.search_info_label.setAlignment(Qt.AlignCenter)

        self.search_layout.addWidget(self.search_input)
        self.search_layout.addWidget(self.chk_case)
        self.search_layout.addWidget(self.chk_wrap)
        self.search_layout.addWidget(self.btn_prev)
        self.search_layout.addWidget(self.btn_next)
        self.search_layout.addWidget(self.search_info_label)
        self.search_layout.addWidget(self.btn_close_search)

        # TODO: Resolve text visibility issue when Graphics Effects are enabled. 
        # Disabling both Shadow and Opacity for now to ensure functional search box.
        # shadow = QGraphicsDropShadowEffect(self.search_widget)
        # shadow.setBlurRadius(15)
        # shadow.setColor(QColor(0, 0, 0, 100))
        # shadow.setOffset(0, 2)
        # self.search_widget.setGraphicsEffect(shadow)

        # self.search_opacity_effect = QGraphicsOpacityEffect(self.search_widget)
        # self.search_widget.setGraphicsEffect(self.search_opacity_effect)
        # self.search_opacity_effect.setOpacity(0.95)

        # self.search_anim = QPropertyAnimation(self.search_opacity_effect, b"opacity")
        # self.search_anim.setDuration(200)

        self.search_widget.setFixedWidth(550)
        self.search_widget.hide()

        self.search_input.installEventFilter(self)
        self.search_input.lineEdit().installEventFilter(self)
        self.chk_case.installEventFilter(self)
        self.chk_wrap.installEventFilter(self)
        self.btn_prev.installEventFilter(self)
        self.btn_next.installEventFilter(self)
        self.search_widget.installEventFilter(self)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_bar.addWidget(self.status_label, 1)

        self.toast = Toast(self)
        self._create_menu()

        # Restore Dock State
        if self.settings.value("window_geometry"):
            self.restoreGeometry(self.settings.value("window_geometry"))
        if self.settings.value("window_state"):
            self.restoreState(self.settings.value("window_state"))

        self.apply_theme()

        self.btn_prev.clicked.connect(self.find_previous)
        self.btn_next.clicked.connect(self.find_next)

    def _create_menu(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        open_action = QAction("&Open Log...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file_dialog)
        file_menu.addAction(open_action)

        self.recent_menu = file_menu.addMenu("Open Recent")
        self.update_recent_menu()

        file_menu.addSeparator()
        load_filters_action = QAction("Load Filters...", self)
        load_filters_action.triggered.connect(self.import_filters)
        file_menu.addAction(load_filters_action)

        save_filters_action = QAction("Save Filters", self)
        save_filters_action.triggered.connect(self.quick_save_filters)
        file_menu.addAction(save_filters_action)

        save_filters_as_action = QAction("Save Filters As...", self)
        save_filters_as_action.triggered.connect(self.save_filters_as)
        file_menu.addAction(save_filters_as_action)

        file_menu.addSeparator()
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close_app)
        file_menu.addAction(exit_action)

        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self.filter_dock.toggleViewAction())
        
        toggle_notes_action = QAction("Toggle Notes", self)
        toggle_notes_action.triggered.connect(self.notes_manager.toggle_view)
        view_menu.addAction(toggle_notes_action)
        
        export_notes_action = QAction("Export Notes to Text...", self)
        export_notes_action.triggered.connect(self.export_notes_to_text)
        view_menu.addAction(export_notes_action)

        show_filtered_action = QAction("Show Filtered Only", self)
        show_filtered_action.setShortcut("Ctrl+H")
        show_filtered_action.setCheckable(True)
        show_filtered_action.triggered.connect(self.toggle_show_filtered_only)
        view_menu.addAction(show_filtered_action)
        self.show_filtered_action = show_filtered_action

        view_menu.addSeparator()
        toggle_theme_action = QAction("Toggle Dark/Light Mode", self)
        toggle_theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(toggle_theme_action)

        find_action = QAction("&Find...", self)
        find_action.setShortcut(QKeySequence.Find)
        find_action.triggered.connect(self.show_search_bar)
        self.addAction(find_action)
        view_menu.addAction(find_action)

        next_action = QAction("Find Next", self)
        next_action.setShortcut("F3")
        next_action.triggered.connect(self.find_next)
        self.addAction(next_action)
        prev_action = QAction("Find Previous", self)
        prev_action.setShortcut("F2")
        prev_action.triggered.connect(self.find_previous)
        self.addAction(prev_action)
        escape_action = QAction("Clear Search", self)
        escape_action.setShortcut("Esc")
        escape_action.triggered.connect(self.hide_search_bar)
        self.addAction(escape_action)

        copy_action = QAction("&Copy", self)
        copy_action.setShortcut(QKeySequence.Copy)
        copy_action.triggered.connect(self.copy_selection)
        self.addAction(copy_action)
        self.list_view.addAction(copy_action)

        edit_menu = menu_bar.addMenu("&Edit")
        edit_menu.addAction(copy_action)

        help_menu = menu_bar.addMenu("&Help")
        
        shortcuts_action = QAction("Keyboard Shortcuts", self)
        shortcuts_action.triggered.connect(self.show_shortcuts)
        help_menu.addAction(shortcuts_action)
        
        doc_action = QAction("Documentation", self)
        doc_action.triggered.connect(self.open_documentation)
        help_menu.addAction(doc_action)

        help_menu.addSeparator()
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def toggle_show_filtered_only(self):
        self.show_filtered_only = self.show_filtered_action.isChecked()
        # Toggle view should not invalidate cache, just re-apply cached results if available
        # But we need to update the view indices
        self.recalc_filters()

    def eventFilter(self, obj, event):
        if obj == self.list_view and event.type() == QEvent.Resize:
            self.update_scrollbar_range()
            return False # Don't consume, let list view handle layout

        if obj == self.list_view and event.type() == QEvent.Wheel:
            # Forward wheel events to custom scrollbar
            delta = event.angleDelta().y()
            # Standard step is 120 per notch. One notch = 3 lines?
            steps = -delta / 40 # Sensitivity
            current = self.v_scrollbar.value()
            self.v_scrollbar.setValue(current + steps)
            return True # Consume event

        if obj == self.list_view and event.type() == QEvent.KeyPress:
            key = event.key()
            mod = event.modifiers()
            
            # Virtual Viewport Navigation
            if key == Qt.Key_Down:
                idx = self.list_view.currentIndex()
                row = idx.row() if idx.isValid() else -1
                if row >= self.model.rowCount() - 1:
                    # At bottom of viewport, scroll down
                    self.v_scrollbar.setValue(self.v_scrollbar.value() + 1)
                    return True # Consume
            
            elif key == Qt.Key_Up:
                idx = self.list_view.currentIndex()
                row = idx.row() if idx.isValid() else -1
                if row <= 0:
                    # At top of viewport, scroll up
                    self.v_scrollbar.setValue(self.v_scrollbar.value() - 1)
                    return True # Consume

            elif key == Qt.Key_PageDown:
                self.v_scrollbar.setValue(self.v_scrollbar.value() + self.v_scrollbar.pageStep())
                return True
                
            elif key == Qt.Key_PageUp:
                self.v_scrollbar.setValue(self.v_scrollbar.value() - self.v_scrollbar.pageStep())
                return True

            elif key == Qt.Key_Home:
                # Home or Ctrl+Home -> Top of Log
                self.v_scrollbar.setValue(0)
                self.list_view.setCurrentIndex(self.model.index(0, 0))
                return True

            elif key == Qt.Key_End:
                # End or Ctrl+End -> Bottom of Log
                self.v_scrollbar.setValue(self.v_scrollbar.maximum())
                last = self.model.rowCount() - 1
                if last >= 0:
                    self.list_view.setCurrentIndex(self.model.index(last, 0))
                return True
            
            elif (mod & Qt.ControlModifier):
                 if key == Qt.Key_Left:
                    self.navigate_filter_hit(reverse=True)
                    return True
                 elif key == Qt.Key_Right:
                    self.navigate_filter_hit(reverse=False)
                    return True

            # 'C' key for Add/Edit Note
            elif key == Qt.Key_C and mod == Qt.NoModifier:
                idx = self.list_view.currentIndex()
                if idx.isValid():
                    view_abs_row = self.model.viewport_start + idx.row()
                    raw_index = view_abs_row
                    if self.show_filtered_only and self.model.filtered_indices:
                        if view_abs_row < len(self.model.filtered_indices):
                            raw_index = self.model.filtered_indices[view_abs_row]
                    
                    self.notes_manager.add_note(raw_index, "", self.current_log_path)
                    return True

        if hasattr(self, 'filter_tree') and obj == self.filter_tree and event.type() == QEvent.KeyPress:
            if event.modifiers() & Qt.ControlModifier:
                if event.key() == Qt.Key_Left:
                    self.navigate_filter_hit(reverse=True)
                    return True
                elif event.key() == Qt.Key_Right:
                    self.navigate_filter_hit(reverse=False)
                    return True
        if event.type() == QEvent.FocusIn: self._animate_search_opacity(0.95)
        elif event.type() == QEvent.FocusOut: QTimer.singleShot(10, self._check_search_focus)
        return super().eventFilter(obj, event)

    def _check_search_focus(self):
        fw = QApplication.focusWidget()
        if not fw: return
        if self.search_widget.isAncestorOf(fw) or fw == self.search_widget or fw == self.search_input.lineEdit():
            self._animate_search_opacity(0.95)
        else: self._animate_search_opacity(0.5)

    def calculate_viewport_size(self):
        h = self.list_view.viewport().height()
        if h <= 0: return 100
        
        row_height = QFontMetrics(self.list_view.font()).height()
        if row_height <= 0: row_height = 20
        
        # Buffer needs to be generous to handle resizing and scrolling gaps
        return (h // row_height) + 100 

    def on_scrollbar_value_changed(self, value):
        self.is_scrolling = True
        try:
            size = self.calculate_viewport_size()
            self.model.set_viewport(value, size)
        finally:
            self.is_scrolling = False

    def on_view_selection_changed(self, current, previous):
        if self.is_scrolling: return
        if not current.isValid(): return
        
        # Calculate raw index from visual index
        relative_row = current.row()
        view_abs_row = self.model.viewport_start + relative_row
        
        # Map to raw index
        raw_index = view_abs_row
        if self.show_filtered_only and self.model.filtered_indices:
            if view_abs_row < len(self.model.filtered_indices):
                raw_index = self.model.filtered_indices[view_abs_row]
        
        self.selected_raw_index = raw_index

    def update_scrollbar_range(self):
        if not self.current_engine: return
        
        # Get total count (filtered or full)
        if self.show_filtered_only and self.model.filtered_indices:
             total = len(self.model.filtered_indices)
        elif self.model.filtered_indices is not None and len(self.model.filtered_indices) == 0 and self.show_filtered_only:
             total = 0 # special case empty filter
        else:
             total = self.current_engine.line_count()

        vp_size = self.calculate_viewport_size()
        max_val = max(0, total - vp_size)
        
        self.v_scrollbar.setRange(0, max_val)
        self.v_scrollbar.setPageStep(vp_size)
        self.v_scrollbar.setSingleStep(1)

        # Trigger update of model viewport in case range changed but value didn't
        self.on_scrollbar_value_changed(self.v_scrollbar.value())

    def resizeEvent(self, event):
        # Update viewport size on resize
        self.update_scrollbar_range()
        
        if not self.toast.isHidden():
             txt = self.toast.label.text()
             txt = self.toast.label.text()
             self.toast.show_message(txt, duration=self.toast.timer.remainingTime())
        if not self.search_widget.isHidden():
            cw = self.centralWidget()
            sw_w = self.search_widget.width()
            x = cw.width() - sw_w - 20
            y = 0
            self.search_widget.move(x, y)
        super().resizeEvent(event)

    def _animate_search_opacity(self, target):
        pass
        # if self.search_opacity_effect.opacity() == target: return
        # self.search_anim.stop()
        # self.search_anim.setStartValue(self.search_opacity_effect.opacity())
        # self.search_anim.setEndValue(target)
        # self.search_anim.start()

    def toggle_theme(self):
        self.is_dark_mode = not self.is_dark_mode
        self.settings.setValue("dark_mode", self.is_dark_mode)
        self.apply_theme()
        # Refresh colors for filters immediately (unconditional)
        self.refresh_filter_tree()
        if self.current_engine and self.filters:
            # Theme change affects colors, but not line matches, so cache is still valid regarding indices/tags
            # But we need to regenerate the palette in the model
            self.recalc_filters(force_color_update=True)

    def update_status_bar(self, message):
        self.last_status_message = message
        self.status_label.setText(message)

    def _set_windows_title_bar_color(self, is_dark):
        set_windows_title_bar_color(self.winId(), is_dark)

        # Attempt to set for all top-level widgets (Dialogs, Floating Docks)
        for widget in QApplication.topLevelWidgets():
            if widget.isWindow() and widget != self:
                set_windows_title_bar_color(widget.winId(), is_dark)

    def apply_theme(self):
        self.notes_manager.set_theme(self.is_dark_mode)
        self.model.set_theme_mode(self.is_dark_mode)

        # Set Global Style to affect Dialogs
        app = QApplication.instance()

        if self.is_dark_mode:
            bg_color, fg_color, selection_bg, selection_fg = "#1e1e1e", "#d4d4d4", "#264f78", "#ffffff"
            hover_bg, scrollbar_bg, scrollbar_handle = "#2a2d2e", "#1e1e1e", "#424242"
            scrollbar_hover, menu_bg, menu_fg, menu_sel = "#4f4f4f", "#252526", "#cccccc", "#094771"
            bar_bg, bar_fg, input_bg, input_fg = "#007acc", "#ffffff", "#3c3c3c", "#cccccc"
            float_bg, float_border, dock_title_bg, tree_bg = "#252526", "#454545", "#252526", "#252526"
            # Dialog colors
            dialog_bg, dialog_fg = "#252526", "#cccccc"
        else:
            bg_color, fg_color, selection_bg, selection_fg = "#ffffff", "#000000", "#add6ff", "#000000"
            hover_bg, scrollbar_bg, scrollbar_handle = "#e8e8e8", "#f3f3f3", "#c1c1c1"
            scrollbar_hover, menu_bg, menu_fg, menu_sel = "#a8a8a8", "#f3f3f3", "#333333", "#0060c0"
            bar_bg, bar_fg, input_bg, input_fg = "#007acc", "#ffffff", "#ffffff", "#000000"
            float_bg, float_border, dock_title_bg, tree_bg = "#f3f3f3", "#cecece", "#f3f3f3", "#f3f3f3"
            dialog_bg, dialog_fg = "#f3f3f3", "#000000"

        self.delegate.set_hover_color(hover_bg)
        self.list_view.viewport().update()
        self._set_windows_title_bar_color(self.is_dark_mode)
        self.update_status_bar(self.last_status_message)

        style = f"""
        QMainWindow, QDialog {{ background-color: {bg_color}; color: {fg_color}; }}
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

        QDockWidget {{ color: {fg_color}; titlebar-close-icon: url(close.png); titlebar-normal-icon: url(float.png); }}
        QDockWidget::title {{ background: {dock_title_bg}; padding-left: 5px; }}
        QTreeWidget {{ background-color: {tree_bg}; border: none; color: {fg_color}; }}
        QHeaderView::section {{ background-color: {menu_bg}; color: {fg_color}; border: none; padding: 2px; }}

        /* Dialog specific */
        QDialog, QMessageBox {{ background-color: {dialog_bg}; color: {dialog_fg}; }}
        QLabel, QCheckBox, QMessageBox QLabel {{ color: {dialog_fg}; }}
        QLineEdit, QTextEdit, QPlainTextEdit {{ background-color: {input_bg}; color: {input_fg}; border: 1px solid #555; }}

        #search_widget {{
            background-color: {float_bg};
            border: 1px solid {float_border};
            border-top: none;
            border-bottom-left-radius: 5px;
            border-bottom-right-radius: 5px;
        }}
        QComboBox {{ background-color: {input_bg}; color: {input_fg}; border: 1px solid #555; padding: 2px; }}
        QComboBox QAbstractItemView {{ background-color: {menu_bg}; color: {menu_fg}; selection-background-color: {menu_sel}; }}
        QToolButton {{ background-color: transparent; color: {input_fg}; border: none; font-weight: bold; }}
        QToolButton:hover {{ background-color: {hover_bg}; border-radius: 3px; }}
        QToolButton:checked {{ background-color: {selection_bg}; color: {selection_fg}; border-radius: 3px; }}

        QCheckBox {{ spacing: 5px; }}
        QCheckBox::indicator {{ width: 13px; height: 13px; }}

        QPushButton {{ background-color: {menu_bg}; color: {fg_color}; border: 1px solid {float_border}; padding: 4px 12px; border-radius: 3px; }}
        QPushButton:hover {{ background-color: {hover_bg}; }}
        QPushButton:pressed {{ background-color: {selection_bg}; color: {selection_fg}; }}
        """
        app.setStyleSheet(style)

    # ... [Open/Load Log, Copy Selection, Resize Event, Search Logic - Same as before] ...
    def open_file_dialog(self):
        last_dir = self.settings.value("last_dir", "")
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Log File", last_dir, "Log Files (*.log *.txt);;All Files (*)")
        if filepath: self.load_log(filepath)

    def update_recent_menu(self):
        self.recent_menu.clear()
        recent_files = self.settings.value("recent_files", [], type=list)
        # Ensure list consistency
        recent_files = [str(f) for f in recent_files if f]
        
        has_items = False
        for fp in recent_files:
            if not os.path.exists(fp): continue
            has_items = True
            action = QAction(os.path.basename(fp), self)
            action.setToolTip(fp)
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

    def load_log(self, filepath):
        if self.notes_manager.has_unsaved_changes():
            reply = QMessageBox.question(self, "Save Notes?",
                                         "You have unsaved notes. Do you want to save them before loading a new log?",
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                         QMessageBox.Save)
            if reply == QMessageBox.Save:
                self.notes_manager.quick_save()
                if self.notes_manager.has_unsaved_changes(): return
            elif reply == QMessageBox.Cancel:
                return

        self.add_to_recent(filepath)
        # Switch to Log View
        self.central_stack.setCurrentIndex(1)
        self.update_status_bar(f"Loading {filepath}...")
        start_time = time.time()
        self.settings.setValue("last_dir", os.path.dirname(filepath))
        self.current_engine = get_engine(filepath)
        self.model.set_engine(self.current_engine, filepath)
        self.current_log_path = filepath
        self.notes_manager.load_notes_for_file(filepath)
        end_time = time.time()
        duration = end_time - start_time
        count = self.current_engine.line_count()
        
        self.delegate.set_max_line_number(count)

        self.update_window_title()

        self.update_status_bar(f"Shows {count:,} lines (Total {count:,})")
        self.toast.show_message(f"Loaded {count:,} lines in {duration:.3f}s", duration=4000)
        self.search_results = []
        self.current_match_index = -1
        self.search_info_label.setText("")
        
        # Reset Scrollbar
        self.update_scrollbar_range()
        self.v_scrollbar.setValue(0)

        self.filters_dirty_cache = True # New file, must re-filter
        # Do not clear filters, re-apply them
        if self.filters:
            self.recalc_filters()
        else:
            self.refresh_filter_tree()

    def show_context_menu(self, pos):
        menu = QMenu(self)
        copy_action = QAction("Copy", self)
        copy_action.triggered.connect(self.copy_selection)
        menu.addAction(copy_action)
        
        menu.addSeparator()
        
        # Check if single line selected
        indexes = self.list_view.selectionModel().selectedIndexes()
        if len(indexes) == 1:
            idx = indexes[0]
            # Map to raw index
            view_abs_row = self.model.viewport_start + idx.row()
            raw_index = view_abs_row
            if self.show_filtered_only and self.model.filtered_indices:
                if view_abs_row < len(self.model.filtered_indices):
                    raw_index = self.model.filtered_indices[view_abs_row]
            
            note_action = QAction("Add/Edit Note", self)
            note_action.triggered.connect(lambda: self.notes_manager.add_note(raw_index, "", self.current_log_path))
            menu.addAction(note_action)

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
        # Update viewport size on resize
        self.update_scrollbar_range()
        
        if not self.toast.isHidden():
             txt = self.toast.label.text()
             self.toast.show_message(txt, duration=self.toast.timer.remainingTime())
        if not self.search_widget.isHidden():
            cw = self.centralWidget()
            sw_w = self.search_widget.width()
            x = cw.width() - sw_w - 20
            y = 0
            self.search_widget.move(x, y)
        super().resizeEvent(event)

    def show_search_bar(self):
        if self.search_widget.isHidden():
            self.search_widget.show(); self.search_widget.raise_(); self.resizeEvent(None)
            self.search_input.setFocus(); self.search_input.lineEdit().selectAll()
            self._animate_search_opacity(0.95)
        else: self.search_input.setFocus(); self.search_input.lineEdit().selectAll()

    def hide_search_bar(self):
        self.search_widget.hide(); self.delegate.set_search_query(None, False); self.list_view.viewport().update()
        self.search_info_label.setText(""); self.list_view.setFocus()

    def find_next(self):
        query = self.search_input.currentText()
        if not query: return
        if self.delegate.search_query != query or not self.search_results: self._perform_search(query); return
        if not self.search_results: return
        
        # Calculate current RAW row index from view selection
        current_raw_row = -1
        idx = self.list_view.currentIndex()
        if idx.isValid():
            view_abs_row = self.model.viewport_start + idx.row()
            if self.show_filtered_only and self.model.filtered_indices:
                if view_abs_row < len(self.model.filtered_indices):
                    current_raw_row = self.model.filtered_indices[view_abs_row]
            else:
                current_raw_row = view_abs_row

        next_match_list_idx = bisect.bisect_right(self.search_results, current_raw_row)
        is_wrap = self.chk_wrap.isChecked()
        if next_match_list_idx >= len(self.search_results):
            if is_wrap: next_match_list_idx = 0; self.toast.show_message("Wrapped to top", duration=1000)
            else: self.toast.show_message("End of results", duration=1000); return
        self._jump_to_match(next_match_list_idx)

    def find_previous(self):
        query = self.search_input.currentText()
        if not query: return
        if self.delegate.search_query != query or not self.search_results: self._perform_search(query); return
        if not self.search_results: return
        
        # Calculate current RAW row index from view selection
        current_raw_row = -1
        idx = self.list_view.currentIndex()
        if idx.isValid():
            view_abs_row = self.model.viewport_start + idx.row()
            if self.show_filtered_only and self.model.filtered_indices:
                if view_abs_row < len(self.model.filtered_indices):
                    current_raw_row = self.model.filtered_indices[view_abs_row]
            else:
                current_raw_row = view_abs_row

        insertion_point = bisect.bisect_left(self.search_results, current_raw_row)
        prev_match_list_idx = insertion_point - 1
        is_wrap = self.chk_wrap.isChecked()
        if prev_match_list_idx < 0:
            if is_wrap: prev_match_list_idx = len(self.search_results) - 1; self.toast.show_message("Wrapped to bottom", duration=1000)
            else: self.toast.show_message("Start of results", duration=1000); return
        self._jump_to_match(prev_match_list_idx)

    def on_search_case_changed(self):
        query = self.search_input.currentText()
        if query:
            self._perform_search(query)

    def _perform_search(self, query):
        if not query or not self.current_engine: return
        self.toast.show_message(f"Searching for '{query}'...", duration=1000)
        self.update_status_bar("Searching...")
        QApplication.processEvents()
        is_case = self.chk_case.isChecked()
        results = self.current_engine.search(query, False, is_case)
        self.search_results = results
        self.current_match_index = -1
        self.delegate.set_search_query(query, is_case)
        self.list_view.viewport().update()
        self.update_status_bar(f"Found {len(results):,} matches")
        if results: self._jump_to_match(0)
        else: self.search_info_label.setText("No results"); self.toast.show_message("No results found", duration=2000)

    def on_notes_updated(self):
        self.list_view.viewport().update()

    def jump_to_raw_index(self, raw_index):
        # Determine visual absolute row
        view_abs_row = raw_index
        if self.show_filtered_only and self.model.filtered_indices:
             idx = bisect.bisect_left(self.model.filtered_indices, raw_index)
             if idx < len(self.model.filtered_indices) and self.model.filtered_indices[idx] == raw_index:
                 view_abs_row = idx
             else:
                 self.toast.show_message("Line is hidden by filter")
                 return

        vp_size = self.calculate_viewport_size()
        new_vp_start = max(0, view_abs_row - (vp_size // 2))
        
        self.v_scrollbar.setValue(new_vp_start)
        
        actual_vp_start = self.v_scrollbar.value()
        self.model.set_viewport(actual_vp_start, vp_size)
        
        QApplication.processEvents()

        relative_row = view_abs_row - actual_vp_start
        
        index = self.model.index(relative_row, 0)
        if index.isValid():
            self.list_view.clearSelection()
            self.list_view.setCurrentIndex(index)
            self.list_view.scrollTo(index, QAbstractItemView.PositionAtCenter)
            self.list_view.setFocus()
        else:
            self.toast.show_message(f"Nav Error: View {relative_row} invalid")

    def _jump_to_match(self, result_index):
        if not self.search_results or result_index < 0 or result_index >= len(self.search_results): return
        self.current_match_index = result_index
        raw_row_idx = self.search_results[result_index]
        self.jump_to_raw_index(raw_row_idx)
        self.search_info_label.setText(f"{result_index + 1} / {len(self.search_results)}")

    # --- Filter Logic ---
    def on_filter_tree_reordered(self):
        # Sync self.filters with the visual tree order after drag-and-drop
        new_filters = []
        root = self.filter_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            idx = item.data(0, Qt.UserRole)
            new_filters.append(self.filters[idx])
            # Update the item data to reflect the new index
            item.setData(0, Qt.UserRole, i)

        self.filters = new_filters
        self.filters_modified = True
        self.filters_dirty_cache = True # Order changes can affect priority
        self.update_window_title()
        self.recalc_filters()

    def refresh_filter_tree(self):
        self.filter_tree.blockSignals(True) # Prevent recursive signals during build
        self.filter_tree.clear()
        for i, flt in enumerate(self.filters):
            hits_str = str(flt.get("hits", 0))

            # Pattern Prefix
            prefix = ""
            if flt["is_exclude"]: prefix += "[x]"
            if flt["is_regex"]: prefix += "[R]"
            pattern_display = f"{prefix} {flt['text']}" if prefix else flt['text']

            item = QTreeWidgetItem(self.filter_tree)

            # En column as checkbox
            item.setFlags((item.flags() | Qt.ItemIsUserCheckable) & ~Qt.ItemIsDropEnabled)
            item.setCheckState(0, Qt.Checked if flt["enabled"] else Qt.Unchecked)

            item.setText(1, pattern_display)
            item.setText(2, hits_str)
            item.setData(0, Qt.UserRole, i)

            fg = adjust_color_for_theme(flt["fg_color"], False, self.is_dark_mode)
            bg = adjust_color_for_theme(flt["bg_color"], True, self.is_dark_mode)
            item.setForeground(1, QColor(fg))
            item.setBackground(1, QColor(bg))
        self.filter_tree.blockSignals(False)

    def on_filter_item_clicked(self, item, column):
        # Just update selected index for navigation
        if item:
            self.selected_filter_index = item.data(0, Qt.UserRole)

    def on_filter_item_changed(self, item, column):
        if column == 0 and item:
            idx = item.data(0, Qt.UserRole)
            # Ensure index is valid and within range
            if 0 <= idx < len(self.filters):
                new_state = (item.checkState(0) == Qt.Checked)
                if self.filters[idx]["enabled"] != new_state:
                    self.filters[idx]["enabled"] = new_state
                    self.filters_modified = True
                    self.filters_dirty_cache = True
                    self.update_window_title()
                    self.recalc_filters()

    def on_log_double_clicked(self, index):
        text = self.model.data(index, Qt.DisplayRole)
        if text:
            self.add_filter_dialog(initial_text=text.strip())

    def edit_selected_filter(self):
        item = self.filter_tree.currentItem()
        if not item: return
        idx = item.data(0, Qt.UserRole)
        flt = self.filters[idx]
        dialog = FilterDialog(self, flt)
        if dialog.exec():
            new_data = dialog.get_data()
            self.filters[idx].update(new_data)
            self.filters_modified = True
            self.filters_dirty_cache = True
            self.update_window_title()
            self.refresh_filter_tree()
            self.recalc_filters()

    def add_filter_dialog(self, initial_text=""):
        dialog = FilterDialog(self)
        if initial_text:
            dialog.pattern_edit.setText(initial_text)
        if dialog.exec():
            flt = dialog.get_data()
            flt["hits"] = 0
            self.filters.append(flt)
            self.filters_modified = True
            self.filters_dirty_cache = True
            self.update_window_title()
            self.refresh_filter_tree()
            self.recalc_filters()

    def remove_filter(self):
        item = self.filter_tree.currentItem()
        if not item: return
        idx = item.data(0, Qt.UserRole)
        del self.filters[idx]
        self.filters_modified = True
        self.filters_dirty_cache = True
        self.update_window_title()
        self.refresh_filter_tree()
        self.recalc_filters()

    def move_filter_top(self):
        item = self.filter_tree.currentItem()
        if not item: return
        idx = item.data(0, Qt.UserRole)
        if idx > 0:
            flt = self.filters.pop(idx)
            self.filters.insert(0, flt)
            self.filters_modified = True
            self.filters_dirty_cache = True
            self.update_window_title()
            self.refresh_filter_tree()
            self.filter_tree.setCurrentItem(self.filter_tree.topLevelItem(0))
            self.recalc_filters()

    def move_filter_bottom(self):
        item = self.filter_tree.currentItem()
        if not item: return
        idx = item.data(0, Qt.UserRole)
        if idx < len(self.filters) - 1:
            flt = self.filters.pop(idx)
            self.filters.append(flt)
            self.filters_modified = True
            self.filters_dirty_cache = True
            self.update_window_title()
            self.refresh_filter_tree()
            self.filter_tree.setCurrentItem(self.filter_tree.topLevelItem(len(self.filters)-1))
            self.recalc_filters()

    def closeEvent(self, event):
        try:
            if self.filters_modified and self.filters:
                reply = QMessageBox.question(self, "Save Filters?",
                                             "You have unsaved filter changes. Do you want to save them?",
                                             QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                             QMessageBox.Save)
                if reply == QMessageBox.Save:
                    self.quick_save_filters()
                    if self.filters_modified: # If cancel inside save dialog
                         event.ignore()
                         return
                elif reply == QMessageBox.Cancel:
                    event.ignore()
                    return

            if self.notes_manager.has_unsaved_changes():
                reply = QMessageBox.question(self, "Save Notes?",
                                             "You have unsaved notes. Do you want to save them?",
                                             QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
                                             QMessageBox.Save)
                if reply == QMessageBox.Save:
                    self.notes_manager.quick_save()
                    if self.notes_manager.has_unsaved_changes():
                         event.ignore()
                         return
                elif reply == QMessageBox.Cancel:
                    event.ignore()
                    return

            self.settings.setValue("window_geometry", self.saveGeometry())
            self.settings.setValue("window_state", self.saveState())
            super().closeEvent(event)
        except Exception as e:
            # Handle cases like KeyboardInterrupt during close
            pass

    def close_app(self):
        self.close()

    def show_filter_menu(self, pos):
        item = self.filter_tree.itemAt(pos)
        menu = QMenu(self)
        add_action = QAction("Add Filter", self)
        add_action.triggered.connect(self.add_filter_dialog)
        menu.addAction(add_action)
        if item:
            menu.addSeparator()
            edit_action = QAction("Edit Filter", self)
            edit_action.triggered.connect(self.edit_selected_filter)
            menu.addAction(edit_action)
            rem_action = QAction("Remove Filter", self)
            rem_action.triggered.connect(self.remove_filter)
            menu.addAction(rem_action)
            menu.addSeparator()
            top_action = QAction("Move to Top", self)
            top_action.triggered.connect(self.move_filter_top)
            menu.addAction(top_action)
            bot_action = QAction("Move to Bottom", self)
            bot_action.triggered.connect(self.move_filter_bottom)
            menu.addAction(bot_action)
            idx = item.data(0, Qt.UserRole)
            is_enabled = self.filters[idx]["enabled"]
            toggle_txt = "Disable" if is_enabled else "Enable"
            toggle_action = QAction(toggle_txt, self)
            def toggle_func():
                self.filters[idx]["enabled"] = not is_enabled
                self.filters_dirty_cache = True
                self.refresh_filter_tree()
                self.recalc_filters()
            toggle_action.triggered.connect(toggle_func)
            menu.addAction(toggle_action)
        menu.exec_(self.filter_tree.mapToGlobal(pos))

    # --- TAT I/O ---
    def import_filters(self):
        last_dir = self.settings.value("last_filter_dir", "")
        filepath, _ = QFileDialog.getOpenFileName(self, "Import Filters", last_dir, "TextAnalysisTool (*.tat);;All Files (*)")
        if filepath:
            self.settings.setValue("last_filter_dir", os.path.dirname(filepath))
            loaded = load_tat_filters(filepath)
            if loaded is not None:
                self.filters = loaded
                self.current_filter_file = filepath
                self.filters_modified = False
                self.filters_dirty_cache = True

                self.update_window_title()
                self.refresh_filter_tree()
                self.recalc_filters()
                self.toast.show_message(f"Imported {len(loaded)} filters")

    def quick_save_filters(self):
        if self.current_filter_file:
            if save_tat_filters(self.current_filter_file, self.filters):
                self.filters_modified = False
                self.update_window_title()
                self.toast.show_message("Filters saved")
        else:
            self.save_filters_as()

    def export_notes_to_text(self):
        last_dir = self.settings.value("last_note_export_dir", "")
        filepath, _ = QFileDialog.getSaveFileName(self, "Export Notes", last_dir, "Text Files (*.txt);;All Files (*)")
        if filepath:
            self.settings.setValue("last_note_export_dir", os.path.dirname(filepath))
            self.notes_manager.export_to_text(filepath)

    def save_filters_as(self):
        last_dir = self.settings.value("last_filter_dir", "")
        filepath, _ = QFileDialog.getSaveFileName(self, "Save Filters As", last_dir, "TextAnalysisTool (*.tat);;All Files (*)")
        if filepath:
            self.settings.setValue("last_filter_dir", os.path.dirname(filepath))
            if save_tat_filters(filepath, self.filters):
                self.current_filter_file = filepath
                self.filters_modified = False
                self.update_window_title()
                self.toast.show_message("Filters saved")

    def update_window_title(self):
        parts = []
        if self.current_log_path:
            parts.append(os.path.basename(self.current_log_path))

        if self.current_filter_file:
            filter_name = os.path.basename(self.current_filter_file)
            if self.filters_modified:
                filter_name = "*" + filter_name
            parts.append(filter_name)
        elif self.filters_modified:
             parts.append("*Unsaved Filters")

        parts.append(f"{self.APP_NAME} {self.VERSION}")
        self.setWindowTitle(" - ".join(parts))

    def navigate_filter_hit(self, reverse=False):
        if not self.current_engine or not self.model.tag_codes:
            return

        if self.selected_filter_index < 0 or self.selected_filter_index >= len(self.filters):
            self.toast.show_message("Select a filter to navigate")
            return

        target_filter_idx = self.selected_filter_index

        # Determine the target code used in tag_codes
        target_code = -1
        current_j = 0
        for i, f in enumerate(self.filters):
            if f["enabled"]:
                if i == target_filter_idx:
                    target_code = current_j + 2
                    break
                current_j += 1

        if target_code == -1:
            self.toast.show_message("Selected filter is disabled")
            return

        # Use internal state for reliable navigation source
        start_raw_index = -1
        
        # Priority: Selected Raw Index > Current View Selection > Viewport Top
        if self.selected_raw_index != -1:
             start_raw_index = self.selected_raw_index
        else:
             idx = self.list_view.currentIndex()
             if idx.isValid():
                 start_raw_index = self.model.viewport_start + idx.row()
                 # Map if filtered
                 if self.show_filtered_only and self.model.filtered_indices:
                     if start_raw_index < len(self.model.filtered_indices):
                         start_raw_index = self.model.filtered_indices[start_raw_index]
             else:
                 start_raw_index = self.model.viewport_start
                 if self.show_filtered_only and self.model.filtered_indices:
                     if start_raw_index < len(self.model.filtered_indices):
                         start_raw_index = self.model.filtered_indices[start_raw_index]

        count = len(self.model.tag_codes)
        found_row = -1

        if reverse:
            # Look backwards
            for r in range(start_raw_index - 1, -1, -1):
                if self.model.tag_codes[r] == target_code:
                    found_row = r
                    break
        else:
            # Look forward
            for r in range(start_raw_index + 1, count):
                if self.model.tag_codes[r] == target_code:
                    found_row = r
                    break

        if found_row != -1:
            # Update internal state immediately
            self.selected_raw_index = found_row
            
            # found_row is a RAW index.
            # We need to convert it to VIEW index (absolute) first.
            view_row = found_row
            if self.show_filtered_only and self.model.filtered_indices:
                idx = bisect.bisect_left(self.model.filtered_indices, found_row)
                if idx < len(self.model.filtered_indices) and self.model.filtered_indices[idx] == found_row:
                    view_row = idx
                else:
                    return # Should not happen

            # --- Virtual Viewport Adjustment ---
            # Calculate new viewport start to center the found row
            vp_size = self.calculate_viewport_size()
            new_vp_start = max(0, view_row - (vp_size // 2))
            
            # Update Scrollbar (this triggers model update via signal)
            self.v_scrollbar.setValue(new_vp_start)
            
            # Now calculate the relative row index within the new viewport
            # Note: v_scrollbar.value() might be clamped by its range, so read it back
            actual_vp_start = self.v_scrollbar.value()
            relative_row = view_row - actual_vp_start
            
            # Select the item
            index = self.model.index(relative_row, 0)
            if index.isValid():
                self.list_view.clearSelection()
                self.list_view.setCurrentIndex(index)
                self.list_view.scrollTo(index, QAbstractItemView.PositionAtCenter) # Local scroll within viewport
                self.list_view.setFocus() # Ensure focus for keyboard nav
                self.toast.show_message(f"Jumped to line {found_row+1}")
        else:
            self.toast.show_message("No more matches for this filter")

    def recalc_filters(self, force_color_update=False):
        if not self.current_engine: return
        if not hasattr(self.current_engine, 'filter'): return

        # Optimization: Only run engine filter if filters have actually changed
        if self.filters_dirty_cache:
            self.update_status_bar("Filtering...")
            QApplication.processEvents()

            rust_filters = []
            for i, f in enumerate(self.filters):
                if f["enabled"]:
                    rust_filters.append((f["text"], f["is_regex"], f["is_exclude"], False, i))

            try:
                start_t = time.time()
                # Returns: tag_codes, filtered_indices, subset_counts, timeline_events
                res = self.current_engine.filter(rust_filters)
                dur = time.time() - start_t

                self.cached_filter_results = (res, rust_filters)
                self.filters_dirty_cache = False
                self.toast.show_message(f"Filter applied in {dur:.3f}s")

            except Exception as e:
                print(f"Filter Error: {e}")
                self.toast.show_message("Filter Error")
                return

        # If we have results (cached or new)
        if self.cached_filter_results:
            res, rust_filters = self.cached_filter_results

            if len(res) >= 3:
                tag_codes = res[0]
                filtered_indices = res[1]
                subset_counts = res[2]

                # Update hits
                for j, rf in enumerate(rust_filters):
                    orig_idx = rf[4]
                    if j < len(subset_counts):
                        self.filters[orig_idx]["hits"] = subset_counts[j]

                # Colors map (Strings, let Model create QColor)
                code_to_filter = {}
                for j, rf in enumerate(rust_filters):
                    orig_idx = rf[4]
                    code_to_filter[j+2] = self.filters[orig_idx]

                palette = {}
                for code, flt in code_to_filter.items():
                    fg = adjust_color_for_theme(flt["fg_color"], False, self.is_dark_mode)
                    bg = adjust_color_for_theme(flt["bg_color"], True, self.is_dark_mode)
                    palette[code] = (fg, bg)

                # Determine indices to show based on mode
                indices_to_set = None
                if self.show_filtered_only and rust_filters:
                    indices_to_set = filtered_indices

                # Atomically update model to avoid double refresh
                self.model.update_filter_result(tag_codes, palette, indices_to_set)

                self.update_scrollbar_range()
                # self.v_scrollbar.setValue(0) # Optional: reset scroll on filter change

                # Refresh tree to show hits
                if not force_color_update:
                     self.refresh_filter_tree()

                # Update Status Bar
                total_lines = self.current_engine.line_count()
                if indices_to_set is not None:
                    self.update_status_bar(f"Filtered: {len(indices_to_set):,} lines (Total {total_lines:,})")
                else:
                    self.update_status_bar(f"Shows {total_lines:,} lines")

    def show_shortcuts(self):
        shortcuts = [
            ("General", ""),
            ("Ctrl + O", "Open Log File"),
            ("Ctrl + Q", "Exit Application"),
            ("", ""),
            ("View & Navigation", ""),
            ("Ctrl + F", "Open Find Bar"),
            ("Esc", "Close Find Bar / Clear Selection"),
            ("Ctrl + H", "Toggle Show Filtered Only"),
            ("F2 / F3", "Find Previous / Next"),
            ("Ctrl + Left / Right", "Navigate Filter Hits (Selected Filter)"),
            ("Home / End", "Jump to Start / End of Log"),
            ("", ""),
            ("Log View", ""),
            ("Double-Click", "Create Filter from selected text"),
            ("'C' key", "Add / Edit Note for current line"),
            ("Ctrl + C", "Copy selected lines"),
            ("", ""),
            ("Filters", ""),
            ("Delete", "Remove selected filter"),
            ("Double-Click", "Edit filter properties"),
            ("Space", "Toggle filter enabled/disabled"),
        ]
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Keyboard Shortcuts")
        dialog.resize(550, 600)
        layout = QVBoxLayout(dialog)
        
        tree = QTreeWidget()
        tree.setHeaderLabels(["Key", "Description"])
        tree.setRootIsDecorated(False)
        tree.setAlternatingRowColors(True)
        
        for key, desc in shortcuts:
            item = QTreeWidgetItem(tree)
            if not key and not desc:
                # item.setFlags(Qt.NoItemFlags)
                pass
            elif not desc:
                # Category Header
                item.setText(0, key)
                bg = QColor(60, 60, 60) if self.is_dark_mode else QColor(230, 230, 230)
                item.setBackground(0, bg)
                item.setBackground(1, bg)
                font = item.font(0)
                font.setBold(True)
                item.setFont(0, font)
            else:
                item.setText(0, key)
                item.setText(1, desc)
        
        tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        layout.addWidget(tree)
        
        btn = QPushButton("Close")
        btn.clicked.connect(dialog.accept)
        layout.addWidget(btn)
        
        set_windows_title_bar_color(dialog.winId(), self.is_dark_mode)
        dialog.exec()

    def show_about(self):
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("About")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(f"<h3>{self.APP_NAME} {self.VERSION}</h3>"
                        f"<p>A high-performance log analysis tool built with PySide6 and Rust extension.</p>"
                        f"<p>Developer: Gary Hsieh</p>")
        msg_box.setStandardButtons(QMessageBox.Ok)
        
        # Ensure title bar color matches theme
        set_windows_title_bar_color(msg_box.winId(), self.is_dark_mode)
        
        msg_box.exec()

    def open_documentation(self):
        doc_filename = f"Log_Analyzer_{self.VERSION}_Docs_EN.html"
        # Path logic: root/Doc/filename
        doc_path = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "Doc", doc_filename))
        
        if not os.path.exists(doc_path):
            QMessageBox.warning(self, "Error", f"Documentation file not found:\n{doc_path}")
            return
            
        import webbrowser
        webbrowser.open(f"file://{doc_path}")
