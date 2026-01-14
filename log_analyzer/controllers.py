from PySide6.QtCore import QObject, Signal, QTimer
from .engine_wrapper import get_engine
from .utils import load_tat_filters, save_tat_filters
import os
import time
import bisect

class LogController(QObject):
    """
    Handles Log file management.
    """
    log_loaded = Signal(str) # filepath
    log_closed = Signal(str) # filepath
    
    def __init__(self):
        super().__init__()
        self.loaded_logs = {} # {path: engine}
        self.log_order = [] # Ordered paths
        self.current_log_path = None
        self.current_engine = None

    def load_log(self, filepath):
        if not filepath or not os.path.exists(filepath): return False
        
        filepath = os.path.abspath(filepath)
        if filepath in self.loaded_logs:
            self.set_current_log(filepath)
            return True

        try:
            engine = get_engine(filepath)
            self.loaded_logs[filepath] = engine
            self.log_order.append(filepath)
            self.set_current_log(filepath)
            self.log_loaded.emit(filepath)
            return True
        except Exception as e:
            print(f"Error loading log {filepath}: {e}")
            return False

    def set_current_log(self, filepath):
        if filepath in self.loaded_logs:
            self.current_log_path = filepath
            self.current_engine = self.loaded_logs[filepath]
            return True
        return False

    def close_log(self, filepath):
        if filepath in self.loaded_logs:
            del self.loaded_logs[filepath]
            if filepath in self.log_order:
                self.log_order.remove(filepath)
            
            if self.current_log_path == filepath:
                self.current_log_path = None
                self.current_engine = None
                if self.log_order:
                    self.set_current_log(self.log_order[0])
            
            self.log_closed.emit(filepath)
            return True
        return False

    def clear_all_logs(self):
        logs = list(self.loaded_logs.keys())
        for fp in logs:
            self.close_log(fp)

class SearchController(QObject):
    search_results_ready = Signal(list, str) # results, query
    
    def __init__(self):
        super().__init__()
        self.search_results = []
        self.history = []
        self.last_query = ""
        self.last_case_sensitive = False

    def perform_search(self, engine, query, case_sensitive=False):
        if not engine or not query: 
            self.search_results = []
            self.search_results_ready.emit([], query)
            return

        self.last_query = query
        self.last_case_sensitive = case_sensitive
        self._add_to_history(query)
        
        # Perform search
        results = engine.search(query, False, case_sensitive)
        self.search_results = results
        self.search_results_ready.emit(results, query)

    def find_next(self, current_raw_index, wrap=True):
        if not self.search_results: return None
        
        idx = bisect.bisect_right(self.search_results, current_raw_index)
        if idx >= len(self.search_results):
            if wrap:
                return self.search_results[0]
            else:
                return None
        return self.search_results[idx]

    def find_previous(self, current_raw_index, wrap=True):
        if not self.search_results: return None
        
        idx = bisect.bisect_left(self.search_results, current_raw_index) - 1
        if idx < 0:
            if wrap:
                return self.search_results[-1]
            else:
                return None
        return self.search_results[idx]

    def _add_to_history(self, query):
        if query in self.history:
            self.history.remove(query)
        self.history.insert(0, query)
        if len(self.history) > 10:
            self.history.pop()

    def get_history(self):
        return self.history

class FilterController(QObject):
    filters_changed = Signal() # Filters list changed (add/remove/reorder)
    filter_results_ready = Signal(object, object) # results (tuple), rust_filters (list)
    
    def __init__(self):
        super().__init__()
        self.filters = []
        self.filters_dirty_cache = True
        self.cached_filter_results = None
        self.current_filter_file = None
        self.filters_modified = False

    def add_filter(self, filter_data):
        # Ensure hits is 0
        filter_data["hits"] = 0
        self.filters.append(filter_data)
        self.invalidate_cache()
        self.filters_changed.emit()

    def update_filter(self, index, filter_data):
        if 0 <= index < len(self.filters):
            self.filters[index].update(filter_data)
            self.invalidate_cache()
            self.filters_changed.emit()

    def remove_filter(self, index):
        if 0 <= index < len(self.filters):
            del self.filters[index]
            self.invalidate_cache()
            self.filters_changed.emit()
            
    def move_filter(self, from_index, to_index):
        if 0 <= from_index < len(self.filters) and 0 <= to_index < len(self.filters):
            item = self.filters.pop(from_index)
            self.filters.insert(to_index, item)
            self.invalidate_cache()
            self.filters_changed.emit()

    def set_filters(self, new_filters):
        self.filters = new_filters
        self.invalidate_cache()
        self.filters_changed.emit()

    def set_cache(self, cache):
        """Restores a previously calculated filter result cache."""
        self.cached_filter_results = cache
        self.filters_dirty_cache = False

    def toggle_filter(self, index, enabled):
        if 0 <= index < len(self.filters):
            if self.filters[index]["enabled"] != enabled:
                self.filters[index]["enabled"] = enabled
                self.invalidate_cache()
                self.filters_changed.emit()

    def invalidate_cache(self, mark_modified=True):
        self.filters_dirty_cache = True
        if mark_modified:
            self.filters_modified = True

    def apply_filters(self, engine):
        if not engine: return
        
        if self.filters_dirty_cache:
            rust_f = [(f["text"], f["is_regex"], f["is_exclude"], False, i) for i, f in enumerate(self.filters) if f["enabled"]]
            try:
                res = engine.filter(rust_f)
                self.cached_filter_results = (res, rust_f)
                self.filters_dirty_cache = False
                
                # Update hits locally
                # res[2] is subset_counts
                subset_counts = res[2]
                for j, rf in enumerate(rust_f):
                    original_idx = rf[4]
                    if j < len(subset_counts):
                        self.filters[original_idx]["hits"] = subset_counts[j]
                
                self.filter_results_ready.emit(res, rust_f)
            except Exception as e:
                print(f"Filter error: {e}")
        elif self.cached_filter_results:
            self.filter_results_ready.emit(*self.cached_filter_results)

    def load_from_file(self, filepath):
        loaded = load_tat_filters(filepath)
        if loaded:
            self.filters = loaded
            self.current_filter_file = filepath
            self.filters_modified = False
            self.filters_dirty_cache = True
            self.filters_changed.emit()
            return True
        return False

    def save_to_file(self, filepath):
        if save_tat_filters(filepath, self.filters):
            self.current_filter_file = filepath
            self.filters_modified = False
            return True
        return False
