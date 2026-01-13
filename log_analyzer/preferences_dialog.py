from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QListWidget, QStackedWidget,
    QComboBox, QCheckBox, QSpinBox, QGroupBox, QFrame, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QFontDatabase
from log_analyzer.modern_dialog import ModernDialog
from log_analyzer.config import get_config
from log_analyzer.resources import get_svg_icon

class PreferencesDialog(ModernDialog):
    def __init__(self, parent=None):
        super().__init__(parent, title="Preferences", fixed_size=(700, 550))
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
        self.sidebar.setFixedWidth(180)
        self.sidebar.setFrameShape(QFrame.NoFrame)
        
        # Add categories
        self.sidebar.addItem("General")
        self.sidebar.addItem("Log View")
        self.sidebar.addItem("Appearance")
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
        bottom_bar.setFixedHeight(60)
        bottom_layout = QHBoxLayout(bottom_bar)
        bottom_layout.setContentsMargins(20, 0, 20, 0)
        
        self.btn_reset = QPushButton("Reset to Defaults")
        self.btn_reset.setIcon(get_svg_icon("rotate-ccw", "#888888"))
        self.btn_reset.clicked.connect(self.on_reset_clicked)
        
        self.btn_close = QPushButton("Close")
        self.btn_close.setDefault(True)
        self.btn_close.clicked.connect(self.accept)
        self.btn_close.setFixedWidth(100)
        
        bottom_layout.addWidget(self.btn_reset)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.btn_close)

        container_layout.addWidget(content_row, 1)
        container_layout.addWidget(bottom_bar)

        # Set the content of ModernDialog
        # Reset default padding of ModernDialog for this specific layout
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.addWidget(container)
        
        # Select first item
        self.sidebar.setCurrentRow(0)
        
        self.config.themeChanged.connect(self.apply_theme)
        self.apply_theme()

    def change_page(self, index):
        self.pages.setCurrentIndex(index)

    def create_section_header(self, text):
        label = QLabel(text)
        label.setObjectName("section_header")
        return label

    def apply_theme(self, theme_name=None):
        super().apply_theme()
        
        if not hasattr(self, 'sidebar'): return

        # Determine mode from config directly (or signal arg)
        current_theme = theme_name if theme_name else self.config.theme
        is_dark = (current_theme == "Dark")
        ui_font_size = self.config.ui_font_size

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

        self.sidebar.setStyleSheet(f"""
            QListWidget {{
                background-color: {sidebar_bg};
                color: {sidebar_fg};
                outline: none;
                border-right: 1px solid {sidebar_border};
                padding-top: 10px;
                font-size: {ui_font_size}px;
            }}
            QListWidget::item {{
                height: 36px;
                padding-left: 10px;
                border-left: 3px solid transparent;
            }}
            QListWidget::item:selected {{
                background-color: {sidebar_sel_bg};
                color: {sidebar_sel_fg};
                border-left: 3px solid #007acc;
            }}
            QListWidget::item:hover {{
                background-color: {sidebar_hover};
            }}
        """)
        
        self.pages.setStyleSheet(f"""
            QStackedWidget {{ background-color: {content_bg}; color: {content_fg}; }}
            QLabel#section_header {{ font-size: {ui_font_size + 4}px; font-weight: bold; color: {header_fg}; margin-bottom: 10px; }}
        """)

        # Style Bottom Bar
        self.findChild(QFrame, "bottom_bar").setStyleSheet(f"""
            #bottom_bar {{
                background-color: {sidebar_bg};
                border-top: 1px solid {bottom_border};
            }}
        """)

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

    def refresh_ui_from_config(self):
        # 1. General
        self.encoding_combo.setCurrentText(self.config.default_encoding)
        
        # 2. Log View
        self.font_combo.setCurrentText(self.config.editor_font_family)
        self.font_size_spin.setValue(self.config.editor_font_size)
        self.line_spacing_spin.setValue(self.config.editor_line_spacing)
        self.line_numbers_cb.setChecked(self.config.show_line_numbers)
        
        # 3. Appearance
        self.theme_combo.setCurrentText(self.config.theme)
        self.ui_font_spin.setValue(self.config.ui_font_size)
        self.ui_font_combo.setCurrentText(self.config.ui_font_family)

    def create_general_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignTop)

        layout.addWidget(self.create_section_header("General Settings"))

        # -- Default Encoding --
        encoding_group = QGroupBox("Default Encoding")
        encoding_layout = QVBoxLayout(encoding_group)
        
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(["UTF-8", "ASCII", "ISO-8859-1", "GBK", "Shift_JIS"])
        self.encoding_combo.setCurrentText(self.config.default_encoding)
        self.encoding_combo.currentTextChanged.connect(lambda t: self.config.set("general/default_encoding", t))
        
        encoding_layout.addWidget(QLabel("Encoding to use when opening new files:"))
        encoding_layout.addWidget(self.encoding_combo)
        layout.addWidget(encoding_group)

        return page

    def create_log_view_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignTop)

        layout.addWidget(self.create_section_header("Log View Settings"))

        # -- Font Settings --
        font_group = QGroupBox("Font")
        font_layout = QVBoxLayout(font_group)
        
        # Font Family
        font_layout.addWidget(QLabel("Font Family:"))
        self.font_combo = QComboBox()
        
        # Manually populate monospaced fonts to filter out problematic legacy raster fonts
        # that cause DirectWrite warnings (Fixedsys, Terminal, etc.)
        all_families = QFontDatabase.families()
        blacklist = {"fixedsys", "terminal", "system", "modern", "roman", "script", 
                     "ms serif", "ms sans serif", "small fonts", "courier"}
        
        safe_fonts = []
        for f in all_families:
            if f.lower() in blacklist or f.startswith("@"): continue
            if QFontDatabase.isFixedPitch(f):
                safe_fonts.append(f)
        
        safe_fonts.sort()
        
        for f in safe_fonts:
            self.font_combo.addItem(f)
            # Set the item's font to the font itself for preview
            self.font_combo.setItemData(self.font_combo.count() - 1, QFont(f, 11), Qt.FontRole)
        
        current_font = self.config.editor_font_family
        if current_font in safe_fonts:
            self.font_combo.setCurrentText(current_font)
        else:
            # Fallback if config has a font not in our safe list
            self.font_combo.addItem(current_font)
            self.font_combo.setCurrentText(current_font)

        # Initialize combo box font preview
        self.update_combo_font(current_font)

        self.font_combo.currentTextChanged.connect(self.on_font_combo_changed)
        font_layout.addWidget(self.font_combo)

        # Font Size
        font_layout.addWidget(QLabel("Font Size:"))
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 72)
        self.font_size_spin.setValue(self.config.editor_font_size)
        self.font_size_spin.valueChanged.connect(self.update_editor_font)
        font_layout.addWidget(self.font_size_spin)

        # Line Spacing
        font_layout.addWidget(QLabel("Line Spacing (px):"))
        self.line_spacing_spin = QSpinBox()
        self.line_spacing_spin.setRange(0, 50)
        self.line_spacing_spin.setValue(self.config.editor_line_spacing)
        self.line_spacing_spin.valueChanged.connect(lambda v: setattr(self.config, 'editor_line_spacing', v))
        font_layout.addWidget(self.line_spacing_spin)

        layout.addWidget(font_group)

        # -- Display Settings --
        display_group = QGroupBox("Display")
        display_layout = QVBoxLayout(display_group)

        self.line_numbers_cb = QCheckBox("Show Line Numbers")
        self.line_numbers_cb.setChecked(self.config.show_line_numbers)
        self.line_numbers_cb.toggled.connect(lambda c: setattr(self.config, 'show_line_numbers', c))
        display_layout.addWidget(self.line_numbers_cb)

        layout.addWidget(display_group)

        return page

    def create_appearance_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setAlignment(Qt.AlignTop)

        layout.addWidget(self.create_section_header("Appearance Settings"))

        # -- Theme Settings --
        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout(theme_group)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        
        # Set current selection based on config
        current_theme = self.config.theme
        self.theme_combo.setCurrentText(current_theme)
        
        self.theme_combo.currentTextChanged.connect(lambda t: setattr(self.config, 'theme', t))
        
        theme_layout.addWidget(QLabel("Application Theme:"))
        theme_layout.addWidget(self.theme_combo)

        # UI Font Family
        theme_layout.addWidget(QLabel("UI Font Family:"))
        self.ui_font_combo = QComboBox()
        
        # Populate with safe system fonts (case-insensitive blacklist check)
        all_families = QFontDatabase.families()
        blacklist = {"fixedsys", "terminal", "system", "modern", "roman", "script", 
                     "ms serif", "ms sans serif", "small fonts", "courier"}
        safe_fonts = sorted([f for f in all_families if f.lower() not in blacklist and not f.startswith("@")])
        
        for f in safe_fonts:
            self.ui_font_combo.addItem(f)
            # Preview font in the dropdown
            self.ui_font_combo.setItemData(self.ui_font_combo.count() - 1, QFont(f, 11), Qt.FontRole)
        
        current_ui_font = self.config.ui_font_family
        if current_ui_font in safe_fonts:
            self.ui_font_combo.setCurrentText(current_ui_font)
        else:
            self.ui_font_combo.addItem(current_ui_font)
            self.ui_font_combo.setItemData(self.ui_font_combo.count() - 1, QFont(current_ui_font, 11), Qt.FontRole)
            self.ui_font_combo.setCurrentText(current_ui_font)
            
        # Initial stylesheet update for combo box font
        self.ui_font_combo.setStyleSheet(f"font-family: \"{current_ui_font}\"; font-size: 14px;")
            
        def on_ui_font_changed(text):
            self.config.ui_font_family = text
            self.ui_font_combo.setStyleSheet(f"font-family: \"{text}\"; font-size: 14px;")

        self.ui_font_combo.currentTextChanged.connect(on_ui_font_changed)
        theme_layout.addWidget(self.ui_font_combo)

        # UI Font Size
        theme_layout.addWidget(QLabel("UI Font Size:"))
        self.ui_font_spin = QSpinBox()
        self.ui_font_spin.setRange(8, 24)
        self.ui_font_size = self.config.ui_font_size # Store reference for internal access if needed
        self.ui_font_spin.setValue(self.config.ui_font_size)
        self.ui_font_spin.valueChanged.connect(lambda v: setattr(self.config, 'ui_font_size', v))
        theme_layout.addWidget(self.ui_font_spin)
        
        layout.addWidget(theme_group)

        return page

    def on_font_combo_changed(self, text):
        self.update_combo_font(text)
        self.update_editor_font()

    def update_combo_font(self, family):
        # Use stylesheet to override the global application font-family setting
        # We apply it to the QComboBox and its internal QAbstractItemView to ensure consistency,
        # although item fonts are handled by setItemData.
        self.font_combo.setStyleSheet(f"font-family: \"{family}\"; font-size: 14px;")

    def update_editor_font(self):
        family = self.font_combo.currentText()
        size = self.font_size_spin.value()
        self.config.set_editor_font(family, size)


    def on_font_combo_changed(self, text):
        self.update_combo_font(text)
        self.update_editor_font()

    def update_combo_font(self, family):
        # Use stylesheet to override the global application font-family setting
        # We apply it to the QComboBox and its internal QAbstractItemView to ensure consistency,
        # although item fonts are handled by setItemData.
        self.font_combo.setStyleSheet(f"font-family: \"{family}\"; font-size: 14px;")

    def update_editor_font(self):
        family = self.font_combo.currentText()
        size = self.font_size_spin.value()
        self.config.set_editor_font(family, size)
