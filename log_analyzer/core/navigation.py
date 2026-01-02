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

    @property
    def max_scrollbar_top(self):
        val = self.app.scrollbar_track_height - self.app.scrollbar_thumb_height
        return max(0, val)

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

    def handle_scrollbar_drag(self, delta_y):
        """Updates thumb position locally and scrolls content."""
        self.app.thumb_top += delta_y
        max_top = self.max_scrollbar_top

        self.app.thumb_top = max(0.0, min(self.app.thumb_top, max_top))
        self.app.scrollbar_thumb.top = self.app.thumb_top
        self.app.scrollbar_thumb.update() # Fast local update

        if max_top > 0:
            percentage = self.app.thumb_top / max_top
            new_idx = int(percentage * self.max_scroll_index)

            # Update target directly without calling scroll_to to avoid re-clamping logic interference
            # (though scroll_to does clamping too, which is fine)
            self.app.target_start_index = new_idx

            if not self.app.is_updating:
                asyncio.create_task(self.app.immediate_render())

    def handle_scrollbar_tap(self, local_y):
        """Jumps to position based on click on track."""
        click_y = local_y - (self.app.scrollbar_thumb_height / 2)
        max_top = self.max_scrollbar_top

        if max_top <= 0: return

        target_top = max(0.0, min(click_y, max_top))
        percentage = target_top / max_top
        new_idx = int(percentage * self.max_scroll_index)

        self.scroll_to(new_idx, immediate=True)

    def sync_scrollbar_position(self):
        """Syncs the scrollbar thumb position with current log view index."""
        if not self.app.log_engine: return

        max_idx = self.max_scroll_index
        if max_idx <= 0:
            self.app.thumb_top = 0
            self.app.scrollbar_thumb.top = 0
            return

        percentage = self.app.current_start_index / max_idx
        max_top = self.max_scrollbar_top
        if max_top < 0: max_top = 0

        self.app.thumb_top = percentage * max_top
        self.app.scrollbar_thumb.top = self.app.thumb_top
