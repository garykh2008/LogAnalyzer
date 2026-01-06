import xml.etree.ElementTree as ET
import os
import sys
import ctypes

def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    if not hex_str: return (0, 0, 0)
    if len(hex_str) == 3: hex_str = "".join(c*2 for c in hex_str)
    try:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    except: return (0, 0, 0)

def fix_color(hex_str, default):
    if not hex_str:
        return default
    hex_str = hex_str.strip()
    if not hex_str.startswith('#'):
        return '#' + hex_str
    return hex_str

def adjust_color_for_theme(hex_color, is_background, is_dark_mode):
    """
    Dynamically adjusts filter colors for Dark Mode to prevent jarring contrast.
    Ported from loganalyzer.py
    """
    if not hex_color: return hex_color
    hex_color = hex_color.strip().lower()
    if not hex_color.startswith("#"): hex_color = "#" + hex_color

    if not is_dark_mode:
        return hex_color

    # 1. Handle Defaults
    if is_background and (hex_color == "#ffffff" or hex_color == "#fff"):
        return "#1e1e1e" # Match dark theme bg
    if not is_background and (hex_color == "#000000" or hex_color == "#000"):
        return "#d4d4d4" # Match dark theme text

    # 2. Smart Adjustment based on Luminance
    rgb = hex_to_rgb(hex_color)
    lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255.0

    if is_background and lum > 0.4: # Too bright for dark mode bg
        # Dim it
        return '#{:02x}{:02x}{:02x}'.format(*tuple(int(c * 0.25) for c in rgb))
    if not is_background and lum < 0.5: # Too dark for dark mode text
        # Lighten it
        return '#{:02x}{:02x}{:02x}'.format(*tuple(int(c + (255 - c) * 0.6) for c in rgb))

    return hex_color

def set_windows_title_bar_color(win_id, is_dark):
    """
    Sets the Windows title bar color to match the theme (Dark/Light).
    """
    if sys.platform != "win32": return
    try:
        hwnd = int(win_id)
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        value = ctypes.c_int(1 if is_dark else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
    except Exception: pass

def bool_to_tat(value):
    return 'y' if value else 'n'

def is_true(value):
    if value is None: return False
    return str(value).lower() in ('1', 'y', 'yes', 'true')

def color_to_tat(hex_color):
    if not hex_color: return ""
    return hex_color.replace("#", "")

def load_tat_filters(filepath):
    filters = []
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        for f in root.findall('.//filter'):
            text = f.get('text')
            if text:
                flt = {
                    "text": text,
                    "enabled": is_true(f.get('enabled')),
                    "is_exclude": is_true(f.get('excluding')),
                    "is_regex": is_true(f.get('regex')),
                    "fg_color": fix_color(f.get('foreColor'), "#000000"),
                    "bg_color": fix_color(f.get('backColor'), "#FFFFFF"),
                    "hits": 0
                }
                filters.append(flt)
    except Exception as e:
        print(f"Error loading TAT file: {e}")
        return None
    return filters

def save_tat_filters(filepath, filters):
    try:
        root = ET.Element("TextAnalysisTool.NET")
        root.set("version", "2017-01-24")
        root.set("showOnlyFilteredLines", "False")
        filters_node = ET.SubElement(root, "filters")

        for flt in filters:
            f_node = ET.SubElement(filters_node, "filter")
            f_node.set("enabled", bool_to_tat(flt["enabled"]))
            f_node.set("excluding", bool_to_tat(flt["is_exclude"]))
            f_node.set("text", flt["text"])
            f_node.set("type", "matches_text") # Defaulting type
            f_node.set("regex", bool_to_tat(flt["is_regex"]))
            f_node.set("case_sensitive", "n")

            fg = flt.get("fg_color", "#000000")
            bg = flt.get("bg_color", "#FFFFFF")

            if fg != "#000000": f_node.set("foreColor", color_to_tat(fg))
            if bg != "#FFFFFF": f_node.set("backColor", color_to_tat(bg))

        tree = ET.ElementTree(root)
        tree.write(filepath, encoding="utf-8", xml_declaration=True)
        return True
    except Exception as e:
        print(f"Error saving TAT file: {e}")
        return False
