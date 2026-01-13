from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QStackedWidget,
    QComboBox, QCheckBox, QSpinBox, QGroupBox, QFrame, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont, QFontDatabase
from log_analyzer.modern_dialog import ModernDialog
from log_analyzer.config import get_config
from log_analyzer.resources import get_svg_icon

class PreferencesDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__(parent, title="Preferences", fixed_size=(750, 600))
        self.config = get_config()
        self.init_ui()

    def init_ui(self):
        # Create main layout container
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        content_row = QWidget()
        main_layout = QHBoxLayout(content_row)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Sidebar (Categories)
        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(200)
        self.sidebar.setFrameShape(QFrame.NoFrame)
        self.sidebar.setSpacing(4)
        
        # Add categories with icons
        self.add_sidebar_item("General", "settings")
        self.add_sidebar_item("Log View", "file-text")
        self.add_sidebar_item("Appearance", "sun-moon")
        
        self.sidebar.currentRowChanged.connect(self.change_page)

        # 2. Content Area (Stacked Widget)
        self.pages = QStackedWidget()
        
        # Add pages
        self.pages.addWidget(self.create_general_page())
        self.pages.addWidget(self.create_log_view_page())
        self.pages.addWidget(self.create_appearance_page())

        main_layout.addWidget(self.sidebar)
        main_layout.addWidget(self.pages)

        # 3. Bottom Action Bar
        bottom_bar = QFrame()
        bottom_bar.setObjectName("bottom_bar")
        bottom_bar.setFixedHeight(70)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(25, 0, 25, 0)
        
        self.btn_reset = QPushButton("Reset to Defaults")
        self.btn_reset.setObjectName("btn_reset")
        self.btn_reset.setMinimumWidth(160)
        self.btn_reset.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.btn_reset.clicked.connect(self.on_reset_clicked)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.setObjectName("btn_close")
        self.btn_close.setDefault(True)
        self.btn_close.clicked.connect(self.accept)
        self.btn_close.setMinimumWidth(100)
        
        bottom_layout.addWidget(self.btn_reset)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_close)

        container_layout.addWidget(content_row, 1)
        container_layout.addWidget(bottom_bar)

        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.addWidget(container)
        
        self.sidebar.setCurrentRow(0)
        
        # Signals for dynamic UI updates
        self.config.themeChanged.connect(self.apply_theme)
        self.config.uiFontSizeChanged.connect(lambda s: self.apply_theme())
        self.config.uiFontFamilyChanged.connect(lambda f: self.apply_theme())
        
        self.apply_theme()

    def add_sidebar_item(self, text, icon_name):
        from PySide6.QtWidgets import QListWidgetItem
        item = QListWidgetItem(self.sidebar)
        item.setText(text)
        item.setData(Qt.UserRole, icon_name)
        item.setSizeHint(QSize(180, 40))

    def create_setting_row(self, title, description, widget):
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 10, 0, 10)
        
        text_container = QWidget()
        text_layout = QVBoxLayout(text_container)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)
        
        title_label = QLabel(title)
        title_label.setObjectName("setting_title")
        
        desc_label = QLabel(description)
        desc_label.setObjectName("setting_desc")
        desc_label.setWordWrap(True)
        
        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)
        
        layout.addWidget(text_container, 1)
        layout.addWidget(widget)
        layout.setAlignment(widget, Qt.AlignVCenter)
        
        # Add separator line below
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setObjectName("separator")
        
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(row)
        container_layout.addWidget(line)
        
        return container

    def change_page(self, index):
        if 0 <= index < self.pages.count():
            self.pages.setCurrentIndex(index)

    def create_section_header(self, text):
        label = QLabel(text)
        label.setObjectName("section_header")
        return label

    def apply_theme(self, theme_name=None):
        super().apply_theme()
        
        if not hasattr(self, 'sidebar'): return

        current_theme = theme_name if theme_name else self.config.theme
        is_dark = (current_theme == "Dark")
        ui_font_size = self.config.ui_font_size
        ui_font_family = self.config.ui_font_family

        if is_dark:
            sidebar_bg = "#252526"
            sidebar_fg = "#cccccc"
            sidebar_border = "#3e3e42"
            sidebar_sel_bg = "#37373d"
            sidebar_sel_fg = "#ffffff"
            sidebar_hover = "#2a2d2e"
            content_bg = "#1e1e1e"
            content_fg = "#d4d4d4"
            header_fg = "#ffffff"
            bottom_border = "#333333"
            sep_color = "#333333"
        else:
            sidebar_bg = "#f3f3f3"
            sidebar_fg = "#333333"
            sidebar_border = "#e5e5e5"
            sidebar_sel_bg = "#e1e1e1"
            sidebar_sel_fg = "#000000"
            sidebar_hover = "#e8e8e8"
            content_bg = "#ffffff"
            content_fg = "#333333"
            header_fg = "#000000"
            bottom_border = "#eeeeee"
            sep_color = "#eeeeee"

        self.sidebar.setStyleSheet(f"""
            QListWidget {{
                background-color: {sidebar_bg};
                color: {sidebar_fg};
                outline: none;
                border-right: 1px solid {sidebar_border};
                padding-top: 10px;
                font-family: \"{ui_font_family}\";
                font-size: {ui_font_size}px;
            }}
            QListWidget::item {{
                height: 40px;
                padding-left: 15px;
                border-radius: 5px;
                margin: 2px 8px;
                border: none;
            }}
            QListWidget::item:selected {{
                background-color: {sidebar_sel_bg};
                color: {sidebar_sel_fg};
                font-weight: bold;
            }}
            QListWidget::item:hover {{
                background-color: {sidebar_hover};
            }}
        """)
        
        # Update sidebar icons
        for i in range(self.sidebar.count()):
            item = self.sidebar.item(i)
            icon_name = item.data(Qt.UserRole)
            if icon_name:
                color = sidebar_sel_fg if item.isSelected() else sidebar_fg
                item.setIcon(get_svg_icon(icon_name, color))
        
        self.pages.setStyleSheet(f"""
            QStackedWidget {{
                background-color: {content_bg}; 
                color: {content_fg}; 
                font-family: \"{ui_font_family}\";
            }}
            QComboBox, QSpinBox, QPushButton {{
                font-family: \"{ui_font_family}\";
                font-size: {ui_font_size}px;
            }}
            QLabel {{ color: {content_fg}; font-family: \"{ui_font_family}\"; }}
            QLabel#section_header {{
                font-size: {ui_font_size + 6}px; 
                font-weight: bold; 
                color: {header_fg};
                margin-bottom: 20px;
                padding-bottom: 5px;
            }}
            QLabel#setting_title {{
                font-size: {ui_font_size}px; 
                font-weight: bold; 
            }}
            QLabel#setting_desc {{
                font-size: {max(9, ui_font_size - 2)}px; 
                color: #888888; 
            }}
            QFrame#separator {{
                background-color: {sep_color};
                max-height: 1px;
                border: none;
            }}
        """)

        # Style Bottom Bar
        self.findChild(QFrame, "bottom_bar").setStyleSheet(f"""
            #bottom_bar {{
                background-color: {sidebar_bg};
                border-top: 1px solid {bottom_border};
                font-family: \"{ui_font_family}\";
            }}
            QPushButton {{ font-family: \"{ui_font_family}\"; font-size: {ui_font_size}px; }}
            QPushButton#btn_reset {{
                background-color: transparent;
                border: 1px solid {sidebar_border};
                color: {sidebar_fg};
            }}
            QPushButton#btn_reset:hover {{
                background-color: {sidebar_hover};
            }}
        """)

        # Ensure font preview combos are updated with current UI size
        if hasattr(self, 'font_combo'):
            self.update_combo_font(self.config.editor_font_family)
        if hasattr(self, 'ui_font_combo'):
            self.ui_font_combo.setStyleSheet(f"font-family: \"{self.config.ui_font_family}\"; font-size: {ui_font_size}px;")

    def on_reset_clicked(self):
        from log_analyzer.modern_messagebox import ModernMessageBox
        from PySide6.QtWidgets import QMessageBox
        
        res = ModernMessageBox.question(self, "Reset Settings", 
                                        "Are you sure you want to reset all settings to default values?",
                                        QMessageBox.Yes | QMessageBox.No)
        
        if res == QMessageBox.Yes:
            self.config.reset_to_defaults()
            # Refresh all UI components in the dialog to reflect new config
            self.refresh_ui_from_config()
            self.apply_theme()

    def refresh_ui_from_config(self):
        # 1. General
        self.encoding_combo.setCurrentText(self.config.default_encoding)
        
        # 2. Log View
        self.font_combo.setCurrentText(self.config.editor_font_family)
        self.update_combo_font(self.config.editor_font_family)
        self.font_size_spin.setValue(self.config.editor_font_size)
        self.line_spacing_spin.setValue(self.config.editor_line_spacing)
        self.line_numbers_cb.setChecked(self.config.show_line_numbers)
        
        # 3. Appearance
        self.theme_combo.setCurrentText(self.config.theme)
        self.ui_font_spin.setValue(self.config.ui_font_size)
        self.ui_font_combo.setCurrentText(self.config.ui_font_family)
        self.ui_font_combo.setStyleSheet(f"font-family: \"{self.config.ui_font_family}\"; font-size: {self.config.ui_font_size}px;")

    def create_general_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignTop)

        layout.addWidget(self.create_section_header("General Settings"))

        # -- Default Encoding --
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["UTF-8", "ASCII", "ISO-8859-1", "GBK", "Shift_JIS"])
        self.encoding_combo.setFixedWidth(150)
        self.encoding_combo.setCurrentText(self.config.default_encoding)
        self.encoding_combo.currentTextChanged.connect(lambda t: self.config.set("general/default_encoding", t))
        
        layout.addWidget(self.create_setting_row(
            "Default Encoding", 
            "The character encoding used when opening log files. UTF-8 is recommended for most cases.",
            self.encoding_combo
        ))

        return page

    def create_log_view_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignTop)

        layout.addWidget(self.create_section_header("Log View Settings"))

        # 1. Font Family
        self.font_combo = QComboBox()
        self.font_combo.setFixedWidth(200)
        all_families = QFontDatabase.families()
        blacklist = {"fixedsys", "terminal", "system", "modern", "roman", "script", 
                     "ms serif", "ms sans serif", "small fonts", "courier"}
        safe_fonts = sorted([f for f in all_families if f.lower() not in blacklist and not f.startswith("@") and QFontDatabase.isFixedPitch(f)])
        
        for f in safe_fonts:
            self.font_combo.addItem(f)
            self.font_combo.setItemData(self.font_combo.count() - 1, QFont(f, 11), Qt.FontRole)
        
        current_font = self.config.editor_font_family
        self.font_combo.setCurrentText(current_font)
        self.update_combo_font(current_font)
        self.font_combo.currentTextChanged.connect(self.on_font_combo_changed)
        
        layout.addWidget(self.create_setting_row(
            "Font Family",
            "Choose the typeface for the log content. Monospaced fonts are recommended.",
            self.font_combo
        ))

        # 2. Font Size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 72)
        self.font_size_spin.setFixedWidth(100)
        self.font_size_spin.setValue(self.config.editor_font_size)
        self.font_size_spin.valueChanged.connect(self.update_editor_font)
        
        layout.addWidget(self.create_setting_row(
            "Font Size",
            "Adjust the text size of the log entries.",
            self.font_size_spin
        ))

        # 3. Line Spacing
        self.line_spacing_spin = QSpinBox()
        self.line_spacing_spin.setRange(0, 50)
        self.line_spacing_spin.setFixedWidth(100)
        self.line_spacing_spin.setValue(self.config.editor_line_spacing)
        self.line_spacing_spin.valueChanged.connect(lambda v: setattr(self.config, 'editor_line_spacing', v))
        
        layout.addWidget(self.create_setting_row(
            "Line Spacing",
            "Additional vertical space between lines in pixels.",
            self.line_spacing_spin
        ))

        # 4. Show Line Numbers
        self.line_numbers_cb = QCheckBox()
        self.line_numbers_cb.setChecked(self.config.show_line_numbers)
        self.line_numbers_cb.toggled.connect(lambda c: setattr(self.config, 'show_line_numbers', c))
        
        layout.addWidget(self.create_setting_row(
            "Show Line Numbers",
            "Display line counts on the left side of the log view.",
            self.line_numbers_cb
        ))

        return page

    def create_appearance_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignTop)

        layout.addWidget(self.create_section_header("Appearance Settings"))

        # 1. Theme
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setFixedWidth(150)
        self.theme_combo.setCurrentText(self.config.theme)
        self.theme_combo.currentTextChanged.connect(lambda t: setattr(self.config, 'theme', t))
        
        layout.addWidget(self.create_setting_row(
            "Color Theme",
            "Switch between dark and light interface modes.",
            self.theme_combo
        ))

        # 2. UI Font Family
        self.ui_font_combo = QComboBox()
        self.ui_font_combo.setFixedWidth(200)
        all_families = QFontDatabase.families()
        blacklist = {"fixedsys", "terminal", "system", "modern", "roman", "script", 
                     "ms serif", "ms sans serif", "small fonts", "courier"}
        safe_fonts = sorted([f for f in all_families if f.lower() not in blacklist and not f.startswith("@")])
        
        for f in safe_fonts:
            self.ui_font_combo.addItem(f)
            self.ui_font_combo.setItemData(self.ui_font_combo.count() - 1, QFont(f, 11), Qt.FontRole)
        
        current_ui_font = self.config.ui_font_family
        self.ui_font_combo.setCurrentText(current_ui_font)
        self.ui_font_combo.setStyleSheet(f"font-family: \"{current_ui_font}\"; font-size: {self.config.ui_font_size}px;")
            
        def _on_ui_font_changed(text):
            self.config.ui_font_family = text
            self.ui_font_combo.setStyleSheet(f"font-family: \"{text}\"; font-size: {self.config.ui_font_size}px;")

        self.ui_font_combo.currentTextChanged.connect(_on_ui_font_changed)
        
        layout.addWidget(self.create_setting_row(
            "Interface Font",
            "The typeface used for menus, buttons, and sidebars.",
            self.ui_font_combo
        ))

        # 3. UI Font Size
        self.ui_font_spin = QSpinBox()
        self.ui_font_spin.setRange(8, 24)
        self.ui_font_spin.setFixedWidth(100)
        self.ui_font_spin.setValue(self.config.ui_font_size)
        self.ui_font_spin.valueChanged.connect(lambda v: setattr(self.config, 'ui_font_size', v))
        
        layout.addWidget(self.create_setting_row(
            "Interface Font Size",
            "Scale the overall size of the user interface text.",
            self.ui_font_spin
        ))

        return page

    def on_font_combo_changed(self, text):
        self.update_combo_font(text)
        self.update_editor_font()

    def update_combo_font(self, family):
        size = self.config.ui_font_size
        self.font_combo.setStyleSheet(f"font-family: \"{family}\"; font-size: {size}px;")

    def update_editor_font(self):
        family = self.font_combo.currentText()
        size = self.font_size_spin.value()
        self.config.set_editor_font(family, size)
