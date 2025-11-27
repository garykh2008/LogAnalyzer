import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox, ttk
import re
import json
import xml.etree.ElementTree as ET
import os

# --- 輔助函式 ---

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

# --- 核心類別 ---

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

		# 設定檔相關
		self.config_file = "app_config.json"
		self.config = self.load_config()

		self.filters = []
		self.raw_lines = []

		# 快取結構: [(line_content, tags, raw_index), ...]
		self.filtered_cache = []

		self.current_log_path = None
		self.current_tat_path = None

		self.update_title()

		self.view_start_index = 0
		self.visible_rows = 50
		self.font_size = 10

		# [新增] 記錄選取狀態
		self.selected_raw_index = -1  # 目前選取的原始行號
		self.selection_offset = 0     # 選取的行距離視窗頂部幾行 (用於保持視角)

		self.show_only_filtered_var = tk.BooleanVar(value=True)

		# --- 介面佈局 ---

		# 1. 頂部工具列
		toolbar = tk.Frame(root, bd=1, relief=tk.RAISED)
		toolbar.pack(side=tk.TOP, fill=tk.X)

		tk.Button(toolbar, text="開啟 Log", command=self.load_log).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Frame(toolbar, width=10).pack(side=tk.LEFT)

		tk.Button(toolbar, text="新增 Filter", command=self.add_filter_dialog).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Frame(toolbar, width=10).pack(side=tk.LEFT)

		chk_show = tk.Checkbutton(toolbar, text="只顯示過濾結果 (Ctrl+H)", variable=self.show_only_filtered_var, command=self.recalc_filtered_data)
		chk_show.pack(side=tk.LEFT, padx=5, pady=2)

		tk.Frame(toolbar, width=10).pack(side=tk.LEFT)
		tk.Button(toolbar, text="匯入 TAT", command=self.import_tat_filters).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Button(toolbar, text="儲存 TAT", command=self.quick_save_tat).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Button(toolbar, text="另存 TAT", command=self.save_as_tat_filters).pack(side=tk.LEFT, padx=2, pady=2)

		tk.Button(toolbar, text="JSON 匯出", command=self.export_filters).pack(side=tk.RIGHT, padx=2, pady=2)
		tk.Button(toolbar, text="JSON 匯入", command=self.import_json_filters).pack(side=tk.RIGHT, padx=2, pady=2)

		# 2. 底部狀態列
		self.status_bar = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
		self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

		# 3. 中間可調整區域
		self.paned_window = tk.PanedWindow(root, orient=tk.VERTICAL, sashwidth=4, sashrelief=tk.RAISED, bg="#d9d9d9")
		self.paned_window.pack(fill=tk.BOTH, expand=True)

		# --- 上半部：Log 顯示區 ---
		content_frame = tk.Frame(self.paned_window)

		self.scrollbar_y = tk.Scrollbar(content_frame, command=self.on_scroll_y)
		self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

		self.text_area = tk.Text(content_frame, wrap="none", font=("Consolas", self.font_size))
		self.scrollbar_x = tk.Scrollbar(content_frame, orient="horizontal", command=self.text_area.xview)
		self.text_area.configure(xscrollcommand=self.scrollbar_x.set)

		self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
		self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

		# 綁定事件
		self.text_area.bind("<MouseWheel>", self.on_mousewheel)
		self.text_area.bind("<Button-4>", self.on_mousewheel)
		self.text_area.bind("<Button-5>", self.on_mousewheel)
		self.text_area.bind("<Control-MouseWheel>", self.on_zoom)
		self.text_area.bind("<Control-Button-4>", self.on_zoom)
		self.text_area.bind("<Control-Button-5>", self.on_zoom)

		self.text_area.bind("<Double-Button-1>", self.on_log_double_click)
		self.text_area.bind("<Button-1>", self.on_log_single_click)

		self.root.bind("<Control-h>", self.toggle_show_filtered)
		self.root.bind("<Control-H>", self.toggle_show_filtered)

		self.paned_window.add(content_frame, height=450, minsize=100)

		# --- 下半部：Filter 列表區 ---
		filter_frame = tk.LabelFrame(self.paned_window, text="Active Filters (空白鍵: 開關 | 雙擊: 編輯 | Delete: 刪除)")

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

		self.paned_window.add(filter_frame, minsize=100)

	# --- 設定檔管理 ---
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

	# --- 標題更新邏輯 ---
	def update_title(self):
		log_name = os.path.basename(self.current_log_path) if self.current_log_path else "No file load"
		filter_name = os.path.basename(self.current_tat_path) if self.current_tat_path else "No filter file"
		self.root.title(f"[{log_name}] - [{filter_name}] - Log Analyzer")

	def update_status(self, msg):
		self.status_bar.config(text=msg)
		self.root.update_idletasks()

	# --- 檔案讀取 ---
	def load_log(self):
		init_dir = self.config.get("last_log_dir", ".")
		filepath = filedialog.askopenfilename(initialdir=init_dir, filetypes=[("Log Files", "*.log *.txt"), ("All Files", "*.*")])
		if not filepath: return

		self.config["last_log_dir"] = os.path.dirname(filepath); self.save_config()
		self.update_status(f"正在讀取檔案: {filepath} ...")
		try:
			with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
				self.raw_lines = f.readlines()
			self.current_log_path = filepath; self.update_title()

			# 重置選取狀態
			self.selected_raw_index = -1
			self.selection_offset = 0

			self.update_status(f"讀取完成，共 {len(self.raw_lines)} 行。正在建立索引...")
			self.recalc_filtered_data()
		except Exception as e:
			messagebox.showerror("讀取錯誤", str(e)); self.update_status("讀取失敗")

	# --- [核心] 過濾邏輯 (視角與焦點還原) ---
	def recalc_filtered_data(self):
		# 1. 準備視角還原資訊
		# 如果有選取行，優先鎖定選取行；否則鎖定視窗第一行
		anchor_raw_index = -1
		anchor_offset = 0

		if self.selected_raw_index != -1:
			# 鎖定選取行
			anchor_raw_index = self.selected_raw_index
			anchor_offset = self.selection_offset
		elif self.filtered_cache and self.view_start_index < len(self.filtered_cache):
			# 鎖定頂端行
			anchor_raw_index = self.filtered_cache[self.view_start_index][2]
			anchor_offset = 0

		self.update_status("正在套用過濾器...")

		for f in self.filters: f.hit_count = 0

		self.text_area.config(state=tk.NORMAL)
		self.text_area.delete("1.0", tk.END)

		for i, flt in enumerate(self.filters):
			tag_name = f"filter_{i}"
			self.text_area.tag_config(tag_name, foreground=flt.fore_color, background=flt.back_color)

		# [重要] 設定選取高亮的 Tag (確保它比其他 Filter 顏色優先)
		# background: 深藍, foreground: 白
		self.text_area.tag_config("current_line", background="#0078D7", foreground="#FFFFFF")

		self.filtered_cache = []
		show_only_filtered = self.show_only_filtered_var.get()

		compiled_excludes = []
		for idx, f in enumerate(self.filters):
			if f.enabled and f.is_exclude:
				if f.is_regex:
					try: compiled_excludes.append((re.compile(f.text, re.IGNORECASE), idx, True))
					except: pass
				else:
					compiled_excludes.append((f.text, idx, False))

		active_has_includes = any(f.enabled and not f.is_exclude for f in self.filters)
		compiled_includes = []
		for idx, flt in enumerate(self.filters):
			if flt.enabled and not flt.is_exclude:
				tag = f"filter_{idx}"
				if flt.is_regex:
					try: compiled_includes.append((re.compile(flt.text, re.IGNORECASE), tag, idx, True))
					except: pass
				else:
					compiled_includes.append((flt.text, tag, idx, False))

		for raw_idx, line in enumerate(self.raw_lines):
			skip = False
			for rule, idx, is_re in compiled_excludes:
				matched = False
				if is_re:
					if rule.search(line): matched = True
				else:
					if rule in line: matched = True
				if matched:
					self.filters[idx].hit_count += 1
					skip = True
					break

			matched_tags = []
			is_match = False

			if not skip:
				if not active_has_includes:
					is_match = True
				else:
					for rule, tag, idx, is_re in compiled_includes:
						matched = False
						if is_re:
							if rule.search(line): matched = True
						else:
							if rule in line: matched = True
						if matched:
							is_match = True
							matched_tags.append(tag)
							self.filters[idx].hit_count += 1

			if show_only_filtered:
				if not skip and is_match:
					self.filtered_cache.append((line, matched_tags, raw_idx))
			else:
				final_tags = matched_tags if (not skip and is_match) else []
				self.filtered_cache.append((line, final_tags, raw_idx))

		self.refresh_filter_list()

		# 2. 執行視角還原
		new_start_index = 0
		if anchor_raw_index >= 0:
			# 在新的 cache 中尋找 >= anchor_raw_index 的行
			found_idx = -1
			for i, item in enumerate(self.filtered_cache):
				if item[2] >= anchor_raw_index:
					found_idx = i
					break

			if found_idx != -1:
				# 找到了，嘗試恢復相對位置 (offset)
				new_start_index = max(0, found_idx - anchor_offset)
			else:
				# 沒找到 (可能在最後)，停在尾部
				new_start_index = max(0, len(self.filtered_cache) - self.visible_rows)

		self.view_start_index = new_start_index

		self.render_viewport()
		self.update_scrollbar_thumb()

		mode_text = "過濾檢視" if show_only_filtered else "完整檢視"
		self.update_status(f"[{mode_text}] 顯示 {len(self.filtered_cache)} 行 (原始 {len(self.raw_lines)} 行)")

	def toggle_show_filtered(self, event=None):
		current = self.show_only_filtered_var.get()
		self.show_only_filtered_var.set(not current)
		self.recalc_filtered_data()

	# --- [修改] 單擊 Log 行：記錄選取資訊 ---
	def on_log_single_click(self, event):
		# 移除舊高亮
		self.text_area.tag_remove("current_line", "1.0", tk.END)

		# 取得點擊位置的 UI 行號 (1-based)
		try:
			index = self.text_area.index(f"@{event.x},{event.y}")
			ui_row = int(index.split('.')[0])

			# 加高亮
			self.text_area.tag_add("current_line", f"{ui_row}.0", f"{ui_row}.end")
			# 確保高亮顯示在最上層
			self.text_area.tag_raise("current_line")

			# [重要] 記錄選取資訊供下次 recalc 使用
			# 換算回 cache index
			cache_index = self.view_start_index + (ui_row - 1)
			if 0 <= cache_index < len(self.filtered_cache):
				# 記住原始檔案行號
				self.selected_raw_index = self.filtered_cache[cache_index][2]
				# 記住它距離視窗頂部幾行 (Offset)
				self.selection_offset = ui_row - 1
			else:
				self.selected_raw_index = -1
				self.selection_offset = 0

		except Exception as e:
			print(e)

	def on_log_double_click(self, event):
		try:
			try:
				selected_text = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
			except tk.TclError:
				selected_text = ""

			if not selected_text:
				cursor_index = self.text_area.index(f"@{event.x},{event.y}")
				line_start = cursor_index.split('.')[0] + ".0"
				line_end = cursor_index.split('.')[0] + ".end"
				selected_text = self.text_area.get(line_start, line_end)
				selected_text = selected_text.strip()

			if selected_text:
				self.add_filter_dialog(initial_text=selected_text)

		except Exception as e:
			print(f"Double click error: {e}")

	# --- 虛擬捲動與 UI 邏輯 (含高亮還原) ---
	def render_viewport(self):
		self.text_area.config(state=tk.NORMAL)
		self.text_area.delete("1.0", tk.END)
		total = len(self.filtered_cache)
		if total == 0:
			self.text_area.config(state=tk.DISABLED)
			return
		end_index = min(self.view_start_index + self.visible_rows, total)
		lines_to_render = self.filtered_cache[self.view_start_index : end_index]

		full_text = "".join([item[0] for item in lines_to_render])
		self.text_area.insert("1.0", full_text)

		for i, (line, tags, raw_idx) in enumerate(lines_to_render):
			line_idx = i + 1
			# 1. 套用 Filter 顏色
			if tags:
				for tag in tags: self.text_area.tag_add(tag, f"{line_idx}.0", f"{line_idx}.end")

			# 2. [重要] 檢查是否為選取行，是則套用高亮
			if raw_idx == self.selected_raw_index:
				self.text_area.tag_add("current_line", f"{line_idx}.0", f"{line_idx}.end")

		# 確保選取高亮在所有 Filter 顏色之上
		self.text_area.tag_raise("current_line")

		self.text_area.config(state=tk.DISABLED)

	def update_scrollbar_thumb(self):
		total = len(self.filtered_cache)
		if total == 0: self.scrollbar_y.set(0, 1)
		else:
			page_size = self.visible_rows / total
			start = self.view_start_index / total
			end = start + page_size
			self.scrollbar_y.set(start, end)

	def on_scroll_y(self, *args):
		total = len(self.filtered_cache)
		if total == 0: return
		op = args[0]
		if op == "scroll":
			units = int(args[1])
			what = args[2]
			step = self.visible_rows if what == "pages" else 1
			new_start = self.view_start_index + (units * step)
		elif op == "moveto":
			fraction = float(args[1])
			new_start = int(total * fraction)
		new_start = max(0, min(new_start, total - self.visible_rows))
		if new_start != self.view_start_index:
			self.view_start_index = int(new_start)
			self.render_viewport()
			self.update_scrollbar_thumb()

	def on_mousewheel(self, event):
		total = len(self.filtered_cache)
		if total == 0: return
		scroll_dir = 0
		if event.num == 5 or event.delta < 0: scroll_dir = 1
		elif event.num == 4 or event.delta > 0: scroll_dir = -1
		step = 3
		new_start = self.view_start_index + (scroll_dir * step)
		new_start = max(0, min(new_start, total - self.visible_rows))
		if new_start != self.view_start_index:
			self.view_start_index = int(new_start)
			self.render_viewport()
			self.update_scrollbar_thumb()
		return "break"

	def on_zoom(self, event):
		delta = 0
		if event.num == 5 or event.delta < 0: delta = -1
		elif event.num == 4 or event.delta > 0: delta = 1
		if delta != 0:
			new_size = self.font_size + delta
			new_size = max(6, min(new_size, 50))
			if new_size != self.font_size:
				self.font_size = new_size
				self.text_area.configure(font=("Consolas", self.font_size))
		return "break"

	# --- Filter 列表與編輯 ---
	def refresh_filter_list(self):
		for item in self.tree.get_children(): self.tree.delete(item)
		for idx, flt in enumerate(self.filters):
			en_str = "[X]" if flt.enabled else "[ ]"
			type_str = "Excl" if flt.is_exclude else ("Regex" if flt.is_regex else "Text")
			item_id = self.tree.insert("", "end", values=(en_str, type_str, flt.text, str(flt.hit_count)))
			tag_name = f"row_{idx}"
			self.tree.item(item_id, tags=(tag_name,))
			self.tree.tag_configure(tag_name, foreground=flt.fore_color, background=flt.back_color)

	def on_filter_toggle(self, event):
		selected_item = self.tree.selection()
		if not selected_item: return
		for item_id in selected_item:
			idx = self.tree.index(item_id)
			self.filters[idx].enabled = not self.filters[idx].enabled
		self.refresh_filter_list(); self.recalc_filtered_data()

	def on_filter_delete(self, event):
		selected_items = self.tree.selection()
		if not selected_items: return
		indices_to_delete = sorted([self.tree.index(item) for item in selected_items], reverse=True)
		for idx in indices_to_delete: del self.filters[idx]
		self.refresh_filter_list(); self.recalc_filtered_data()

	def on_filter_double_click(self, event):
		item_id = self.tree.identify_row(event.y)
		if not item_id: return
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
			else:
				new_filter = Filter(text, colors["fg"], colors["bg"], enabled=True, is_regex=var_regex.get(), is_exclude=var_exclude.get())
				self.filters.append(new_filter)
			dialog.destroy(); self.recalc_filtered_data()
		tk.Button(dialog, text="Save", command=save, width=15).grid(row=3, column=0, columnspan=3, pady=10)

	# --- 檔案 I/O (TAT/JSON) ---
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
		except Exception as e: messagebox.showerror("寫入失敗", str(e)); return False

	def quick_save_tat(self):
		if self.current_tat_path:
			if self._write_tat_file(self.current_tat_path): messagebox.showinfo("儲存", "儲存成功")
		else: self.save_as_tat_filters()

	def save_as_tat_filters(self):
		init_dir = self.config.get("last_filter_dir", ".")
		filepath = filedialog.asksaveasfilename(initialdir=init_dir, defaultextension=".tat", filetypes=[("TextAnalysisTool", "*.tat"), ("XML", "*.xml")])
		if not filepath: return
		self.config["last_filter_dir"] = os.path.dirname(filepath); self.save_config()
		if self._write_tat_file(filepath):
			self.current_tat_path = filepath; self.update_title()
			messagebox.showinfo("成功", "已另存新檔")

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
			self.recalc_filtered_data()
			messagebox.showinfo("成功", f"已匯入 {len(new_filters)} 個 Filters")
		except Exception as e: messagebox.showerror("匯入失敗", str(e))

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
			self.recalc_filtered_data()
		except Exception as e: messagebox.showerror("錯誤", f"JSON 匯入失敗: {e}")

if __name__ == "__main__":
	root = tk.Tk()
	app = LogAnalyzerApp(root)
	root.mainloop()