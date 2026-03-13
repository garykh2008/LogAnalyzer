import os
import sys
import tempfile
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, QObject

class IconManager(QObject):
    """A 100% portable icon manager with caching and dynamic recoloring."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(IconManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, assets_dir=None):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        
        # Handle PyInstaller _MEIPASS for resource paths
        if hasattr(sys, '_MEIPASS'):
            # Running in PyInstaller bundle
            base_dir = os.path.join(sys._MEIPASS, "log_analyzer")
        else:
            # Running in normal Python environment
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.assets_dir = assets_dir or os.path.join(base_dir, "assets")
        self._cache = {}
        self._path_cache = {}

    def get_icon_css_url(self, name, color="#FFFFFF", size=16):
        """
        Generates a temporary SVG file and returns a CSS url(...) string.
        Robust solution for QSS image loading.
        """
        cache_key = (name, color)
        if cache_key in self._path_cache:
            if os.path.exists(self._path_cache[cache_key]):
                # Return cached path format
                path = self._path_cache[cache_key].replace("\\", "/")
                return f"url({path})"

        svg_path = os.path.join(self.assets_dir, f"{name}.svg")
        if not os.path.exists(svg_path):
            return ""

        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Dynamic recoloring
            for target in ["#000000", "#FFFFFF", "white", "black", "currentColor"]:
                content = content.replace(f'"{target}"', f'"{color}"').replace(f'={target}', f'={color}')
            
            # Create temp file
            temp_dir = os.path.join(tempfile.gettempdir(), "LogAnalyzer_Icons")
            os.makedirs(temp_dir, exist_ok=True)
            
            safe_color = color.replace("#", "")
            temp_filename = f"{name}_{safe_color}.svg"
            temp_path = os.path.join(temp_dir, temp_filename)
            
            with open(temp_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self._path_cache[cache_key] = temp_path
            final_path = temp_path.replace("\\", "/")
            return f"url({final_path})"
            
        except Exception as e:
            print(f"[IconManager] Error creating icon path {name}: {e}")
            return ""

    def load_icon(self, name, color="#FFFFFF", size=24):
        """Loads and recolors an SVG icon, returns QIcon."""
        pixmap = self.load_pixmap(name, color, size, size)
        return QIcon(pixmap)

    def load_pixmap(self, name, color="#FFFFFF", width=24, height=24):
        """Loads and recolors an SVG icon, returns QPixmap with caching."""
        cache_key = (name, color, width, height)
        if cache_key in self._cache:
            return self._cache[cache_key]

        svg_path = os.path.join(self.assets_dir, f"{name}.svg")
        
        # If file doesn't exist, return empty transparent pixmap to avoid Qt warnings
        if not os.path.exists(svg_path):
            pixmap = QPixmap(width, height)
            pixmap.fill(QColor("transparent"))
            return pixmap

        try:
            with open(svg_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if not content.strip():
                raise ValueError("Empty SVG file")

            # Dynamic recoloring
            for target in ["#000000", "#FFFFFF", "white", "black", "currentColor"]:
                content = content.replace(f'"{target}"', f'"{color}"').replace(f'={target}', f'={color}')
            
            renderer = QSvgRenderer(QByteArray(content.encode('utf-8')))
            pixmap = QPixmap(width, height)
            pixmap.fill(QColor("transparent"))
            
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            
            self._cache[cache_key] = pixmap
            return pixmap
        except Exception as e:
            print(f"[IconManager] Error loading {name}: {e}")
            pixmap = QPixmap(width, height)
            pixmap.fill(QColor("transparent"))
            return pixmap

# Export a lazy singleton to ensure QApplication is initialized first
class _LazyIconManager:
    def __getattr__(self, name):
        global icon_manager_instance
        if 'icon_manager_instance' not in globals():
            global icon_manager_instance
            icon_manager_instance = IconManager()
        return getattr(icon_manager_instance, name)

icon_manager = _LazyIconManager()
