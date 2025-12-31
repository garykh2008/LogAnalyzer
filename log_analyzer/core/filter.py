class Filter:
    def __init__(self, text, fore_color="#000000", back_color="#FFFFFF", enabled=True, is_regex=False, is_exclude=False, is_event=False):
        self.text = text
        self.fore_color = fore_color
        self.back_color = back_color
        self.enabled = enabled
        self.is_regex = is_regex
        self.is_exclude = is_exclude
        self.is_event = is_event
        self.hit_count = 0

    def to_tat_xml(self):
        """Converts filter to TextAnalysisTool XML format."""
        en = 'y' if self.enabled else 'n'
        reg = 'y' if self.is_regex else 'n'
        exc = 'y' if self.is_exclude else 'n' # Use 'y'/'n' for consistency
        # Remove '#' for TAT color format
        fg = self.fore_color.lstrip('#')
        bg = self.back_color.lstrip('#')

        # Match btm.tat format for compatibility
        return f'<filter enabled="{en}" excluding="{exc}" description="" foreColor="{fg}" backColor="{bg}" type="matches_text" case_sensitive="{reg}" regex="{reg}" text="{self.text}"></filter>'
