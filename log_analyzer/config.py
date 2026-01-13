from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtGui import QFont

class ConfigManager(QObject):
    """
    Manages application settings using QSettings.
    Singleton-like access is recommended by passing a shared instance.
    """
    
    # Signals to notify UI of changes
    fontChanged = Signal(object) # Emits QFont
    themeChanged = Signal(str)   # Emits "Dark", "Light", or "System"
    uiFontSizeChanged = Signal(int) # Emits size
    editorFontChanged = Signal(str, int) # Emits font_family, font_size
    editorLineSpacingChanged = Signal(int) # Emits spacing
    showLineNumbersChanged = Signal(bool)
    
    def __init__(self):
        super().__init__()
        # Explicitly set names to ensure consistency regardless of global app state
        self.settings = QSettings("LogAnalyzer", "Log Analyzer Qt")
        
    def get(self, key, default=None):
        return self.settings.value(key, default)

    def set(self, key, value):
        self.settings.setValue(key, value)

    # --- Convenience Accessors with Signals ---

    # 1. Appearance
    @property
    def theme(self):
        return self.settings.value("appearance/theme", "Light")

    @theme.setter
    def theme(self, value):
        if self.theme != value:
            self.settings.setValue("appearance/theme", value)
            self.themeChanged.emit(value)

    @property
    def ui_font_size(self):
        return int(self.settings.value("appearance/ui_font_size", 12))

    @ui_font_size.setter
    def ui_font_size(self, value):
        current = self.ui_font_size
        if current != value:
            self.settings.setValue("appearance/ui_font_size", value)
            self.uiFontSizeChanged.emit(value)

    # 2. Log Editor / View
    @property
    def editor_font_family(self):
        return self.settings.value("editor/font_family", "Consolas")

    @property
    def editor_font_size(self):
        return int(self.settings.value("editor/font_size", 12))

    def set_editor_font(self, family, size):
        changed = False
        if self.editor_font_family != family:
            self.settings.setValue("editor/font_family", family)
            changed = True
        if self.editor_font_size != size:
            self.settings.setValue("editor/font_size", size)
            changed = True
        
        if changed:
            self.editorFontChanged.emit(family, size)

    @property
    def editor_line_spacing(self):
        return int(self.settings.value("editor/line_spacing", 0))

    @editor_line_spacing.setter
    def editor_line_spacing(self, spacing):
        if self.editor_line_spacing != spacing:
            self.settings.setValue("editor/line_spacing", spacing)
            self.editorLineSpacingChanged.emit(spacing)

    @property
    def show_line_numbers(self):
        return str(self.settings.value("editor/show_line_numbers", "true")).lower() == "true"

    @show_line_numbers.setter
    def show_line_numbers(self, enabled):
        if self.show_line_numbers != enabled:
            self.settings.setValue("editor/show_line_numbers", enabled)
            self.showLineNumbersChanged.emit(enabled)

    # 3. General
    @property
    def default_encoding(self):
        return self.settings.value("general/default_encoding", "UTF-8")

    @default_encoding.setter
    def default_encoding(self, value):
        self.settings.setValue("general/default_encoding", value)

# Global instance
_config_instance = None

def get_config():
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance
