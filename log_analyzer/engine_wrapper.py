import os

try:
    import log_engine_rs
    HAS_RUST = True
except ImportError:
    HAS_RUST = False


def detect_encoding(filepath):
    """Simple BOM-based encoding detection."""
    try:
        with open(filepath, 'rb') as f:
            raw = f.read(4)
        if raw.startswith(b'\xff\xfe') or raw.startswith(b'\xfe\xff'):
            return 'utf-16'
        return 'utf-8'
    except Exception:
        return 'utf-8'


class MockLogEngine:
    """Fallback engine for UI development when Rust extension is missing."""
    def __init__(self, filepath=None):
        self.filepath = filepath
        self._lines = []
        if filepath:
            try:
                enc = detect_encoding(filepath)
                with open(filepath, 'r', encoding=enc, errors='replace') as f:
                    self._lines = f.readlines()
            except Exception:
                self._lines = [f"Error loading {filepath}"]
        else:
             # Generate dummy data for testing
            self._lines = [f"Mock Log Line {i+1}: This is a sample log entry. [TIMESTAMP]" for i in range(1000)]

    def line_count(self):
        return len(self._lines)

    def get_line(self, index):
        if 0 <= index < len(self._lines):
            return self._lines[index].rstrip('\n')
        return None

    def filter(self, filters):
        # Dummy implementation
        return [], [], [], []

    def search(self, query, is_regex, case_sensitive):
        # Simple Python search for Mock engine
        results = []
        import re
        try:
            for i, line in enumerate(self._lines):
                if is_regex:
                    flags = 0 if case_sensitive else re.IGNORECASE
                    if re.search(query, line, flags):
                        results.append(i)
                else:
                    target = query if case_sensitive else query.lower()
                    source = line if case_sensitive else line.lower()
                    if target in source:
                        results.append(i)
        except Exception:
            pass
        return results


def get_engine(filepath):
    if HAS_RUST:
        try:
            return log_engine_rs.LogEngine(filepath)
        except Exception as e:
            print(f"Failed to load Rust engine: {e}")
            return MockLogEngine(filepath)
    else:
        print("Rust extension not found. Using Mock Engine.")
        return MockLogEngine(filepath)
