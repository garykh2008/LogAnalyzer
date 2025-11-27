import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox
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

	def to_dict(self):
		return self.__dict__

class LogAnalyzerApp:
	def __init__(self, root):
		self.root = root
		self.root.geometry("1000x700")

		self.filters = []
		self.raw_lines = []         # 原始資料
		self.filtered_cache = []    # 過濾後的資料 (只存內容與 Tag，不存 Widget)

		# 狀態變數：記錄目前開啟的檔案路徑
		self.current_log_path = None
		self.current_tat_path = None

		# 初始化標題
		self.update_title()

		# 虛擬捲動相關變數
		self.view_start_index = 0   # 目前顯示的第一行在 filtered_cache 中的索引
		self.visible_rows = 50      # 一次渲染多少行 (保持介面流暢)

		# --- 介面佈局 ---
		toolbar = tk.Frame(root, bd=1, relief=tk.RAISED)
		toolbar.pack(side=tk.TOP, fill=tk.X)

		# 按鈕群組
		tk.Button(toolbar, text="開啟 Log", command=self.load_log).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Frame(toolbar, width=10).pack(side=tk.LEFT)
		tk.Button(toolbar, text="新增 Filter", command=self.add_filter_dialog).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Frame(toolbar, width=10).pack(side=tk.LEFT)
		tk.Button(toolbar, text="匯入 TAT", command=self.import_tat_filters).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Button(toolbar, text="儲存 TAT", command=self.quick_save_tat).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Button(toolbar, text="另存 TAT", command=self.save_as_tat_filters).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Button(toolbar, text="JSON 匯出", command=self.export_filters).pack(side=tk.RIGHT, padx=2, pady=2)
		tk.Button(toolbar, text="JSON 匯入", command=self.import_json_filters).pack(side=tk.RIGHT, padx=2, pady=2)

		# 狀態列
		self.status_bar = tk.Label(root, text="Ready", bd=1, relief=tk.SUNKEN, anchor=tk.W)
		self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

		# Log 顯示區與捲動條
		content_frame = tk.Frame(root)
		content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

		self.scrollbar_y = tk.Scrollbar(content_frame, command=self.on_scroll_y)
		self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

		self.text_area = tk.Text(content_frame, wrap="none", font=("Consolas", 10))
		self.scrollbar_x = tk.Scrollbar(root, orient="horizontal", command=self.text_area.xview)
		self.text_area.configure(xscrollcommand=self.scrollbar_x.set)

		self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
		self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

		# 綁定滑鼠滾輪
		self.text_area.bind("<MouseWheel>", self.on_mousewheel)
		self.text_area.bind("<Button-4>", self.on_mousewheel)
		self.text_area.bind("<Button-5>", self.on_mousewheel)

		# Filter 列表區
		filter_frame = tk.LabelFrame(root, text="Active Filters")
		filter_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

		self.filter_list_canvas = tk.Canvas(filter_frame, height=100)
		self.filter_list_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)

		self.filter_container = tk.Frame(self.filter_list_canvas)
		self.filter_list_canvas.create_window((0, 0), window=self.filter_container, anchor="nw")
		self.filter_container.bind("<Configure>", lambda e: self.filter_list_canvas.configure(scrollregion=self.filter_list_canvas.bbox("all")))

	# --- 標題更新邏輯 (新功能) ---
	def update_title(self):
		log_name = os.path.basename(self.current_log_path) if self.current_log_path else "No file load"
		filter_name = os.path.basename(self.current_tat_path) if self.current_tat_path else "No filter file"
		self.root.title(f"[{log_name}] - [{filter_name}] - Log Analyzer")

	def update_status(self, msg):
		self.status_bar.config(text=msg)
		self.root.update_idletasks()

	# --- 檔案讀取 ---

	def load_log(self):
		filepath = filedialog.askopenfilename(filetypes=[("Log Files", "*.log *.txt"), ("All Files", "*.*")])
		if not filepath: return

		self.update_status(f"正在讀取檔案: {filepath} ...")
		try:
			with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
				self.raw_lines = f.readlines()

			# 更新狀態與標題
			self.current_log_path = filepath
			self.update_title()

			self.update_status(f"讀取完成，共 {len(self.raw_lines)} 行。正在建立索引...")
			self.recalc_filtered_data()

		except Exception as e:
			messagebox.showerror("讀取錯誤", str(e))
			self.update_status("讀取失敗")

	# --- 虛擬捲動核心邏輯 ---

	def recalc_filtered_data(self):
		self.update_status("正在套用過濾器...")
		self.text_area.config(state=tk.NORMAL)
		self.text_area.delete("1.0", tk.END)

		for i, flt in enumerate(self.filters):
			tag_name = f"filter_{i}"
			self.text_area.tag_config(tag_name, foreground=flt.fore_color, background=flt.back_color)

		self.filtered_cache = []

		active_filters = [f for f in self.filters if f.enabled and not f.is_exclude]
		exclude_filters = [f for f in self.filters if f.enabled and f.is_exclude]

		compiled_excludes = []
		for f in exclude_filters:
			if f.is_regex:
				try: compiled_excludes.append(re.compile(f.text, re.IGNORECASE))
				except: pass
			else:
				compiled_excludes.append(f.text)

		compiled_includes = []
		for i, flt in enumerate(self.filters):
			if flt.enabled and not flt.is_exclude:
				tag = f"filter_{i}"
				if flt.is_regex:
					try: compiled_includes.append((re.compile(flt.text, re.IGNORECASE), tag, True))
					except: pass
				else:
					compiled_includes.append((flt.text, tag, False))

		for line in self.raw_lines:
			skip = False
			for exc in compiled_excludes:
				if isinstance(exc, str):
					if exc in line:
						skip = True; break
				else:
					if exc.search(line):
						skip = True; break
			if skip: continue

			matched_tags = []
			is_match = False

			if not active_filters:
				is_match = True
			else:
				for rule, tag, is_re in compiled_includes:
					if is_re:
						if rule.search(line):
							is_match = True
							matched_tags.append(tag)
					else:
						if rule in line:
							is_match = True
							matched_tags.append(tag)

			if is_match:
				self.filtered_cache.append((line, matched_tags))

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
		if total == 0:
			self.scrollbar_y.set(0, 1)
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
			if what == "pages":
				step = self.visible_rows
			else:
				step = 1
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
		if event.num == 5 or event.delta < 0:
			scroll_dir = 1
		elif event.num == 4 or event.delta > 0:
			scroll_dir = -1

		step = 3
		new_start = self.view_start_index + (scroll_dir * step)
		new_start = max(0, min(new_start, total - self.visible_rows))

		if new_start != self.view_start_index:
			self.view_start_index = int(new_start)
			self.render_viewport()
			self.update_scrollbar_thumb()
		return "break"

	# --- Filter 操作 ---

	def add_filter_dialog(self):
		dialog = tk.Toplevel(self.root)
		dialog.title("Add Filter")
		tk.Label(dialog, text="關鍵字:").grid(row=0, column=0)
		entry_text = tk.Entry(dialog)
		entry_text.grid(row=0, column=1)

		colors = {"fg": "#000000", "bg": "#FFFFFF"}

		def pick_fg():
			c = colorchooser.askcolor()[1]
			if c: colors["fg"] = c; btn_fg.config(bg=c)
		def pick_bg():
			c = colorchooser.askcolor()[1]
			if c: colors["bg"] = c; btn_bg.config(bg=c)

		btn_fg = tk.Button(dialog, text="文字", bg=colors["fg"], command=pick_fg)
		btn_fg.grid(row=1, column=0)
		btn_bg = tk.Button(dialog, text="背景", bg=colors["bg"], command=pick_bg)
		btn_bg.grid(row=1, column=1)

		def save():
			if entry_text.get():
				new_filter = Filter(entry_text.get(), colors["fg"], colors["bg"])
				self.filters.append(new_filter)
				self.refresh_filter_list()
				self.recalc_filtered_data()
				dialog.destroy()

		tk.Button(dialog, text="確定", command=save).grid(row=2, column=0, columnspan=2)

	def refresh_filter_list(self):
		for widget in self.filter_container.winfo_children():
			widget.destroy()

		for idx, flt in enumerate(self.filters):
			var = tk.BooleanVar(value=flt.enabled)
			def toggle_handler(idx=idx, var=var):
				self.filters[idx].enabled = var.get()
				self.recalc_filtered_data()

			text_label = flt.text
			if flt.is_exclude: text_label = f"[Ex] {text_label}"

			chk = tk.Checkbutton(self.filter_container, text=text_label, variable=var, command=toggle_handler,
								 bg=flt.back_color, fg=flt.fore_color, selectcolor=flt.back_color)
			chk.pack(side=tk.LEFT, padx=5)

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
		filepath = filedialog.asksaveasfilename(defaultextension=".tat", filetypes=[("TextAnalysisTool", "*.tat"), ("XML", "*.xml")])
		if not filepath: return
		if self._write_tat_file(filepath):
			self.current_tat_path = filepath
			self.update_title() # 更新標題
			messagebox.showinfo("成功", "已另存新檔")

	def import_tat_filters(self):
		filepath = filedialog.askopenfilename(filetypes=[("TextAnalysisTool", "*.tat"), ("XML", "*.xml")])
		if not filepath: return
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

			self.current_tat_path = filepath
			self.update_title() # 更新標題

			self.refresh_filter_list()
			self.recalc_filtered_data()
			messagebox.showinfo("成功", f"已匯入 {len(new_filters)} 個 Filters")
		except Exception as e: messagebox.showerror("匯入失敗", str(e))

	def export_filters(self):
		filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
		if not filepath: return
		data = [f.to_dict() for f in self.filters]
		with open(filepath, 'w') as f: json.dump(data, f, indent=4)

	def import_json_filters(self):
		filepath = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
		if not filepath: return
		try:
			with open(filepath, 'r') as f:
				data = json.load(f)
				self.filters = [Filter(**item) for item in data]
			self.refresh_filter_list()
			self.recalc_filtered_data()
		except Exception as e: messagebox.showerror("錯誤", f"JSON 匯入失敗: {e}")

if __name__ == "__main__":
	root = tk.Tk()
	app = LogAnalyzerApp(root)
	root.mainloop()