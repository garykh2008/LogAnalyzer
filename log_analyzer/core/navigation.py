import asyncio
import math

class NavigationController:
    def __init__(self, app):
        self.app = app

    @property
    def total_items(self):
        if self.app.show_only_filtered and self.app.filtered_indices is not None:
            return len(self.app.filtered_indices)
        return self.app.log_engine.line_count() if self.app.log_engine else 0

    @property
    def max_scroll_index(self):
        return max(0, self.total_items - self.app.LINES_PER_PAGE)

    def scroll_to(self, index, immediate=True, center=False):
        """Scrolls to a specific line index. If center is True, tries to center the line."""
        if not self.app.log_engine:
            return

        target = int(index)

        if center:
            target -= self.app.LINES_PER_PAGE // 2

        max_idx = self.max_scroll_index
        target = max(0, min(target, max_idx))

        self.app.target_start_index = target

        if immediate:
            asyncio.create_task(self.app.immediate_render())

    def scroll_by(self, delta):
        """Scrolls by a relative amount of lines."""
        self.scroll_to(self.app.target_start_index + delta)

    def handle_mouse_wheel(self, delta_y):
        """Calculates scroll step based on wheel delta and scrolls."""
        if not self.app.log_engine:
            return

        base_step = 3
        abs_delta = abs(delta_y)

        if abs_delta >= 100:
             step = int(abs_delta / 10) # e.g. 100 -> 10 lines
        elif abs_delta > 20:
             step = 5
        else:
             step = base_step

        step = max(1, step) # Minimum 1 line

        if delta_y > 0:
            self.scroll_by(step)
        elif delta_y < 0:
            self.scroll_by(-step)

    def sync_scrollbar_position(self):
        """
        Syncs the scrollbar thumb position.

        NOTE: Custom scrollbar has been removed in favor of native ListView scrolling.
        This method is kept as a stub to prevent AttributeErrors from existing calls in app.py
        until full refactoring is complete.
        """
        pass
