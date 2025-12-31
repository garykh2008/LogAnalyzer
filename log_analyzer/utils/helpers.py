def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    if not hex_str: return (0, 0, 0)
    if len(hex_str) == 3: hex_str = "".join(c*2 for c in hex_str)
    try:
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
    except: return (0, 0, 0)

def get_luminance(hex_str):
    rgb = hex_to_rgb(hex_str)
    return (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255.0

def adjust_color_for_theme(hex_color, is_background, is_dark_mode):
    """
    Dynamically adjusts filter colors for Dark Mode to prevent jarring contrast.
    Ported from loganalyzer.py.
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
        return '#{:02x}{:02x}{:02x}'.format(*tuple(int(c * 0.25) for c in rgb))
    if not is_background and lum < 0.5: # Too dark for dark mode text
        return '#{:02x}{:02x}{:02x}'.format(*tuple(int(c + (255 - c) * 0.6) for c in rgb))

    return hex_color

def get_event_prop(event, prop_name, default=None):
    """
    Safely access event properties with fallback and debug info.
    Helps resolve API differences between Flet versions.
    """
    # 1. Direct access
    if hasattr(event, prop_name):
        return getattr(event, prop_name)

    # 2. Common Aliases / Fallbacks for 0.80.0+
    aliases = {
        'delta_y': ['delta', 'scroll_delta', 'local_delta'], # Added local_delta
        'local_y': ['local_position'],       # local_position is Offset
        'global_y': ['global_position']
    }

    if prop_name in aliases:
        for alias in aliases[prop_name]:
            if hasattr(event, alias):
                val = getattr(event, alias)
                # Handle Offset objects (local_position, etc.)
                if prop_name.endswith('_y') and hasattr(val, 'y'):
                    return val.y
                if prop_name.endswith('_x') and hasattr(val, 'x'):
                    return val.x
                # If expecting a scalar but got scalar (e.g. scroll_delta)
                return val

    # 3. Last Resort: Inspect and Debug

    return default
