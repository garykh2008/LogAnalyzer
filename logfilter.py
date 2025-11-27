import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox
import re
import json
import xml.etree.ElementTree as ET
import os # 用來顯示檔名在視窗標題

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
		self.root.title("My Log Analyzer")
		self.root.geometry("1000x700")

		self.filters = []
		self.raw_lines = []

		# [新增] 用來記錄目前編輯的 TAT 檔案路徑
		self.current_tat_path = None

		# --- 介面佈局 ---
		toolbar = tk.Frame(root, bd=1, relief=tk.RAISED)
		toolbar.pack(side=tk.TOP, fill=tk.X)

		# Log 操作
		tk.Button(toolbar, text="開啟 Log", command=self.load_log).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Frame(toolbar, width=10).pack(side=tk.LEFT) # 分隔線

		# Filter 操作
		tk.Button(toolbar, text="新增 Filter", command=self.add_filter_dialog).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Frame(toolbar, width=10).pack(side=tk.LEFT) # 分隔線

		# 檔案操作 (TAT)
		tk.Button(toolbar, text="匯入 TAT", command=self.import_tat_filters).pack(side=tk.LEFT, padx=2, pady=2)
		tk.Button(toolbar, text="儲存 TAT", command=self.quick_save_tat).pack(side=tk.LEFT, padx=2, pady=2) # [新增] 直接儲存
		tk.Button(toolbar, text="另存 TAT", command=self.save_as_tat_filters).pack(side=tk.LEFT, padx=2, pady=2) # 原本的匯出

		# JSON 操作 (放到右邊一點)
		tk.Button(toolbar, text="JSON 匯出", command=self.export_filters).pack(side=tk.RIGHT, padx=2, pady=2)
		tk.Button(toolbar, text="JSON 匯入", command=self.import_json_filters).pack(side=tk.RIGHT, padx=2, pady=2)

		self.text_area = tk.Text(root, wrap="none", font=("Consolas", 10))
		self.scrollbar_y = tk.Scrollbar(root, command=self.text_area.yview)
		self.scrollbar_x = tk.Scrollbar(root, orient="horizontal", command=self.text_area.xview)

		self.text_area.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)

		self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
		self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
		self.text_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

		filter_frame = tk.LabelFrame(root, text="Active Filters")
		filter_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

		self.filter_list_canvas = tk.Canvas(filter_frame, height=100)
		self.filter_list_canvas.pack(side=tk.LEFT, fill=tk.X, expand=True)

		self.filter_container = tk.Frame(self.filter_list_canvas)
		self.filter_list_canvas.create_window((0, 0), window=self.filter_container, anchor="nw")
		self.filter_container.bind("<Configure>", lambda e: self.filter_list_canvas.configure(scrollregion=self.filter_list_canvas.bbox("all")))

	# --- 輔助：更新視窗標題 ---
	def update_title(self):
		if self.current_tat_path:
			filename = os.path.basename(self.current_tat_path)
			self.root.title(f"My Log Analyzer - {filename}")
		else:
			self.root.title("My Log Analyzer - 未儲存")

	# --- 核心邏輯 ---

	def load_log(self):
		filepath = filedialog.askopenfilename(filetypes=[("Log Files", "*.log *.txt"), ("All Files", "*.*")])
		if not filepath: return
		with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
			self.raw_lines = f.readlines()
		self.refresh_view()

	def add_filter_dialog(self):
		dialog = tk.Toplevel(self.root)
		dialog.title("Add Filter")
		tk.Label(dialog, text="關鍵字:").grid(row=0, column=0)
		entry_text = tk.Entry(dialog)
		entry_text.grid(row=0, column=1)

		colors = {"fg": "#000000", "bg": "#FFFFFF"}

		def pick_fg():
			c = colorchooser.askcolor()[1]
			if c:
				colors["fg"] = c
				btn_fg.config(bg=c)

		def pick_bg():
			c = colorchooser.askcolor()[1]
			if c:
				colors["bg"] = c
				btn_bg.config(bg=c)

		btn_fg = tk.Button(dialog, text="文字顏色", bg=colors["fg"], command=pick_fg)
		btn_fg.grid(row=1, column=0)
		btn_bg = tk.Button(dialog, text="背景顏色", bg=colors["bg"], command=pick_bg)
		btn_bg.grid(row=1, column=1)

		def save():
			if entry_text.get():
				new_filter = Filter(entry_text.get(), colors["fg"], colors["bg"])
				self.filters.append(new_filter)
				self.refresh_filter_list()
				self.refresh_view()
				dialog.destroy()

		tk.Button(dialog, text="確定", command=save).grid(row=2, column=0, columnspan=2)

	def refresh_filter_list(self):
		for widget in self.filter_container.winfo_children():
			widget.destroy()

		for idx, flt in enumerate(self.filters):
			var = tk.BooleanVar(value=flt.enabled)
			def toggle_handler(idx=idx, var=var):
				self.filters[idx].enabled = var.get()
				self.refresh_view()

			text_label = flt.text
			if flt.is_exclude: text_label = f"[Ex] {text_label}"

			chk = tk.Checkbutton(self.filter_container, text=text_label, variable=var, command=toggle_handler,
								 bg=flt.back_color, fg=flt.fore_color, selectcolor=flt.back_color)
			chk.pack(side=tk.LEFT, padx=5)

	def refresh_view(self):
		self.text_area.config(state=tk.NORMAL)
		self.text_area.delete(1.0, tk.END)
		for i, flt in enumerate(self.filters):
			tag_name = f"filter_{i}"
			self.text_area.tag_config(tag_name, foreground=flt.fore_color, background=flt.back_color)

		active_filters = [f for f in self.filters if f.enabled and not f.is_exclude]
		exclude_filters = [f for f in self.filters if f.enabled and f.is_exclude]

		for line in self.raw_lines:
			skip_line = False
			for ef in exclude_filters:
				if ef.text in line:
					skip_line = True
					break
			if skip_line: continue

			matched_tags = []
			is_match = False
			if not active_filters:
				is_match = True
			else:
				for i, flt in enumerate(self.filters):
					if not flt.enabled or flt.is_exclude: continue
					if flt.text in line:
						is_match = True
						matched_tags.append(f"filter_{i}")

			if is_match:
				self.text_area.insert(tk.END, line)
				if matched_tags:
					line_idx = self.text_area.index("end-2c").split('.')[0]
					for tag in matched_tags:
						self.text_area.tag_add(tag, f"{line_idx}.0", f"{line_idx}.end")
		self.text_area.config(state=tk.DISABLED)

	# --- 檔案寫入核心 (共用邏輯) ---
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

				if flt.fore_color != "#000000":
					f_node.set("foreColor", color_to_tat(flt.fore_color))
				if flt.back_color != "#FFFFFF":
					f_node.set("backColor", color_to_tat(flt.back_color))
				f_node.set("description", "")

			tree = ET.ElementTree(root)
			tree.write(filepath, encoding="utf-8", xml_declaration=True)
			return True
		except Exception as e:
			messagebox.showerror("寫入失敗", str(e))
			return False

	# --- 儲存與另存新檔 ---

	def quick_save_tat(self):
		# 如果已經有路徑，直接儲存
		if self.current_tat_path:
			if self._write_tat_file(self.current_tat_path):
				# 為了不打擾使用者，直接儲存通常不跳視窗，或只在標題列提示
				# 但這裡為了確認，我們在 Console 印出就好
				print(f"Saved to {self.current_tat_path}")
				messagebox.showinfo("儲存", "儲存成功")
		else:
			# 如果沒有路徑，就轉去執行「另存新檔」
			self.save_as_tat_filters()

	def save_as_tat_filters(self):
		filepath = filedialog.asksaveasfilename(defaultextension=".tat", filetypes=[("TextAnalysisTool", "*.tat"), ("XML", "*.xml")])
		if not filepath: return

		if self._write_tat_file(filepath):
			self.current_tat_path = filepath # 更新目前路徑
			self.update_title()
			messagebox.showinfo("成功", "已另存新檔")

	# --- 匯入 TAT ---
	def import_tat_filters(self):
		filepath = filedialog.askopenfilename(filetypes=[("TextAnalysisTool", "*.tat"), ("XML", "*.xml")])
		if not filepath: return

		try:
			tree = ET.parse(filepath)
			root = tree.getroot()
			filters_node = root.findall('.//filter')

			new_filters = []
			for f in filters_node:
				enabled = is_true(f.get('enabled'))
				text = f.get('text')
				fore = fix_color(f.get('foreColor'), "#000000")
				back = fix_color(f.get('backColor'), "#FFFFFF")
				is_exclude = is_true(f.get('excluding'))
				is_regex = is_true(f.get('regex'))
				if text:
					new_filters.append(Filter(text, fore, back, enabled, is_regex, is_exclude))

			# 匯入成功才更新狀態
			self.filters = new_filters
			self.current_tat_path = filepath # 記錄路徑
			self.update_title()

			self.refresh_filter_list()
			self.refresh_view()
			messagebox.showinfo("成功", f"已匯入 {len(new_filters)} 個 Filters")

		except Exception as e:
			messagebox.showerror("匯入失敗", str(e))

	# --- JSON 匯入匯出 (維持原樣) ---
	def export_filters(self):
		filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
		if not filepath: return
		data = [f.to_dict() for f in self.filters]
		with open(filepath, 'w') as f:
			json.dump(data, f, indent=4)

	def import_json_filters(self):
		filepath = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
		if not filepath: return
		try:
			with open(filepath, 'r') as f:
				data = json.load(f)
				self.filters = [Filter(**item) for item in data]
			self.refresh_filter_list()
			self.refresh_view()
		except Exception as e:
			messagebox.showerror("錯誤", f"JSON 匯入失敗: {e}")

if __name__ == "__main__":
	root = tk.Tk()
	app = LogAnalyzerApp(root)
	root.mainloop()