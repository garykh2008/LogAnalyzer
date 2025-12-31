import os

class MockLogEngine:
    """Fallback engine when Rust extension is missing."""
    def __init__(self, path):
        self.path = path
        # 模擬讀取
        self._lines = 1000 # 假裝有 1000 行

    def line_count(self):
        return self._lines

    def get_line(self, idx):
        return f"Mock Line #{idx} from {os.path.basename(self.path)}"

    def filter(self, filters):
        # filters: List of (text, is_regex, is_exclude, is_event, original_index)

        # 簡單模擬：如果 filter text 是 "error"，就只回傳偶數行
        # 回傳格式: (line_tags_codes, filtered_indices, hit_counts, timeline_events)

        filtered_indices = []
        line_tags = [0] * self._lines
        hit_counts = [0] * len(filters)

        # 模擬一個簡單的過濾邏輯
        has_active_filters = len(filters) > 0

        for i in range(self._lines):
            # 這裡簡單全通過，除非有 filter 且內容包含 "error" (模擬)
            # 為了方便測試，我們假設如果沒有 filter 就全顯示
            # 如果有 filter，我們隨機過濾一些
            if not has_active_filters:
                filtered_indices.append(i)
            else:
                # 模擬：只要有 filter，就只顯示 1/3 的行數
                if i % 3 == 0:
                    filtered_indices.append(i)
                    line_tags[i] = 2 # 模擬匹配第一個 filter
                    hit_counts[0] += 1

        return (line_tags, filtered_indices, hit_counts, [])

try:
    import log_engine_rs
    # Assign the imported class to a new variable for consistent access
    LogEngine = log_engine_rs.LogEngine
    HAS_RUST = True
    print("Rust Extension Loaded Successfully.")
except ImportError as e:
    LogEngine = MockLogEngine # Fallback
    HAS_RUST = False
    print(f"Failed to load Rust Extension: {e}. Using Mock Engine.")
