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
    editorFontChanged = Signal(str, int) # Emits font_family, font_size
    showLineNumbersChanged = Signal(bool)
    
    def __init__(self):
        super().__init__()
        # Organization and App names are set in main.py, so QSettings() works automatically
        self.settings = QSettings()
        
    def get(self, key, default=None):
        return self.settings.value(key, default)

    def set(self, key, value):
        self.settings.setValue(key, value)

    # --- Convenience Accessors with Signals ---

    # 1. Appearance
    @property
    def theme(self):
        return self.settings.value("appearance/theme", "Dark")

    @theme.setter
    def theme(self, value):
        if self.theme != value:
            self.settings.setValue("appearance/theme", value)
            self.themeChanged.emit(value)

    @property
    def ui_font_size(self):
        return int(self.settings.value("appearance/ui_font_size", 10))

    @ui_font_size.setter
    def ui_font_size(self, value):
        current = self.ui_font_size
        if current != value:
            self.settings.setValue("appearance/ui_font_size", value)
            # We might need to construct a QFont to emit, or just let main window handle it
            # For now, let's just emit the new size or a QFont object
            # Ideally, main.py sets the app font.
            pass 

    # 2. Log Editor / View
    @property
    def editor_font_family(self):
        return self.settings.value("editor/font_family", "Consolas")

    @property
    def editor_font_size(self):
        return int(self.settings.value("editor/font_size", 10))

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
