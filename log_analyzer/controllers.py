from PySide6.QtCore import QObject, Signal, QTimer
from .engine_wrapper import get_engine
import os
import time
import bisect

class LogController(QObject):
    """
    Handles Log file management and Search logic.
    """
    log_loaded = Signal(str) # filepath
    log_closed = Signal(str) # filepath
    search_results_ready = Signal(list, str) # results, query
    match_found = Signal(int) # raw_index

    def __init__(self):
        super().__init__()
        self.loaded_logs = {} # {path: engine}
        self.log_order = [] # Ordered paths
        self.current_log_path = None
        self.current_engine = None
        
        self.search_results = []
        self.last_query = ""
        self.last_case_sensitive = False

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
            self.search_results = [] # Clear search on switch? Or cache?
            # Ideally cache search results per file, but for now reset
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

    def search(self, query, case_sensitive=False):
        if not self.current_engine or not query: 
            self.search_results = []
            self.search_results_ready.emit([], query)
            return

        self.last_query = query
        self.last_case_sensitive = case_sensitive
        
        # Perform search
        results = self.current_engine.search(query, False, case_sensitive)
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
