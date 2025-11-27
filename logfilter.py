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
		self.filtered_cache = []

		self.current_log_path = None
		self.current_tat_path = None

		self.update_title()

		self.view_start_index = 0
		self.visible_rows = 50
		self.font_size = 10

		# --- 介面佈局 ---

		# 1. 頂部工具列
		toolbar = tk.Frame(root, bd=1, relief=tk.RAISED)
		toolbar.pack(side=tk.TOP, fill=tk.X)

		tk.Button(toolbar, text="開啟 Log", command=self.load_log).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Frame(toolbar, width=10).pack(side=tk.LEFT)
		tk.Button(toolbar, text="新增 Filter", command=self.add_filter_dialog).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Frame(toolbar, width=10).pack(side=tk.LEFT)
		tk.Button(toolbar, text="匯入 TAT", command=self.import_tat_filters).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Button(toolbar, text="儲存 TAT", command=self.quick_save_tat).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Button(toolbar, text="另存 TAT", command=self.save_as_tat_filters).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Button(toolbar, text="JSON 匯出", command=self.export_filters).pack(side=tk.RIGHT, padx=2, pady=2)
		tk.Button(toolbar, text="JSON 匯入", command=self.import_json_filters).pack(side=tk.RIGHT, padx=2, pady=2)

		# 2. 底部狀態列
		self.status_bar = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
		self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

		# 3. 中間可調整區域 (PanedWindow)
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

		self.text_area.bind("<MouseWheel>", self.on_mousewheel)
		self.text_area.bind("<Button-4>", self.on_mousewheel)
		self.text_area.bind("<Button-5>", self.on_mousewheel)
		self.text_area.bind("<Control-MouseWheel>", self.on_zoom)
		self.text_area.bind("<Control-Button-4>", self.on_zoom)
		self.text_area.bind("<Control-Button-5>", self.on_zoom)

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

	# --- 設定檔管理 (新功能) ---
	def load_config(self):
		if os.path.exists(self.config_file):
			try:
				with open(self.config_file, 'r') as f:
					return json.load(f)
			except:
				pass
		return {}

	def save_config(self):
		try:
			with open(self.config_file, 'w') as f:
				json.dump(self.config, f)
		except:
			pass

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
		# 讀取上次的路徑
		init_dir = self.config.get("last_log_dir", ".")

		filepath = filedialog.askopenfilename(
			initialdir=init_dir,
			filetypes=[("Log Files", "*.log *.txt"), ("All Files", "*.*")]
		)
		if not filepath: return

		# 儲存本次的路徑
		self.config["last_log_dir"] = os.path.dirname(filepath)
		self.save_config()

		self.update_status(f"正在讀取檔案: {filepath} ...")
		try:
			with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
				self.raw_lines = f.readlines()

			self.current_log_path = filepath
			self.update_title()

			self.update_status(f"讀取完成，共 {len(self.raw_lines)} 行。正在建立索引...")
			self.recalc_filtered_data()

		except Exception as e:
			messagebox.showerror("讀取錯誤", str(e))
			self.update_status("讀取失敗")

	# --- 核心過濾與顯示邏輯 ---
	def recalc_filtered_data(self):
		self.update_status("正在套用過濾器...")

		for f in self.filters:
			f.hit_count = 0

		self.text_area.config(state=tk.NORMAL)
		self.text_area.delete("1.0", tk.END)
		for i, flt in enumerate(self.filters):
			tag_name = f"filter_{i}"
			self.text_area.tag_config(tag_name, foreground=flt.fore_color, background=flt.back_color)

		self.filtered_cache = []

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

		for line in self.raw_lines:
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
			if skip: continue

			matched_tags = []
			is_match = False

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

			if is_match:
				self.filtered_cache.append((line, matched_tags))

		self.refresh_filter_list()
		self.view_start_index = 0
		self.render_viewport()
		self.update_scrollbar_thumb()
		self.update_status(f"顯示 {len(self.filtered_cache)} 行 (原始 {len(self.raw_lines)} 行)")

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

		for i, (line, tags) in enumerate(lines_to_render):
			if tags:
				line_idx = i + 1
				for tag in tags:
					self.text_area.tag_add(tag, f"{line_idx}.0", f"{line_idx}.end")
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
		for item in self.tree.get_children():
			self.tree.delete(item)

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
		self.refresh_filter_list()
		self.recalc_filtered_data()

	def on_filter_delete(self, event):
		selected_items = self.tree.selection()
		if not selected_items: return
		indices_to_delete = sorted([self.tree.index(item) for item in selected_items], reverse=True)
		for idx in indices_to_delete:
			del self.filters[idx]
		self.refresh_filter_list()
		self.recalc_filtered_data()

	def on_filter_double_click(self, event):
		item_id = self.tree.identify_row(event.y)
		if not item_id: return
		idx = self.tree.index(item_id)
		self.open_filter_dialog(self.filters[idx], idx)

	def add_filter_dialog(self):
		self.open_filter_dialog(None)

	def open_filter_dialog(self, filter_obj=None, index=None):
		dialog = tk.Toplevel(self.root)
		dialog.title("Edit Filter" if filter_obj else "Add Filter")

		tk.Label(dialog, text="Pattern:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
		entry_text = tk.Entry(dialog, width=40)
		entry_text.grid(row=0, column=1, columnspan=2, padx=5, pady=5)
		if filter_obj: entry_text.insert(0, filter_obj.text)

		var_regex = tk.BooleanVar(value=filter_obj.is_regex if filter_obj else False)
		var_exclude = tk.BooleanVar(value=filter_obj.is_exclude if filter_obj else False)

		tk.Checkbutton(dialog, text="Regex", variable=var_regex).grid(row=1, column=1, sticky="w")
		tk.Checkbutton(dialog, text="Exclude", variable=var_exclude).grid(row=1, column=2, sticky="w")

		colors = {
			"fg": filter_obj.fore_color if filter_obj else "#000000",
			"bg": filter_obj.back_color if filter_obj else "#FFFFFF"
		}

		def pick_fg():
			c = colorchooser.askcolor(color=colors["fg"])[1]
			if c:
				colors["fg"] = c
				btn_fg.config(bg=c)

		def pick_bg():
			c = colorchooser.askcolor(color=colors["bg"])[1]
			if c:
				colors["bg"] = c
				btn_bg.config(bg=c)

		btn_fg = tk.Button(dialog, text="Text Color", bg=colors["fg"], command=pick_fg)
		btn_fg.grid(row=2, column=1, sticky="ew", padx=2)
		btn_bg = tk.Button(dialog, text="Back Color", bg=colors["bg"], command=pick_bg)
		btn_bg.grid(row=2, column=2, sticky="ew", padx=2)

		def save():
			text = entry_text.get()
			if not text: return

			if filter_obj:
				filter_obj.text = text
				filter_obj.fore_color = colors["fg"]
				filter_obj.back_color = colors["bg"]
				filter_obj.is_regex = var_regex.get()
				filter_obj.is_exclude = var_exclude.get()
			else:
				new_filter = Filter(text, colors["fg"], colors["bg"],
									enabled=True,
									is_regex=var_regex.get(),
									is_exclude=var_exclude.get())
				self.filters.append(new_filter)

			dialog.destroy()
			self.recalc_filtered_data()

		tk.Button(dialog, text="Save", command=save, width=15).grid(row=3, column=0, columnspan=3, pady=10)

	# --- 檔案寫入核心 ---
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
		except Exception as e:
			messagebox.showerror("寫入失敗", str(e)); return False

	def quick_save_tat(self):
		if self.current_tat_path:
			if self._write_tat_file(self.current_tat_path): messagebox.showinfo("儲存", "儲存成功")
		else: self.save_as_tat_filters()

	def save_as_tat_filters(self):
		# 使用 last_filter_dir
		init_dir = self.config.get("last_filter_dir", ".")
		filepath = filedialog.asksaveasfilename(
			initialdir=init_dir,
			defaultextension=".tat",
			filetypes=[("TextAnalysisTool", "*.tat"), ("XML", "*.xml")]
		)
		if not filepath: return

		# 儲存 Filter 目錄
		self.config["last_filter_dir"] = os.path.dirname(filepath)
		self.save_config()

		if self._write_tat_file(filepath):
			self.current_tat_path = filepath; self.update_title()
			messagebox.showinfo("成功", "已另存新檔")

	def import_tat_filters(self):
		# 使用 last_filter_dir
		init_dir = self.config.get("last_filter_dir", ".")
		filepath = filedialog.askopenfilename(
			initialdir=init_dir,
			filetypes=[("TextAnalysisTool", "*.tat"), ("XML", "*.xml")]
		)
		if not filepath: return

		# 儲存 Filter 目錄
		self.config["last_filter_dir"] = os.path.dirname(filepath)
		self.save_config()

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