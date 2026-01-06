from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QListView,
                               QLabel, QFileDialog, QMenuBar, QMenu, QStatusBar, QAbstractItemView, QApplication,
                               QHBoxLayout, QLineEdit, QToolButton, QComboBox, QSizePolicy, QGraphicsDropShadowEffect,
                               QGraphicsOpacityEffect, QCheckBox, QDockWidget, QTreeWidget, QTreeWidgetItem, QHeaderView)
from PySide6.QtGui import QAction, QFont, QPalette, QColor, QKeySequence, QCursor, QIcon, QShortcut
from PySide6.QtCore import Qt, QSettings, QTimer, Slot, QModelIndex, QEvent, QPropertyAnimation
from .models import LogModel
from .engine_wrapper import get_engine
from .toast import Toast
from .delegates import LogDelegate
from .filter_dialog import FilterDialog
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

        self.settings = QSettings("LogAnalyzer", "QtApp")
        self.is_dark_mode = self.settings.value("dark_mode", True, type=bool)
        self.last_status_message = "Ready"

        self.current_engine = None
        self.search_results = []
        self.current_match_index = -1
        self.search_history = []
        self.filters = []
        self.show_filtered_only = False

        self.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks | QMainWindow.AllowTabbedDocks)

        self.list_view = QListView()
        self.model = LogModel()
        self.list_view.setModel(self.model)

        self.delegate = LogDelegate(self.list_view)
        self.list_view.setItemDelegate(self.delegate)

        self.list_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_view.customContextMenuRequested.connect(self.show_context_menu)

        self.list_view.setUniformItemSizes(True)
        self.list_view.setLayoutMode(QListView.Batched)
        self.list_view.setBatchSize(100)

        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.Monospace)
        self.list_view.setFont(font)

        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.addWidget(self.list_view)
        self.setCentralWidget(central_widget)

        # --- Filter Panel ---
        self.filter_dock = QDockWidget("Filters", self)
        self.filter_dock.setObjectName("FilterDock")
        self.filter_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea | Qt.BottomDockWidgetArea)

        self.filter_tree = QTreeWidget()
        self.filter_tree.setHeaderLabels(["En", "Type", "Pattern", "Hits"])
        # Fix: ResizeToContents for first column to prevent overlap
        self.filter_tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.filter_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.filter_tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)

        self.filter_tree.setDragDropMode(QAbstractItemView.InternalMove)
        self.filter_tree.setSelectionMode(QAbstractItemView.SingleSelection)
        self.filter_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.filter_tree.customContextMenuRequested.connect(self.show_filter_menu)
        self.filter_tree.itemDoubleClicked.connect(self.edit_selected_filter)
        self.filter_tree.itemClicked.connect(self.on_filter_item_clicked) # Fix: Handle clicks

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
        self.btn_prev.setText("<")
        self.btn_next = QToolButton()
        self.btn_next.setText(">")
        self.chk_case = QCheckBox("Aa")
        self.chk_wrap = QCheckBox("Wrap")
        self.chk_wrap.setChecked(True)

        self.btn_close_search = QToolButton()
        self.btn_close_search.setText("X")
        self.btn_close_search.clicked.connect(self.hide_search_bar)

        self.search_info_label = QLabel("")
        self.search_info_label.setFixedWidth(100)
        self.search_info_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self.search_layout.addWidget(self.search_input)
        self.search_layout.addWidget(self.chk_case)
        self.search_layout.addWidget(self.chk_wrap)
        self.search_layout.addWidget(self.btn_prev)
        self.search_layout.addWidget(self.btn_next)
        self.search_layout.addWidget(self.search_info_label)
        self.search_layout.addWidget(self.btn_close_search)

        shadow = QGraphicsDropShadowEffect(self.search_widget)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 2)
        self.search_widget.setGraphicsEffect(shadow)

        self.search_opacity_effect = QGraphicsOpacityEffect(self.search_widget)
        self.search_widget.setGraphicsEffect(self.search_opacity_effect)
        self.search_opacity_effect.setOpacity(0.95)

        self.search_anim = QPropertyAnimation(self.search_opacity_effect, b"opacity")
        self.search_anim.setDuration(200)

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
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        view_menu = menu_bar.addMenu("&View")
        view_menu.addAction(self.filter_dock.toggleViewAction())

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

    def toggle_show_filtered_only(self):
        self.show_filtered_only = self.show_filtered_action.isChecked()
        self.recalc_filters()

    # ... [Event Filters, Opacity, Theme, Copy logic same as before, abbreviated] ...
    def eventFilter(self, obj, event):
        if event.type() == QEvent.FocusIn:
            self._animate_search_opacity(0.95)
        elif event.type() == QEvent.FocusOut:
            QTimer.singleShot(10, self._check_search_focus)
        return super().eventFilter(obj, event)

    def _check_search_focus(self):
        fw = QApplication.focusWidget()
        if not fw: return
        if self.search_widget.isAncestorOf(fw) or fw == self.search_widget or fw == self.search_input.lineEdit():
            self._animate_search_opacity(0.95)
        else:
            self._animate_search_opacity(0.5)

    def _animate_search_opacity(self, target):
        if self.search_opacity_effect.opacity() == target: return
        self.search_anim.stop()
        self.search_anim.setStartValue(self.search_opacity_effect.opacity())
        self.search_anim.setEndValue(target)
        self.search_anim.start()

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
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
        except Exception: pass

    def apply_theme(self):
        if self.is_dark_mode:
            bg_color, fg_color, selection_bg, selection_fg = "#1e1e1e", "#d4d4d4", "#264f78", "#ffffff"
            hover_bg, scrollbar_bg, scrollbar_handle = "#2a2d2e", "#1e1e1e", "#424242"
            scrollbar_hover, menu_bg, menu_fg, menu_sel = "#4f4f4f", "#252526", "#cccccc", "#094771"
            bar_bg, bar_fg, input_bg, input_fg = "#007acc", "#ffffff", "#3c3c3c", "#cccccc"
            float_bg, float_border, dock_title_bg, tree_bg = "#252526", "#454545", "#252526", "#252526"
        else:
            bg_color, fg_color, selection_bg, selection_fg = "#ffffff", "#000000", "#add6ff", "#000000"
            hover_bg, scrollbar_bg, scrollbar_handle = "#e8e8e8", "#f3f3f3", "#c1c1c1"
            scrollbar_hover, menu_bg, menu_fg, menu_sel = "#a8a8a8", "#f3f3f3", "#333333", "#0060c0"
            bar_bg, bar_fg, input_bg, input_fg = "#007acc", "#ffffff", "#ffffff", "#000000"
            float_bg, float_border, dock_title_bg, tree_bg = "#f3f3f3", "#cecece", "#f3f3f3", "#f3f3f3"

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

        QDockWidget {{ color: {fg_color}; titlebar-close-icon: url(close.png); titlebar-normal-icon: url(float.png); }}
        QDockWidget::title {{ background: {dock_title_bg}; padding-left: 5px; }}
        QTreeWidget {{ background-color: {tree_bg}; border: none; color: {fg_color}; }}
        QHeaderView::section {{ background-color: {menu_bg}; color: {fg_color}; border: none; padding: 2px; }}

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
        QCheckBox {{ spacing: 5px; }}
        QCheckBox::indicator {{ width: 13px; height: 13px; }}
        """
        self.setStyleSheet(style)

    def open_file_dialog(self):
        last_dir = self.settings.value("last_dir", "")
        filepath, _ = QFileDialog.getOpenFileName(self, "Open Log File", last_dir, "Log Files (*.log *.txt);;All Files (*)")
        if filepath: self.load_log(filepath)

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
        self.search_results = []
        self.current_match_index = -1
        self.search_info_label.setText("")
        self.filters.clear()
        self.refresh_filter_tree()

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

    # ... [Search logic same as before, abbreviated] ...
    def show_search_bar(self):
        if self.search_widget.isHidden():
            self.search_widget.show(); self.search_widget.raise_(); self.resizeEvent(None)
            self.search_input.setFocus(); self.search_input.lineEdit().selectAll()
            self._animate_search_opacity(0.95)
        else:
            self.search_input.setFocus(); self.search_input.lineEdit().selectAll()

    def hide_search_bar(self):
        self.search_widget.hide(); self.delegate.set_search_query(None); self.list_view.viewport().update()
        self.search_info_label.setText(""); self.list_view.setFocus()

    def find_next(self):
        query = self.search_input.currentText()
        if not query: return
        if self.delegate.search_query != query or not self.search_results:
            self._perform_search(query); return
        if not self.search_results: return
        current_row = self.list_view.currentIndex().row()
        next_match_list_idx = bisect.bisect_right(self.search_results, current_row)
        is_wrap = self.chk_wrap.isChecked()
        if next_match_list_idx >= len(self.search_results):
            if is_wrap: next_match_list_idx = 0; self.toast.show_message("Wrapped to top", duration=1000)
            else: self.toast.show_message("End of results", duration=1000); return
        self._jump_to_match(next_match_list_idx)

    def find_previous(self):
        query = self.search_input.currentText()
        if not query: return
        if self.delegate.search_query != query or not self.search_results:
            self._perform_search(query); return
        if not self.search_results: return
        current_row = self.list_view.currentIndex().row()
        insertion_point = bisect.bisect_left(self.search_results, current_row)
        prev_match_list_idx = insertion_point - 1
        is_wrap = self.chk_wrap.isChecked()
        if prev_match_list_idx < 0:
            if is_wrap: prev_match_list_idx = len(self.search_results) - 1; self.toast.show_message("Wrapped to bottom", duration=1000)
            else: self.toast.show_message("Start of results", duration=1000); return
        self._jump_to_match(prev_match_list_idx)

    def _perform_search(self, query):
        if not query or not self.current_engine: return
        self.toast.show_message(f"Searching for '{query}'...", duration=1000)
        self.update_status_bar("Searching...")
        QApplication.processEvents()
        is_case = self.chk_case.isChecked()
        results = self.current_engine.search(query, False, is_case)
        self.search_results = results
        self.current_match_index = -1
        self.delegate.set_search_query(query)
        self.list_view.viewport().update()
        self.update_status_bar(f"Found {len(results):,} matches")
        if results: self._jump_to_match(0)
        else: self.search_info_label.setText("No results"); self.toast.show_message("No results found", duration=2000)

    def _jump_to_match(self, result_index):
        if not self.search_results or result_index < 0 or result_index >= len(self.search_results): return
        self.current_match_index = result_index
        row_idx = self.search_results[result_index]
        index = self.model.index(row_idx, 0)
        if index.isValid():
            self.list_view.scrollTo(index, QAbstractItemView.PositionAtCenter)
            self.list_view.setCurrentIndex(index)
            self.list_view.setFocus()
        self.search_info_label.setText(f"{result_index + 1} / {len(self.search_results)}")

    # --- Filter Logic ---

    def refresh_filter_tree(self):
        self.filter_tree.clear()
        for i, flt in enumerate(self.filters):
            # flt is dict: {text, is_regex, is_exclude, fg_color, bg_color, enabled}
            en_char = "☑" if flt["enabled"] else "☐"
            type_str = "Excl" if flt["is_exclude"] else ("Regex" if flt["is_regex"] else "Text")
            hits_str = str(flt.get("hits", 0))

            item = QTreeWidgetItem(self.filter_tree)
            item.setText(0, en_char)
            item.setText(1, type_str)
            item.setText(2, flt["text"])
            item.setText(3, hits_str)
            item.setData(0, Qt.UserRole, i)

            # Use color from filter, apply only to Pattern column
            fg = QColor(flt["fg_color"])
            bg = QColor(flt["bg_color"])
            item.setForeground(2, fg)
            item.setBackground(2, bg)

    def on_filter_item_clicked(self, item, column):
        # Allow toggling check on the first column
        if column == 0:
            idx = item.data(0, Qt.UserRole)
            self.filters[idx]["enabled"] = not self.filters[idx]["enabled"]
            self.refresh_filter_tree()
            self.recalc_filters()

    def edit_selected_filter(self):
        item = self.filter_tree.currentItem()
        if not item: return
        idx = item.data(0, Qt.UserRole)
        flt = self.filters[idx]

        dialog = FilterDialog(self, flt)
        if dialog.exec():
            new_data = dialog.get_data()
            self.filters[idx].update(new_data)
            self.refresh_filter_tree()
            self.recalc_filters()

    def add_filter_dialog(self):
        dialog = FilterDialog(self)
        if dialog.exec():
            flt = dialog.get_data()
            flt["hits"] = 0
            self.filters.append(flt)
            self.refresh_filter_tree()
            self.recalc_filters()

    def remove_filter(self):
        item = self.filter_tree.currentItem()
        if not item: return
        idx = item.data(0, Qt.UserRole)
        del self.filters[idx]
        self.refresh_filter_tree()
        self.recalc_filters()

    def move_filter_top(self):
        item = self.filter_tree.currentItem()
        if not item: return
        idx = item.data(0, Qt.UserRole)
        if idx > 0:
            flt = self.filters.pop(idx)
            self.filters.insert(0, flt)
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
            self.refresh_filter_tree()
            self.filter_tree.setCurrentItem(self.filter_tree.topLevelItem(len(self.filters)-1))
            self.recalc_filters()

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
                self.refresh_filter_tree()
                self.recalc_filters()
            toggle_action.triggered.connect(toggle_func)
            menu.addAction(toggle_action)
        menu.exec_(self.filter_tree.mapToGlobal(pos))

    def recalc_filters(self):
        if not self.current_engine: return
        if not hasattr(self.current_engine, 'filter'): return

        self.update_status_bar("Filtering...")
        QApplication.processEvents()

        rust_filters = []
        for i, f in enumerate(self.filters):
            if f["enabled"]:
                # (text, is_regex, is_exclude, is_event, original_idx)
                rust_filters.append((f["text"], f["is_regex"], f["is_exclude"], False, i))

        try:
            start_t = time.time()
            res = self.current_engine.filter(rust_filters)
            dur = time.time() - start_t

            if len(res) == 4:
                tag_codes, filtered_indices, subset_counts, _ = res

                for j, rf in enumerate(rust_filters):
                    orig_idx = rf[4]
                    if j < len(subset_counts):
                        self.filters[orig_idx]["hits"] = subset_counts[j]

                # Colors map: raw_index -> (fg, bg)
                # tag_codes[raw_idx] = filter_index + 2 (0=None, 1=Exclude)
                # We iterate tag_codes to build map
                color_map = {}

                # Note: tag_codes corresponds to raw lines.
                # If we filter indices, we still need colors for visible lines.
                # The engine should return tag_codes for all lines or we iterate.
                # Assuming tag_codes is list of u8 same length as raw lines.

                # Map codes back to filter colors
                # Code 2 = rust_filters[0], Code 3 = rust_filters[1]...
                code_to_filter = {}
                for j, rf in enumerate(rust_filters):
                    orig_idx = rf[4]
                    code_to_filter[j+2] = self.filters[orig_idx]

                # Optimization: Only build map if needed or process on demand in model?
                # Building a dict for 1M lines is expensive.
                # Better: Model stores tag_codes and map, and looks up on fly.
                # But current Model expects dict. Let's optimize: Model stores tag_codes list directly.

                # Wait, transferring 1M items list from Rust to Python is the bottleneck we avoided with Flet.
                # Does `filter` return full tag_codes list? Yes in previous impl.
                # If it's a list of ints, it's fast enough in PySide6 usually.

                # Actually, let's update Model to accept tag_codes and the filter definitions to resolve colors.
                # Passing `color_map` (dict) is too memory heavy for 1M lines.

                # Updating logic to use tag_codes directly.
                # For now, let's stick to the plan: pass colors.
                # But wait, building `color_map` here is huge.
                # Let's pass `tag_codes` and `filter_palette` to model.

                # Refined Plan implemented here:
                # 1. Construct palette: {code: (fg, bg)}
                palette = {}
                for code, flt in code_to_filter.items():
                    palette[code] = (flt["fg_color"], flt["bg_color"])

                # 2. Pass tags and palette to model
                self.model.set_filter_data(tag_codes, palette)

                # Update Hits UI
                self.refresh_filter_tree()

                if self.show_filtered_only and rust_filters:
                    self.model.set_filtered_indices(filtered_indices)
                    self.update_status_bar(f"Filtered: {len(filtered_indices):,} lines (Total {self.current_engine.line_count():,})")
                else:
                    self.model.set_filtered_indices(None)
                    self.update_status_bar(f"Shows {self.current_engine.line_count():,} lines")

                self.toast.show_message(f"Filter applied in {dur:.3f}s")

        except Exception as e:
            print(f"Filter Error: {e}")
            self.toast.show_message("Filter Error")
