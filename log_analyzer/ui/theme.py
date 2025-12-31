class ThemeColors:
    """Centralized color definitions for the application."""
    # Dark Mode - High Contrast Layering
    DARK = {
        "sidebar_bg": "#1E1E1E",
        "log_bg": "#000000",
        "top_bar_bg": "#333333",
        "text": "#E0E0E0",
        "scroll_track": "#000000",
        "scroll_thumb": "#444444",
        "divider": "#333333",
        "input_bg": "#333333",
        "selection_bg": "#264F78",
        "line_error": "#F44336",
        "line_warn": "#FFEB3B",
        "line_info": "#2196F3",
        "line_default": "#E0E0E0",
        "status_bg": "#005A9E",      # 專業深藍
        "status_text": "#FFFFFF",    # 白色文字
        "search_bg": "#2D2D2D",
    }

    # Light Mode - Paper & Ink Contrast
    LIGHT = {
        "sidebar_bg": "#F5F5F5",
        "log_bg": "#FFFFFF",
        "top_bar_bg": "#E0E0E0",
        "text": "#202124",
        "scroll_track": "#FFFFFF",
        "scroll_thumb": "#CCCCCC",
        "divider": "#D0D0D0",
        "input_bg": "#F1F3F4",
        "selection_bg": "#E8F0FE",
        "line_error": "#D93025",
        "line_warn": "#F9AB00",
        "line_info": "#1A73E8",
        "line_default": "#202124",
        "status_bg": "#E1F5FE",      # 極淺藍色
        "status_text": "#005A9E",    # 深藍色文字
        "search_bg": "#F1F3F4",
    }

    @staticmethod
    def get(mode):
        # Handle ThemeMode Enum or string
        m = str(mode).split(".")[-1].lower()
        return ThemeColors.DARK if m == "dark" else ThemeColors.LIGHT
