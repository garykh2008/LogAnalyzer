import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox, ttk
import re
import json
import xml.etree.ElementTree as ET
import os
import time

# --- Helper Functions ---

def is_true(value):
	if value is None:
		return False
	return str(value).lower() in ('1', 'y', 'yes', 'true')

def fix_color(hex_str, default):
	if not hex_str:
		return default
	hex_str = hex_str.strip()
	if not hex_str.startswith('#'):
		return '#' + hex_str
	return hex_str

def bool_to_tat(value):
	return 'y' if value else 'n'

def color_to_tat(hex_color):
	if not hex_color: return ""
	return hex_color.replace("#", "")

# --- Core Classes ---

class Filter:
	def __init__(self, text, fore_color="#000000", back_color="#FFFFFF", enabled=True, is_regex=False, is_exclude=False):
		self.text = text
		self.fore_color = fore_color
		self.back_color = back_color
		self.enabled = enabled
		self.is_regex = is_regex
		self.is_exclude = is_exclude
		self.hit_count = 0

	def to_dict(self):
		d = self.__dict__.copy()
		if 'hit_count' in d: del d['hit_count']
		return d

class LogAnalyzerApp:
	def __init__(self, root):
		self.root = root
		self.root.geometry("1000x700")

		# Config
		self.config_file = "app_config.json"
		self.config = self.load_config()

		self.filters = []
		self.raw_lines = []

		# Cache structure: [(line_content, tags, raw_index), ...]
		# If None, it means "Raw Mode"
		self.filtered_cache = None

		# [New] Filter Match Cache: { filter_index: [raw_idx1, raw_idx2, ...] }
		# Stores raw indices of lines matched by specific filters
		self.filter_matches = {}

		self.current_log_path = None
		self.current_tat_path = None

		self.update_title()

		self.view_start_index = 0
		self.visible_rows = 50

		# Default font size 12
		self.font_size = self.config.get("font_size", 12)

		self.selected_raw_index = -1
		self.selection_offset = 0

		self.show_only_filtered_var = tk.BooleanVar(value=True)

		# Duration strings
		self.load_duration_str = "0.000s"
		self.filter_duration_str = "0.000s"

		self.drag_start_index = None

		# --- UI Layout ---

		# 1. Toolbar
		toolbar = tk.Frame(root, bd=1, relief=tk.RAISED)
		toolbar.pack(side=tk.TOP, fill=tk.X)

		tk.Button(toolbar, text="Open Log", command=self.load_log).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Frame(toolbar, width=10).pack(side=tk.LEFT)

		tk.Button(toolbar, text="Add Filter", command=self.add_filter_dialog).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Frame(toolbar, width=10).pack(side=tk.LEFT)

		chk_show = tk.Checkbutton(toolbar, text="Show Filtered Only (Ctrl+H)", variable=self.show_only_filtered_var, command=self.recalc_filtered_data)
		chk_show.pack(side=tk.LEFT, padx=5, pady=2)

		tk.Frame(toolbar, width=10).pack(side=tk.LEFT)
		tk.Button(toolbar, text="Import TAT", command=self.import_tat_filters).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Button(toolbar, text="Save TAT", command=self.quick_save_tat).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Button(toolbar, text="Save TAT As", command=self.save_as_tat_filters).pack(side=tk.LEFT, padx=2, pady=2)

		# 2. Status Bar
		self.status_bar = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
		self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

		# 3. Main Content Area (PanedWindow)
		self.paned_window = tk.PanedWindow(root, orient=tk.VERTICAL, sashwidth=4, sashrelief=tk.RAISED, bg="#d9d9d9")
		self.paned_window.pack(fill=tk.BOTH, expand=True)

		# --- Upper: Log View ---
		content_frame = tk.Frame(self.paned_window)

		self.scrollbar_y = tk.Scrollbar(content_frame, command=self.on_scroll_y)
		self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

		self.line_number_area = tk.Text(content_frame, width=7, wrap="none", font=("Consolas", self.font_size),
										state="disabled", bg="#f0f0f0", bd=0, highlightthickness=0, takefocus=0)
		self.line_number_area.pack(side=tk.LEFT, fill=tk.Y)
		self.line_number_area.tag_configure("right_align", justify="right")

		self.text_area = tk.Text(content_frame, wrap="none", font=("Consolas", self.font_size))
		self.scrollbar_x = tk.Scrollbar(content_frame, orient="horizontal", command=self.text_area.xview)
		self.text_area.configure(xscrollcommand=self.scrollbar_x.set)

		self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
		self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

		# Bindings
		self.text_area.bind("<MouseWheel>", self.on_mousewheel)
		self.text_area.bind("<Button-4>", self.on_mousewheel)
		self.text_area.bind("<Button-5>", self.on_mousewheel)
		self.text_area.bind("<Control-MouseWheel>", self.on_zoom)
		self.text_area.bind("<Control-Button-4>", self.on_zoom)
		self.text_area.bind("<Control-Button-5>", self.on_zoom)

		self.text_area.bind("<Double-Button-1>", self.on_log_double_click)
		self.text_area.bind("<Button-1>", self.on_log_single_click)

		self.line_number_area.bind("<MouseWheel>", self.on_mousewheel)
		self.line_number_area.bind("<Button-4>", self.on_mousewheel)
		self.line_number_area.bind("<Button-5>", self.on_mousewheel)
		self.line_number_area.bind("<Control-MouseWheel>", self.on_zoom)

		self.root.bind("<Control-h>", self.toggle_show_filtered)
		self.root.bind("<Control-H>", self.toggle_show_filtered)

		self.root.bind("<Control-Left>", self.on_nav_prev_match)
		self.root.bind("<Control-Right>", self.on_nav_next_match)

		self.paned_window.add(content_frame, height=450, minsize=100)

		# --- Lower: Filter View ---
		filter_frame = tk.LabelFrame(self.paned_window, text="Filters (Drag to Reorder)")

		cols = ("enabled", "type", "pattern", "hits")
		self.tree = ttk.Treeview(filter_frame, columns=cols, show="headings")

		self.tree.heading("enabled", text="En")
		self.tree.column("enabled", width=40, anchor="center")
		self.tree.heading("type", text="Type")
		self.tree.column("type", width=60, anchor="center")
		self.tree.heading("pattern", text="Pattern / Regex")
		self.tree.column("pattern", width=600, anchor="w")
		self.tree.heading("hits", text="Hits")
		self.tree.column("hits", width=80, anchor="e")

		tree_scroll = tk.Scrollbar(filter_frame, orient="vertical", command=self.tree.yview)
		self.tree.configure(yscrollcommand=tree_scroll.set)

		tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
		self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

		self.tree.bind("<Double-1>", self.on_filter_double_click)
		self.tree.bind("<space>", self.on_filter_toggle)
		self.tree.bind("<Delete>", self.on_filter_delete)
		self.tree.bind("<Button-3>", self.on_tree_right_click)
		self.tree.bind("<Button-1>", self.on_tree_click)
		self.tree.bind("<ButtonRelease-1>", self.on_tree_release)

		# Context Menu
		self.context_menu = tk.Menu(self.root, tearoff=0)
		self.context_menu.add_command(label="Remove Filter", command=self.on_filter_delete)
		self.context_menu.add_command(label="Edit Filter", command=self.edit_selected_filter)
		self.context_menu.add_separator()
		self.context_menu.add_command(label="Add Filter", command=self.add_filter_dialog)

		self.paned_window.add(filter_frame, minsize=100)

	# --- Config Management ---
	def load_config(self):
		if os.path.exists(self.config_file):
			try:
				with open(self.config_file, 'r') as f: return json.load(f)
			except: pass
		return {}

	def save_config(self):
		try:
			with open(self.config_file, 'w') as f: json.dump(self.config, f)
		except: pass

	# --- Title Update ---
	def update_title(self):
		log_name = os.path.basename(self.current_log_path) if self.current_log_path else "No file load"
		filter_name = os.path.basename(self.current_tat_path) if self.current_tat_path else "No filter file"
		self.root.title(f"[{log_name}] - [{filter_name}] - Log Analyzer")

	def update_status(self, msg):
		full_text = f"{msg}    |    Load Time: {self.load_duration_str}    |    Filter Time: {self.filter_duration_str}"
		self.status_bar.config(text=full_text)
		self.root.update_idletasks()

	# --- [Data Access Helpers] ---
	def get_total_count(self):
		if self.filtered_cache is None:
			return len(self.raw_lines)
		return len(self.filtered_cache)

	def get_view_item(self, index):
		if self.filtered_cache is None:
			if 0 <= index < len(self.raw_lines):
				return (self.raw_lines[index], [], index)
			return ("", [], -1)
		else:
			if 0 <= index < len(self.filtered_cache):
				return self.filtered_cache[index]
			return ("", [], -1)

	# --- File Loading ---
	def load_log(self):
		init_dir = self.config.get("last_log_dir", ".")
		filepath = filedialog.askopenfilename(initialdir=init_dir, filetypes=[("Log Files", "*.log *.txt"), ("All Files", "*.*")])
		if not filepath: return

		self.config["last_log_dir"] = os.path.dirname(filepath); self.save_config()
		self.update_status(f"Loading file: {filepath} ...")
		try:
			t_start = time.time()
			with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
				self.raw_lines = f.readlines()
			t_end = time.time()
			self.load_duration_str = f"{t_end - t_start:.4f}s"

			self.current_log_path = filepath; self.update_title()
			self.selected_raw_index = -1; self.selection_offset = 0
			self.filter_matches = {} # [New] Clear cache on new file
			self.update_status(f"Loaded {len(self.raw_lines)} lines. Indexing...")
			self.recalc_filtered_data()
		except Exception as e:
			messagebox.showerror("Load Error", str(e)); self.update_status("Load failed")

	# --- [NEW] Smart Update (Uses Cache for Instant Re-enable) ---
	# --- Smart Update (Optimized: Skip Hit Lines) ---
	def smart_update_filter(self, idx, is_enabling):
		flt = self.filters[idx]

		# 複雜情況回退到多執行緒全量重算
		if (not is_enabling and flt.is_exclude) or (self.filtered_cache is None and is_enabling):
			self.recalc_filtered_data(); return

		t_start = time.time()
		self.update_status("Smart updating...")

		# 保存視角
		target_raw_index = -1; anchor_offset = 0
		if self.selected_raw_index != -1:
			target_raw_index = self.selected_raw_index; anchor_offset = self.selection_offset
		elif self.filtered_cache and self.view_start_index < len(self.filtered_cache):
			target_raw_index = self.filtered_cache[self.view_start_index][2]; anchor_offset = 0

		tag_name = f"filter_{idx}"
		self.text_area.tag_config(tag_name, foreground=flt.fore_color, background=flt.back_color)

		new_cache = []
		show_only = self.show_only_filtered_var.get()

		# --- Logic A: Shrinking (關閉 Include / 開啟 Exclude) ---
		# 這裡邏輯不變，因為是在縮減資料，只處理 cache 即可
		if (not is_enabling and not flt.is_exclude) or (is_enabling and flt.is_exclude):
			rule = None
			if flt.is_regex:
				try: rule = re.compile(flt.text, re.IGNORECASE)
				except: pass
			else: rule = flt.text

			flt.hit_count = 0

			for line, tags, raw_idx in self.filtered_cache:
				matched = False
				if isinstance(rule, str): matched = (rule in line)
				elif rule: matched = (rule.search(line) is not None)

				# Disable Include
				if not is_enabling and not flt.is_exclude:
					if matched and tag_name in tags: tags.remove(tag_name)
					active_inc = any(f.enabled and not f.is_exclude for f in self.filters)
					if show_only and active_inc and not tags: continue

				# Enable Exclude
				if is_enabling and flt.is_exclude:
					if matched: flt.hit_count += 1; continue

				new_cache.append((line, tags, raw_idx))
			self.filtered_cache = new_cache

		# --- Logic B: Expanding (開啟 Include) [極致優化：跳過已命中] ---
		elif is_enabling and not flt.is_exclude:

			# 預編譯規則
			rule = None
			if flt.is_regex:
				try: rule = re.compile(flt.text, re.IGNORECASE)
				except: pass
			else: rule = flt.text

			flt.hit_count = 0

			# 準備 Exclude 規則 (用來檢查新命中的行是否該被排除)
			active_excludes = [f for f in self.filters if f.enabled and f.is_exclude]
			exclude_rules = []
			for f in active_excludes:
				if f.is_regex:
					try: exclude_rules.append(re.compile(f.text, re.IGNORECASE))
					except: pass
				else: exclude_rules.append(f.text)

			# 雙指針遍歷：同時掃描 raw_lines 和 old_cache
			# 利用 cache 是按順序排列的特性
			cache_idx = 0
			cache_len = len(self.filtered_cache)

			# 提取下一筆已存在的行號 (Sentinel)
			next_cached_raw_idx = self.filtered_cache[0][2] if cache_len > 0 else -1

			# 快取 append 方法加速
			cache_append = new_cache.append

			for raw_idx, line in enumerate(self.raw_lines):

				# 檢查：這一行是否已經被前面的 Filter 抓到了?
				if raw_idx == next_cached_raw_idx:
					# [Hit Skipped!] 已經在 Cache 裡，直接複製，不跑 Regex！
					cache_item = self.filtered_cache[cache_idx]
					cache_append(cache_item) # 原封不動搬過去，甚至不加新 Tag (因為 break 邏輯)

					# 移動 Cache 指標
					cache_idx += 1
					if cache_idx < cache_len:
						next_cached_raw_idx = self.filtered_cache[cache_idx][2]
					else:
						next_cached_raw_idx = -1 # End of cache

					continue # <--- 這裡就是您要的優化：跳過比對

				# --- 如果執行到這裡，代表這一行原本「沒顯示」 ---
				# 我們檢查它是否符合這個「新 Filter」

				matched = False
				if isinstance(rule, str):
					if rule in line: matched = True
				elif rule:
					if rule.search(line): matched = True

				if matched:
					# 檢查是否被 Exclude (因為原本沒顯示可能是被 Exclude 或是單純沒命中)
					# 我們必須確保新命中的行沒有被 Exclude 擋掉
					is_excluded = False
					for ex_rule in exclude_rules:
						if isinstance(ex_rule, str):
							if ex_rule in line: is_excluded = True; break
						else:
							if ex_rule.search(line): is_excluded = True; break

					if not is_excluded:
						flt.hit_count += 1
						# 命中！加入 Cache
						cache_append((line, [tag_name], raw_idx))

			self.filtered_cache = new_cache

		self.refresh_filter_list()

		# 還原視角
		new_start_index = 0
		if target_raw_index >= 0:
			found_idx = -1
			# 優化：假設順序沒變，我們可以從上次的位置附近找
			# 但為了安全，線性搜尋即可 (Python List C底層很快)
			for i, item in enumerate(self.filtered_cache):
				if item[2] >= target_raw_index: found_idx = i; break

			if found_idx != -1: new_start_index = max(0, found_idx - anchor_offset)
			else: new_start_index = max(0, len(self.filtered_cache) - self.visible_rows)

		self.view_start_index = new_start_index
		self.render_viewport(); self.update_scrollbar_thumb()

		t_end = time.time()
		self.filter_duration_str = f"{t_end - t_start:.4f}s (Smart)"
		mode_text = "Filtered" if show_only else "Full View"
		self.update_status(f"[{mode_text}] Showing {len(self.filtered_cache)} lines")

	# --- [Core] Full Recalc (Populates Cache) ---
	def recalc_filtered_data(self):
		target_raw_index = -1; anchor_offset = 0
		if self.selected_raw_index != -1:
			target_raw_index = self.selected_raw_index; anchor_offset = self.selection_offset
		elif self.filtered_cache and self.view_start_index < len(self.filtered_cache):
			target_raw_index = self.filtered_cache[self.view_start_index][2]; anchor_offset = 0

		t_start = time.time()
		self.update_status("Calculating filters...")

		for f in self.filters: f.hit_count = 0

		self.text_area.config(state=tk.NORMAL); self.text_area.delete("1.0", tk.END)
		self.line_number_area.config(state=tk.NORMAL); self.line_number_area.delete("1.0", tk.END)

		for i, flt in enumerate(self.filters):
			tag_name = f"filter_{i}"
			self.text_area.tag_config(tag_name, foreground=flt.fore_color, background=flt.back_color)
		self.text_area.tag_config("current_line", background="#0078D7", foreground="#FFFFFF")

		show_only_filtered = self.show_only_filtered_var.get()
		has_active_filters = any(f.enabled for f in self.filters)

		if not has_active_filters:
			self.filtered_cache = None
		else:
			self.filtered_cache = []
			txt_excludes = []
			reg_excludes = []
			txt_includes = []
			reg_includes = []
			has_active_includes = False
			filter_counts = [0] * len(self.filters)

			# [New] Prepare temp match lists for active filters
			# We will populate these lists as we scan
			temp_matches = {i: [] for i in range(len(self.filters)) if self.filters[i].enabled}

			for idx, f in enumerate(self.filters):
				if not f.enabled: continue
				if f.is_exclude:
					if f.is_regex:
						try: reg_excludes.append((re.compile(f.text, re.IGNORECASE), idx))
						except: pass
					else: txt_excludes.append((f.text, idx))
				else:
					has_active_includes = True
					tag = f"filter_{idx}"
					if f.is_regex:
						try: reg_includes.append((re.compile(f.text, re.IGNORECASE), tag, idx))
						except: pass
					else: txt_includes.append((f.text, tag, idx))

			cache_append = self.filtered_cache.append

			for raw_idx, line in enumerate(self.raw_lines):
				skip = False
				for text, idx in txt_excludes:
					if text in line:
						filter_counts[idx] += 1
						# [Cache] Store hit
						temp_matches[idx].append(raw_idx)
						skip = True; break
				if skip: continue
				for rule, idx in reg_excludes:
					if rule.search(line):
						filter_counts[idx] += 1
						# [Cache] Store hit
						temp_matches[idx].append(raw_idx)
						skip = True; break
				if skip: continue

				matched_tags = []
				is_match = False

				if not has_active_includes: is_match = True
				else:
					# Note: With 'break', we only capture the first match for display
					# But for caching purposes, if we want to cache ALL matches for future use,
					# we technically should scan all.
					# Trade-off: We stick to "First Match Wins" logic for speed.
					# So only the first matching filter gets the cache entry for this line.

					for text, tag, idx in txt_includes:
						if text in line:
							is_match = True; matched_tags.append(tag); filter_counts[idx] += 1
							temp_matches[idx].append(raw_idx) # [Cache]
							break
					if not is_match:
						for rule, tag, idx in reg_includes:
							if rule.search(line):
								is_match = True; matched_tags.append(tag); filter_counts[idx] += 1
								temp_matches[idx].append(raw_idx) # [Cache]
								break

				if show_only_filtered:
					if is_match: cache_append((line, matched_tags, raw_idx))
				else:
					final_tags = matched_tags if is_match else []
					cache_append((line, final_tags, raw_idx))

			for i, count in enumerate(filter_counts): self.filters[i].hit_count = count

			# [New] Update the persistent cache
			self.filter_matches.update(temp_matches)

		self.refresh_filter_list()

		new_start_index = 0
		new_total = self.get_total_count()
		if target_raw_index >= 0:
			if self.filtered_cache is None: found_idx = target_raw_index
			else:
				found_idx = -1
				for i, item in enumerate(self.filtered_cache):
					if item[2] >= target_raw_index: found_idx = i; break
			if found_idx != -1: new_start_index = max(0, found_idx - anchor_offset)
			else: new_start_index = max(0, new_total - self.visible_rows)

		self.view_start_index = new_start_index
		self.render_viewport(); self.update_scrollbar_thumb()
		t_end = time.time()
		self.filter_duration_str = f"{t_end - t_start:.4f}s"
		mode_text = "Filtered" if show_only_filtered else "Full View"
		self.update_status(f"[{mode_text}] Showing {new_total} lines (Total {len(self.raw_lines)} lines)")

	def toggle_show_filtered(self, event=None):
		current = self.show_only_filtered_var.get()
		self.show_only_filtered_var.set(not current)
		self.recalc_filtered_data()

	# --- Filter Navigation (Ctrl+Left/Right) ---
	def get_current_cache_index(self):
		if self.selected_raw_index == -1: return self.view_start_index
		if self.filtered_cache is None: return self.selected_raw_index
		for i, item in enumerate(self.filtered_cache):
			if item[2] == self.selected_raw_index: return i
		return self.view_start_index

	def navigate_to_match(self, direction):
		if self.filtered_cache is None:
			self.update_status("No active filters to navigate")
			return

		selected_items = self.tree.selection()
		if not selected_items:
			self.update_status("No filter selected for navigation")
			return

		target_tags = set()
		for item_id in selected_items:
			idx = self.tree.index(item_id)
			target_tags.add(f"filter_{idx}")

		if not target_tags: return

		current_idx = self.get_current_cache_index()
		total = len(self.filtered_cache)
		found_idx = -1

		if direction == 1: # Next
			for i in range(current_idx + 1, total):
				line_tags = self.filtered_cache[i][1]
				if any(t in target_tags for t in line_tags): found_idx = i; break
		else: # Prev
			for i in range(current_idx - 1, -1, -1):
				line_tags = self.filtered_cache[i][1]
				if any(t in target_tags for t in line_tags): found_idx = i; break

		if found_idx != -1:
			self.selected_raw_index = self.filtered_cache[found_idx][2]
			half_view = self.visible_rows // 2
			new_start = max(0, found_idx - half_view)
			new_start = min(new_start, max(0, total - self.visible_rows))
			self.view_start_index = new_start
			self.selection_offset = found_idx - new_start
			self.render_viewport(); self.update_scrollbar_thumb()
			self.update_status(f"Jumped to line {self.selected_raw_index + 1}")
		else: self.update_status("No more matches found in that direction")

	def on_nav_next_match(self, event): self.navigate_to_match(1)
	def on_nav_prev_match(self, event): self.navigate_to_match(-1)

	# --- Log Interaction ---
	def on_log_single_click(self, event):
		self.text_area.tag_remove("current_line", "1.0", tk.END)
		try:
			index = self.text_area.index(f"@{event.x},{event.y}")
			ui_row = int(index.split('.')[0])
			self.text_area.mark_set(tk.INSERT, index)
			self.text_area.tag_add("current_line", f"{ui_row}.0", f"{ui_row}.end")
			self.text_area.tag_raise("current_line")

			cache_index = self.view_start_index + (ui_row - 1)
			total = self.get_total_count()
			if 0 <= cache_index < total:
				_, _, raw_idx = self.get_view_item(cache_index)
				self.selected_raw_index = raw_idx
				self.selection_offset = ui_row - 1
			else:
				self.selected_raw_index = -1; self.selection_offset = 0
		except Exception as e: print(e)

	def on_log_double_click(self, event):
		try:
			try: selected_text = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
			except tk.TclError: selected_text = ""
			if not selected_text:
				cursor_index = self.text_area.index(f"@{event.x},{event.y}")
				line_start = cursor_index.split('.')[0] + ".0"
				line_end = cursor_index.split('.')[0] + ".end"
				selected_text = self.text_area.get(line_start, line_end).strip()
			if selected_text: self.add_filter_dialog(initial_text=selected_text)
		except Exception as e: print(f"Double click error: {e}")

	# --- Rendering ---
	def render_viewport(self):
		self.text_area.config(state=tk.NORMAL); self.text_area.delete("1.0", tk.END)
		self.line_number_area.config(state=tk.NORMAL); self.line_number_area.delete("1.0", tk.END)
		total = self.get_total_count()
		if total == 0:
			self.text_area.config(state=tk.DISABLED); self.line_number_area.config(state=tk.DISABLED); return

		end_index = min(self.view_start_index + self.visible_rows, total)

		display_buffer = []
		line_nums_buffer = []
		tag_buffer = []

		for i in range(self.view_start_index, end_index):
			line, tags, raw_idx = self.get_view_item(i)
			display_buffer.append(line)
			line_nums_buffer.append(str(raw_idx + 1))

			relative_idx = i - self.view_start_index + 1
			if tags: tag_buffer.append((relative_idx, tags))
			if raw_idx == self.selected_raw_index:
				tag_buffer.append((relative_idx, ["current_line"]))

		full_text = "".join(display_buffer)
		self.text_area.insert("1.0", full_text)

		line_nums_text = "\n".join(line_nums_buffer)
		self.line_number_area.insert("1.0", line_nums_text)
		self.line_number_area.tag_add("right_align", "1.0", "end")

		for rel_idx, tags in tag_buffer:
			for tag in tags: self.text_area.tag_add(tag, f"{rel_idx}.0", f"{rel_idx}.end")

		self.text_area.tag_raise("current_line")
		self.text_area.config(state=tk.DISABLED); self.line_number_area.config(state=tk.DISABLED)

	def update_scrollbar_thumb(self):
		total = self.get_total_count()
		if total == 0: self.scrollbar_y.set(0, 1)
		else:
			page_size = self.visible_rows / total
			start = self.view_start_index / total
			end = start + page_size
			self.scrollbar_y.set(start, end)

	def on_scroll_y(self, *args):
		total = self.get_total_count()
		if total == 0: return
		op = args[0]
		if op == "scroll":
			units = int(args[1]); what = args[2]
			step = self.visible_rows if what == "pages" else 1
			new_start = self.view_start_index + (units * step)
		elif op == "moveto":
			fraction = float(args[1]); new_start = int(total * fraction)
		new_start = max(0, min(new_start, total - self.visible_rows))
		if new_start != self.view_start_index:
			self.view_start_index = int(new_start)
			self.render_viewport(); self.update_scrollbar_thumb()

	def on_mousewheel(self, event):
		total = self.get_total_count();
		if total == 0: return
		scroll_dir = 0
		if event.num == 5 or event.delta < 0: scroll_dir = 1
		elif event.num == 4 or event.delta > 0: scroll_dir = -1
		step = 3; new_start = self.view_start_index + (scroll_dir * step)
		new_start = max(0, min(new_start, total - self.visible_rows))
		if new_start != self.view_start_index:
			self.view_start_index = int(new_start)
			self.render_viewport(); self.update_scrollbar_thumb()
		return "break"

	def on_zoom(self, event):
		delta = 0
		if event.num == 5 or event.delta < 0: delta = -1
		elif event.num == 4 or event.delta > 0: delta = 1
		if delta != 0:
			new_size = self.font_size + delta; new_size = max(6, min(new_size, 50))
			if new_size != self.font_size:
				self.font_size = new_size
				self.text_area.configure(font=("Consolas", self.font_size))
				self.line_number_area.configure(font=("Consolas", self.font_size))
				self.config["font_size"] = self.font_size; self.save_config()
		return "break"

	# --- Filter List & Editing ---
	def refresh_filter_list(self):
		for item in self.tree.get_children(): self.tree.delete(item)
		for idx, flt in enumerate(self.filters):
			en_str = "☑" if flt.enabled else "☐"
			type_str = "Excl" if flt.is_exclude else ("Regex" if flt.is_regex else "Text")
			item_id = self.tree.insert("", "end", values=(en_str, type_str, flt.text, str(flt.hit_count)))
			tag_name = f"row_{idx}"
			self.tree.item(item_id, tags=(tag_name,))
			self.tree.tag_configure(tag_name, foreground=flt.fore_color, background=flt.back_color)

	def on_tree_click(self, event):
		region = self.tree.identify("region", event.x, event.y)
		if region == "cell":
			column = self.tree.identify_column(event.x)
			if column == "#1":
				item_id = self.tree.identify_row(event.y)
				if item_id:
					idx = self.tree.index(item_id)
					self.filters[idx].enabled = not self.filters[idx].enabled
					# [Modified] Use Smart Update instead of Full Recalc
					self.smart_update_filter(idx, self.filters[idx].enabled)
					return "break"
			else:
				item_id = self.tree.identify_row(event.y)
				if item_id: self.drag_start_index = self.tree.index(item_id)

	def on_tree_release(self, event):
		if self.drag_start_index is None: return
		target_id = self.tree.identify_row(event.y)
		if target_id:
			target_index = self.tree.index(target_id)
			if target_index != self.drag_start_index:
				item = self.filters.pop(self.drag_start_index)
				self.filters.insert(target_index, item)
				self.recalc_filtered_data() # Order changed, must full recalc
		self.drag_start_index = None

	def on_tree_right_click(self, event):
		item_id = self.tree.identify_row(event.y)
		if item_id:
			self.tree.selection_set(item_id)
			self.context_menu.entryconfig("Remove Filter", state="normal")
			self.context_menu.entryconfig("Edit Filter", state="normal")
		else:
			self.tree.selection_remove(self.tree.selection())
			self.context_menu.entryconfig("Remove Filter", state="disabled")
			self.context_menu.entryconfig("Edit Filter", state="disabled")
		self.context_menu.post(event.x_root, event.y_root)

	def edit_selected_filter(self):
		selected = self.tree.selection()
		if not selected: return
		item_id = selected[0]; idx = self.tree.index(item_id)
		self.open_filter_dialog(self.filters[idx], idx)

	def on_filter_toggle(self, event):
		selected_item = self.tree.selection()
		if not selected_item: return
		for item_id in selected_item:
			idx = self.tree.index(item_id)
			self.filters[idx].enabled = not self.filters[idx].enabled
			# Use Smart Update
			self.smart_update_filter(idx, self.filters[idx].enabled)

	def on_filter_delete(self, event=None):
		selected_items = self.tree.selection()
		if not selected_items: return
		indices_to_delete = sorted([self.tree.index(item) for item in selected_items], reverse=True)
		for idx in indices_to_delete:
			del self.filters[idx]
			if idx in self.filter_matches: del self.filter_matches[idx] # [New] Remove from cache
		self.recalc_filtered_data()

	def on_filter_double_click(self, event):
		item_id = self.tree.identify_row(event.y)
		if not item_id: return
		if self.tree.identify_column(event.x) == "#1": return
		idx = self.tree.index(item_id)
		self.open_filter_dialog(self.filters[idx], idx)

	def add_filter_dialog(self, initial_text=None):
		self.open_filter_dialog(None, index=None, initial_text=initial_text)

	def open_filter_dialog(self, filter_obj=None, index=None, initial_text=None):
		dialog = tk.Toplevel(self.root)
		dialog.title("Edit Filter" if filter_obj else "Add Filter")
		tk.Label(dialog, text="Pattern:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
		entry_text = tk.Entry(dialog, width=40)
		entry_text.grid(row=0, column=1, columnspan=2, padx=5, pady=5)
		if filter_obj: entry_text.insert(0, filter_obj.text)
		elif initial_text: entry_text.insert(0, initial_text)
		var_regex = tk.BooleanVar(value=filter_obj.is_regex if filter_obj else False)
		var_exclude = tk.BooleanVar(value=filter_obj.is_exclude if filter_obj else False)
		tk.Checkbutton(dialog, text="Regex", variable=var_regex).grid(row=1, column=1, sticky="w")
		tk.Checkbutton(dialog, text="Exclude", variable=var_exclude).grid(row=1, column=2, sticky="w")
		colors = {"fg": filter_obj.fore_color if filter_obj else "#000000", "bg": filter_obj.back_color if filter_obj else "#FFFFFF"}
		def pick_fg():
			c = colorchooser.askcolor(color=colors["fg"])[1]
			if c: colors["fg"] = c; btn_fg.config(bg=c)
		def pick_bg():
			c = colorchooser.askcolor(color=colors["bg"])[1]
			if c: colors["bg"] = c; btn_bg.config(bg=c)
		btn_fg = tk.Button(dialog, text="Text Color", bg=colors["fg"], command=pick_fg)
		btn_fg.grid(row=2, column=1, sticky="ew", padx=2)
		btn_bg = tk.Button(dialog, text="Back Color", bg=colors["bg"], command=pick_bg)
		btn_bg.grid(row=2, column=2, sticky="ew", padx=2)
		def save():
			text = entry_text.get()
			if not text: return
			if filter_obj:
				filter_obj.text = text; filter_obj.fore_color = colors["fg"]; filter_obj.back_color = colors["bg"]
				filter_obj.is_regex = var_regex.get(); filter_obj.is_exclude = var_exclude.get()
				if index in self.filter_matches: del self.filter_matches[index] # [New] Invalidate cache
				self.recalc_filtered_data()
			else:
				new_filter = Filter(text, colors["fg"], colors["bg"], enabled=True, is_regex=var_regex.get(), is_exclude=var_exclude.get())
				self.filters.append(new_filter)
				self.recalc_filtered_data()
			dialog.destroy()
		tk.Button(dialog, text="Save", command=save, width=15).grid(row=3, column=0, columnspan=3, pady=10)

	# --- File I/O ---
	def _write_tat_file(self, filepath):
		try:
			root = ET.Element("TextAnalysisTool.NET")
			root.set("version", "2017-01-24")
			root.set("showOnlyFilteredLines", "False")
			filters_node = ET.SubElement(root, "filters")
			for flt in self.filters:
				f_node = ET.SubElement(filters_node, "filter")
				f_node.set("enabled", bool_to_tat(flt.enabled))
				f_node.set("excluding", bool_to_tat(flt.is_exclude))
				f_node.set("text", flt.text)
				f_node.set("type", "matches_text")
				f_node.set("regex", bool_to_tat(flt.is_regex))
				f_node.set("case_sensitive", "n")
				if flt.fore_color != "#000000": f_node.set("foreColor", color_to_tat(flt.fore_color))
				if flt.back_color != "#FFFFFF": f_node.set("backColor", color_to_tat(flt.back_color))
				f_node.set("description", "")
			tree = ET.ElementTree(root)
			tree.write(filepath, encoding="utf-8", xml_declaration=True)
			return True
		except Exception as e: messagebox.showerror("Write Error", str(e)); return False

	def quick_save_tat(self):
		if self.current_tat_path:
			if self._write_tat_file(self.current_tat_path): messagebox.showinfo("Save", "Saved successfully")
		else: self.save_as_tat_filters()

	def save_as_tat_filters(self):
		init_dir = self.config.get("last_filter_dir", ".")
		filepath = filedialog.asksaveasfilename(initialdir=init_dir, defaultextension=".tat", filetypes=[("TextAnalysisTool", "*.tat"), ("XML", "*.xml")])
		if not filepath: return
		self.config["last_filter_dir"] = os.path.dirname(filepath); self.save_config()
		if self._write_tat_file(filepath):
			self.current_tat_path = filepath; self.update_title()
			messagebox.showinfo("Success", "File saved")

	def import_tat_filters(self):
		init_dir = self.config.get("last_filter_dir", ".")
		filepath = filedialog.askopenfilename(initialdir=init_dir, filetypes=[("TextAnalysisTool", "*.tat"), ("XML", "*.xml")])
		if not filepath: return
		self.config["last_filter_dir"] = os.path.dirname(filepath); self.save_config()
		try:
			tree = ET.parse(filepath); root = tree.getroot()
			filters_node = root.findall('.//filter')
			new_filters = []
			for f in filters_node:
				enabled = is_true(f.get('enabled'))
				text = f.get('text')
				fore = fix_color(f.get('foreColor'), "#000000")
				back = fix_color(f.get('backColor'), "#FFFFFF")
				is_exclude = is_true(f.get('excluding'))
				is_regex = is_true(f.get('regex'))
				if text: new_filters.append(Filter(text, fore, back, enabled, is_regex, is_exclude))
			self.filters = new_filters
			self.current_tat_path = filepath; self.update_title()
			self.filter_matches = {} # [New] Invalidate all cache on new import
			self.recalc_filtered_data()
			messagebox.showinfo("Success", f"Imported {len(new_filters)} filters")
		except Exception as e: messagebox.showerror("Import Error", str(e))

	# JSON methods
	def export_filters(self):
		init_dir = self.config.get("last_filter_dir", ".")
		filepath = filedialog.asksaveasfilename(initialdir=init_dir, defaultextension=".json", filetypes=[("JSON", "*.json")])
		if not filepath: return
		self.config["last_filter_dir"] = os.path.dirname(filepath); self.save_config()
		data = [f.to_dict() for f in self.filters]
		with open(filepath, 'w') as f: json.dump(data, f, indent=4)

	def import_json_filters(self):
		init_dir = self.config.get("last_filter_dir", ".")
		filepath = filedialog.askopenfilename(initialdir=init_dir, filetypes=[("JSON", "*.json")])
		if not filepath: return
		self.config["last_filter_dir"] = os.path.dirname(filepath); self.save_config()
		try:
			with open(filepath, 'r') as f:
				data = json.load(f)
				self.filters = [Filter(**item) for item in data]
			self.filter_matches = {} # [New] Invalidate cache
			self.recalc_filtered_data()
		except Exception as e: messagebox.showerror("Error", f"JSON Import Failed: {e}")

if __name__ == "__main__":
	root = tk.Tk()
	app = LogAnalyzerApp(root)
	root.mainloop()