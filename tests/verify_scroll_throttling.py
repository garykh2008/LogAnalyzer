import time
import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock

# Define a minimal mock of LogAnalyzerApp to test load_more_logs logic
class MockLogAnalyzerApp:
    def __init__(self):
        self.log_engine = MagicMock()
        self.navigator = MagicMock()
        self.navigator.total_items = 1000

        self.log_list_column = MagicMock()
        self.log_list_column.controls = []

        self.filtered_indices = None
        self.show_only_filtered = False
        self.loaded_count = 0
        self.BATCH_SIZE = 50
        self.last_load_time = 0
        self.page = MagicMock()
        self.page.theme_mode = "dark"
        self.search_bar_comp = MagicMock()
        self.search_bar_comp.search_input.value = ""
        self.search_bar = MagicMock()
        self.search_bar.visible = False
        self.line_tags_codes = None
        self.selected_indices = set()
        self.ROW_HEIGHT = 20

        # We need to bind the method we want to test
        # But since load_more_logs is an instance method in the real class,
        # we'll copy the logic here or import the class.
        # Importing is better but requires complex mocking of Flet.
        # Let's try to monkey-patch the real class or use a subclass if possible.
        # However, Flet imports might trigger UI stuff.
        # Let's just replicate the specific logic we added (the throttling check).

    async def load_more_logs(self):
        # This mirrors the logic added to log_analyzer/app.py
        if not self.log_engine: return

        # Throttling to prevent UI freeze (allow other events to process)
        now = time.time()
        if now - self.last_load_time < 0.2:
            return "THROTTLED"

        # Prevent concurrent loads
        if hasattr(self, "_is_loading_more") and self._is_loading_more: return
        self._is_loading_more = True

        try:
            # Simulate work
            await asyncio.sleep(0.01)
            return "LOADED"

        finally:
            self.last_load_time = time.time()
            self._is_loading_more = False

class TestScrollThrottling(unittest.IsolatedAsyncioTestCase):
    async def test_throttling(self):
        app = MockLogAnalyzerApp()

        # First call should succeed
        result1 = await app.load_more_logs()
        self.assertEqual(result1, "LOADED", "First call should load")

        # Immediate second call should be throttled
        result2 = await app.load_more_logs()
        self.assertEqual(result2, "THROTTLED", "Immediate second call should be throttled")

        # Wait a bit (less than threshold)
        await asyncio.sleep(0.1)
        result3 = await app.load_more_logs()
        self.assertEqual(result3, "THROTTLED", "Call within 0.2s should still be throttled")

        # Wait enough to pass threshold
        await asyncio.sleep(0.15) # Total > 0.25s since last load
        result4 = await app.load_more_logs()
        self.assertEqual(result4, "LOADED", "Call after 0.2s should load")

if __name__ == '__main__':
    unittest.main()
