from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import QByteArray, QSize, Qt

# Minimal Lucide-inspired SVG path data
SVG_ICONS = {
    "chevron-up": """
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" 
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m18 15-6-6-6 6"/>
        </svg>
    """,
    "chevron-down": """
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" 
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m6 9 6 6 6-6"/>
        </svg>
    """,
    "case-sensitive": """
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" 
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m3 15 4-8 4 8"/><path d="M4 13h6"/>
            <circle cx="18" cy="12" r="3"/><path d="M21 9v6"/>
        </svg>
    """,
    "wrap": """
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" 
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="3 6 19 6 19 12"/><polyline points="3 18 19 18 19 12"/><polyline points="7 10 3 6 7 2"/><polyline points="7 22 3 18 7 14"/>
        </svg>
    """,
    "x-close": """
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" 
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
        </svg>
    """
}

def get_svg_icon(name, color_str="#d4d4d4", size=24):
    """Generates a QIcon from an internal SVG string with dynamic color."""
    svg_str = SVG_ICONS.get(name)
    if not svg_str:
        return QIcon()
    
    # Replace 'currentColor' with the actual theme color
    colored_svg = svg_str.replace('currentColor', color_str)
    
    byte_array = QByteArray(colored_svg.encode('utf-8'))
    renderer = QSvgRenderer(byte_array)
    
    pixmap = QPixmap(QSize(size, size))
    pixmap.fill(Qt.transparent)
    
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    
    return QIcon(pixmap)
