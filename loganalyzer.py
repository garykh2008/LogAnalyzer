import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox, ttk
from tkinterdnd2 import DND_FILES, TkinterDnD
import tkinter.font as tkFont
import re
import json
import xml.etree.ElementTree as ET
import os
import time
import threading
import queue
import webbrowser
import sys

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
		self.root.geometry("1000x750")

		# --- UI Theme ---
		style = ttk.Style(self.root)
		style.theme_use("clam")
		style.configure("Treeview", rowheight=25, font=("Segoe UI", 9))
		style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
		style.map("Treeview", background=[("selected", "#0078D7")])
		style.configure("TLabelFrame", padding=5)
		style.configure("TLabelFrame.Label", font=("Segoe UI", 10, "bold"))
		style.configure("TButton", padding=5, font=("Segoe UI", 9))
		style.configure("TProgressbar", thickness=15)

		# App Info
		self.APP_NAME = "Log Analyzer"
		self.VERSION = "V1.3"

		# Threading & Queue
		self.msg_queue = queue.Queue()
		self.is_processing = False

		# Config
		self.config_file = "app_config.json"
		self.config = self.load_config()

		self.filters = []
		self.raw_lines = []

		# Cache structure: [(line_content, tags, raw_index), ...]
		# If None, it means "Raw Mode"
		self.filtered_cache = None

		# Store result of regex scan for ALL lines
		self.all_line_tags = []

		# Pre-computed indices for filtered view [idx1, idx2, ...]
		self.filtered_indices = []

		# Filter Match Cache: { filter_index: [raw_idx1, raw_idx2, ...] }
		self.filter_matches = {}

		self.current_log_path = None
		self.current_tat_path = None

		# Notes System
		self.notes = {}  # { raw_index (int): note_text (str) }
		self.notes_window = None

		self.view_start_index = 0
		self.visible_rows = 50

		# Font management
		self.font_size = self.config.get("font_size", 11)
		self.font_object = tkFont.Font(family="Segoe UI", size=self.font_size)

		self.selected_raw_index = -1
		self.selection_offset = 0

		self.note_view_visible_var = tk.BooleanVar(value=False)
		note_view_mode = self.config.get("note_view_mode", "docked")
		self.show_notes_in_window_var = tk.BooleanVar(value=(note_view_mode == "window"))
		self.show_only_filtered_var = tk.BooleanVar(value=False)

		# Duration strings
		self.load_duration_str = "0.000s"
		self.filter_duration_str = "0.000s"

		self.drag_start_index = None

		# --- UI Layout ---

		# 1. Menu Bar
		self.menubar = tk.Menu(root)
		root.config(menu=self.menubar)

		# [File Menu]
		self.file_menu = tk.Menu(self.menubar, tearoff=0)
		self.menubar.add_cascade(label="File", menu=self.file_menu)

		self.file_menu.add_command(label="Open Log", command=self.load_log)
		self.file_menu.add_separator()
		self.file_menu.add_command(label="Load Filters", command=self.import_tat_filters)
		self.file_menu.add_command(label="Save Filters", command=self.quick_save_tat)
		self.file_menu.add_command(label="Save Filters As", command=self.save_as_tat_filters)

		# JSON Features (Hidden)
		# self.file_menu.add_separator()
		# self.file_menu.add_command(label="Import JSON", command=self.import_json_filters)
		# self.file_menu.add_command(label="Export JSON", command=self.export_filters)

		self.file_menu.add_separator()
		self.file_menu.add_command(label="Exit", command=root.quit)

		# [Filter Menu]
		self.filter_menu = tk.Menu(self.menubar, tearoff=0)
		self.menubar.add_cascade(label="Filter", menu=self.filter_menu)

		self.filter_menu.add_command(label="Add Filter", command=self.add_filter_dialog)
		self.filter_menu.add_checkbutton(label="Show Filtered Only", onvalue=True, offvalue=False,
										 variable=self.show_only_filtered_var,
										 command=self.toggle_show_filtered,
										 accelerator="Ctrl+H")

		# [Notes Menu]
		self.notes_menu = tk.Menu(self.menubar, tearoff=0)
		self.menubar.add_cascade(label="Notes", menu=self.notes_menu)
		self.notes_menu.add_checkbutton(label="Show Notes", onvalue=True, offvalue=False,
										variable=self.note_view_visible_var,
										command=self.toggle_note_view_visibility)
		self.notes_menu.add_checkbutton(label="Show in Separate Window", onvalue=True, offvalue=False,
										variable=self.show_notes_in_window_var,
										command=self.toggle_note_view_mode)
		self.notes_menu.add_separator()
		self.notes_menu.add_command(label="Save Notes to Text file", command=self.save_notes_to_text)

		# [Help Menu]
		self.help_menu = tk.Menu(self.menubar, tearoff=0)
		self.menubar.add_cascade(label="Help", menu=self.help_menu)
		self.help_menu.add_command(label="Keyboard Shortcuts", command=self.show_keyboard_shortcuts)
		self.help_menu.add_command(label="Documentation", command=self.open_documentation)
		self.help_menu.add_separator()
		self.help_menu.add_command(label="About", command=self.show_about)

		# 2. Status Bar & Progress Bar Area
		status_frame = ttk.Frame(root, relief=tk.SUNKEN)
		status_frame.pack(side=tk.BOTTOM, fill=tk.X)

		self.progress_bar = ttk.Progressbar(status_frame, orient="horizontal", mode="determinate", length=200)
		self.progress_bar.pack(side=tk.RIGHT, padx=5, pady=5)

		self.status_label = ttk.Label(status_frame, text="Ready", anchor=tk.W)
		self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

		# Update initial title and status
		self.update_title()
		self.update_status("Ready")

		# 3. Main Content Area (PanedWindow)
		self.paned_window = tk.PanedWindow(root, orient=tk.VERTICAL, sashwidth=6, sashrelief=tk.RAISED, bg="#d9d9d9")
		self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

		# --- Upper: Log View ---
		# --- Upper Pane: Contains both Log View and Note View ---
		top_pane = tk.PanedWindow(self.paned_window, orient=tk.HORIZONTAL, sashwidth=6, sashrelief=tk.RAISED, bg="#d9d9d9")

		# --- Upper-Left: Log View ---
		self.content_frame = ttk.Frame(top_pane)

		self.scrollbar_y = ttk.Scrollbar(self.content_frame, command=self.on_scroll_y)
		self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

		self.line_number_area = tk.Text(self.content_frame, width=7, wrap="none", font=self.font_object,
										state="disabled", bg="#f0f0f0", bd=0, highlightthickness=0, takefocus=0)
		self.line_number_area.pack(side=tk.LEFT, fill=tk.Y)
		self.line_number_area.tag_configure("right_align", justify="right")

		self.text_area = tk.Text(self.content_frame, wrap="none", font=self.font_object)
		self.scrollbar_x = ttk.Scrollbar(self.content_frame, orient="horizontal", command=self.text_area.xview)
		self.text_area.configure(xscrollcommand=self.scrollbar_x.set)

		self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
		self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

		# Configure default selection tag immediately
		self.text_area.tag_config("current_line", background="#0078D7", foreground="#FFFFFF")

		# Bindings
		self.text_area.bind("<MouseWheel>", self.on_mousewheel)
		self.text_area.bind("<Button-4>", self.on_mousewheel)
		self.text_area.bind("<Button-5>", self.on_mousewheel)
		self.text_area.bind("<Control-MouseWheel>", self.on_zoom)
		self.text_area.bind("<Control-Button-4>", self.on_zoom)
		self.text_area.bind("<Control-Button-5>", self.on_zoom)

		self.text_area.bind("<Double-Button-1>", self.on_log_double_click)
		self.text_area.bind("<Button-1>", self.on_log_single_click)
		self.text_area.bind("<Button-3>", self.on_log_right_click)
		self.text_area.bind("c", self.on_key_c_pressed)

		self.line_number_area.bind("<MouseWheel>", self.on_mousewheel)
		self.line_number_area.bind("<Button-4>", self.on_mousewheel)
		self.line_number_area.bind("<Button-5>", self.on_mousewheel)
		self.line_number_area.bind("<Control-MouseWheel>", self.on_zoom)
		self.text_area.bind("<Configure>", self.update_visible_rows)

		self.root.bind("<Control-h>", self.toggle_show_filtered)
		self.root.bind("<Control-H>", self.toggle_show_filtered)

		self.root.bind("<Control-Left>", self.on_nav_prev_match)
		self.root.bind("<Control-Right>", self.on_nav_next_match)

		top_pane.add(self.content_frame, width=750, minsize=300)

		# --- Upper-Right: Note View (Placeholder) ---
		# The actual notes_frame will be created dynamically
		self.notes_frame = None
		self.top_pane = top_pane

		# Initial setup: Hide the notes view by default
		self.toggle_note_view_visibility(initial_setup=True)

		self.paned_window.add(top_pane, height=450, minsize=100)

		# Context Menu for Notes Tree
		self.notes_context_menu = tk.Menu(self.root, tearoff=0)
		self.notes_context_menu.add_command(label="Edit Note", command=self.edit_note_from_tree)
		self.notes_context_menu.add_command(label="Remove Note", command=self.remove_note_from_tree)

		# Log Context Menu
		self.log_context_menu = tk.Menu(self.root, tearoff=0)
		self.log_context_menu.add_command(label="Add/Edit Note", command=self.add_note_dialog)
		self.log_context_menu.add_command(label="Remove Note", command=self.remove_note)

		# --- Lower: Filter View ---
		filter_frame = ttk.LabelFrame(self.paned_window, text="Filters (Drag to Reorder)")

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

		tree_scroll = ttk.Scrollbar(filter_frame, orient="vertical", command=self.tree.yview)
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

		# Start Queue Checker
		self.check_queue()

		# --- Drag and Drop ---
		self.root.drop_target_register(DND_FILES)
		self.root.dnd_bind('<<Drop>>', self.on_drop)

	def _create_notes_view_widgets(self, parent_frame):
		"""Helper to create all widgets for the notes view inside a given parent."""
		# Button Frame
		btn_frame = ttk.Frame(parent_frame, padding=5)
		btn_frame.pack(side=tk.BOTTOM, fill=tk.X)
		ttk.Button(btn_frame, text="Export Notes", command=self.export_notes).pack(side=tk.RIGHT)

		# Treeview Frame
		tree_frame = ttk.Frame(parent_frame)
		tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
		# Treeview for notes
		cols = ("line", "timestamp", "content")
		self.notes_tree = ttk.Treeview(tree_frame, columns=cols, show="headings")
		self.notes_tree.heading("line", text="Line")
		self.notes_tree.column("line", width=60, anchor="center")
		self.notes_tree.heading("timestamp", text="Timestamp")
		self.notes_tree.column("timestamp", width=150, anchor="w")
		self.notes_tree.heading("content", text="Note Content")
		self.notes_tree.column("content", width=350, anchor="w")
		scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.notes_tree.yview)
		self.notes_tree.configure(yscrollcommand=scroll.set)
		scroll.pack(side=tk.RIGHT, fill=tk.Y)
		self.notes_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
		self.notes_tree.bind("<Double-1>", self.on_note_double_click)
		self.notes_tree.bind("<Button-3>", self.on_notes_tree_right_click)

	# --- [Helper] Path Resource Finder ---
	def resource_path(self, relative_path):
		try:
			base_path = sys._MEIPASS
		except Exception:
			base_path = os.path.abspath(".")
		return os.path.join(base_path, relative_path)

	# --- Documentation & About ---
	def open_documentation(self):
		doc_filename = f"Log_Analyzer_{self.VERSION}_Docs_EN.html"
		doc_path = self.resource_path(os.path.join("Doc", doc_filename))

		if not os.path.exists(doc_path):
			# Fallback for development environment
			alt_doc_path = os.path.join(os.path.abspath("."), "Doc", doc_filename)
			if not os.path.exists(alt_doc_path):
				messagebox.showerror("Error", f"Documentation file not found at:\n{doc_path}\n(or {alt_doc_path})\n\nPlease ensure the 'Doc' folder is in the application directory.")
				return
			doc_path = alt_doc_path

		try:
			# os.startfile is preferred on Windows
			os.startfile(doc_path)
		except AttributeError:
			# fallback for non-Windows
			webbrowser.open('file://' + os.path.realpath(doc_path))
		except Exception as e:
			messagebox.showerror("Error", f"Could not open documentation file: {e}")

	def show_about(self):
		msg = f"{self.APP_NAME}\nVersion: {self.VERSION}\n\nA high-performance log analysis tool."
		messagebox.showinfo("About", msg)

	def show_keyboard_shortcuts(self):
		"""Displays a window with a summary of keyboard shortcuts."""
		shortcuts = [
			("General", ""),
			("Ctrl + H", "Toggle between 'Show Filtered Only' and 'Show All'"),
			("Ctrl + Scroll", "Adjust font size in the log view"),
			("Ctrl + Left/Right", "Jump to previous/next match for the selected filter"),
			("", ""),
			("In Log View", ""),
			("Double-Click", "Select text to quickly add a new filter"),
			("'c' key", "Add or edit a note for the selected line"),
			("", ""),
			("In Filter List", ""),
			("Double-Click", "Edit the selected filter"),
			("Spacebar", "Enable or disable the selected filter"),
			("Delete key", "Remove the selected filter(s)"),
		]

		win = tk.Toplevel(self.root)
		win.title("Keyboard Shortcuts")
		win.transient(self.root)
		win.grab_set()
		win.geometry("450x300")

		frame = ttk.Frame(win, padding=15)
		frame.pack(fill=tk.BOTH, expand=True)

		for i, (key, desc) in enumerate(shortcuts):
			if not key and not desc:
				ttk.Separator(frame, orient='horizontal').grid(row=i, columnspan=2, sticky='ew', pady=5)
				continue
			ttk.Label(frame, text=key, font=("Segoe UI", 9, "bold")).grid(row=i, column=0, sticky='w', padx=(0, 10))
			ttk.Label(frame, text=desc).grid(row=i, column=1, sticky='w')

	# --- Status Update ---
	def update_status(self, msg):
		full_text = f"{msg}    |    Load Time: {self.load_duration_str}    |    Filter Time: {self.filter_duration_str}"
		self.status_label.config(text=full_text)

	# --- Tag Configuration ---
	def apply_tag_styles(self):
		for i, flt in enumerate(self.filters):
			tag_name = f"filter_{i}"
			self.text_area.tag_config(tag_name, foreground=flt.fore_color, background=flt.back_color)
		self.text_area.tag_config("current_line", background="#0078D7", foreground="#FFFFFF")
		self.text_area.tag_config("note_line", background="#FFFACD", foreground="#000000")

	# --- Threading Infrastructure ---
	def check_queue(self):
		try:
			while True:
				msg = self.msg_queue.get_nowait()
				msg_type = msg[0]

				if msg_type == 'progress':
					current, total, text = msg[1], msg[2], msg[3]
					self.progress_bar["maximum"] = total
					self.progress_bar["value"] = current
					self.update_status(text)

				elif msg_type == 'load_complete':
					lines, duration, filepath = msg[1], msg[2], msg[3]
					self.raw_lines = lines
					self.load_duration_str = f"{duration:.4f}s"
					self.current_log_path = filepath
					self.update_title()
					self.selected_raw_index = -1
					self.selection_offset = 0
					self.filter_matches = {}
					self.notes = {} # Clear notes
					self.check_and_import_notes() # Auto-import notes
					self.refresh_notes_window()
					self.set_ui_busy(False)
					self.update_status(f"Loaded {len(lines)} lines")
					self.recalc_filtered_data()

				elif msg_type == 'load_error':
					self.set_ui_busy(False)
					messagebox.showerror("Load Error", msg[1])
					self.update_status("Load failed")

				elif msg_type == 'filter_complete':
					line_tags, filtered_idx, duration, counts, matches = msg[1], msg[2], msg[3], msg[4], msg[5]

					# Only update if full recalc or if we need to sync state
					# In partial update, we merge results manually before calling this,
					# or this msg contains the FULL updated state.
					# For simplicity, worker always returns FULL state (even if derived partially)

					self.all_line_tags = line_tags
					self.filtered_indices = filtered_idx
					self.filter_duration_str = f"{duration:.4f}s"

					for i, count in enumerate(counts):
						if i < len(self.filters):
							self.filters[i].hit_count = count

					if matches: self.filter_matches.update(matches)

					self.apply_tag_styles()
					self.refresh_filter_list()
					self.refresh_view_fast()

					self.set_ui_busy(False)
					self.progress_bar["value"] = 0

				elif msg_type == 'status':
					self.update_status(msg[1])

		except queue.Empty:
			pass
		finally:
			self.root.after(100, self.check_queue)

	def set_ui_busy(self, is_busy):
		self.is_processing = is_busy
		state = tk.DISABLED if is_busy else tk.NORMAL
		try:
			self.menubar.entryconfig("File", state=state)
			self.menubar.entryconfig("Filter", state=state)
			self.menubar.entryconfig("Help", state=state)
		except: pass
		self.tree.state(("disabled",) if is_busy else ("!disabled",))
		self.root.config(cursor="watch" if is_busy else "")

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
		self.root.title(f"[{log_name}] - [{filter_name}] - {self.APP_NAME} {self.VERSION}")

	# --- [Data Access Helpers] ---
	def get_total_count(self):
		if self.filtered_cache is not None:
			return len(self.filtered_cache)
		return len(self.raw_lines)

	def get_view_item(self, index):
		if self.filtered_cache is not None:
			if 0 <= index < len(self.filtered_cache):
				return self.filtered_cache[index]
			return ("", [], -1)
		else:
			if 0 <= index < len(self.raw_lines):
				tags = []
				if self.all_line_tags and index < len(self.all_line_tags):
					tag = self.all_line_tags[index]
					if tag and tag != 'EXCLUDED':
						tags = [tag]
				return (self.raw_lines[index], tags, index)
			return ("", [], -1)

	# --- File Loading (Threaded) ---
	def load_log(self):
		if self.is_processing: return
		init_dir = self.config.get("last_log_dir", ".")
		filepath = filedialog.askopenfilename(initialdir=init_dir, filetypes=[("Log Files", "*.log *.txt"), ("All Files", "*.*")])
		if not filepath: return

		self.config["last_log_dir"] = os.path.dirname(filepath); self.save_config()
		self.set_ui_busy(True)
		self.progress_bar["value"] = 0
		t = threading.Thread(target=self._worker_load_log, args=(filepath,))
		t.daemon = True
		t.start()

	def _worker_load_log(self, filepath):
		try:
			t_start = time.time()
			file_size = os.path.getsize(filepath)
			lines = []
			self.msg_queue.put(('progress', 0, 100, f"Loading {os.path.basename(filepath)}..."))
			with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
				if file_size < 10 * 1024 * 1024:
					lines = f.readlines()
				else:
					self.msg_queue.put(('progress', 10, 100, "Reading file into memory... (Please wait)"))
					lines = f.readlines()
			t_end = time.time()
			self.msg_queue.put(('load_complete', lines, t_end - t_start, filepath))
		except Exception as e:
			self.msg_queue.put(('load_error', str(e)))

	def _load_log_from_path(self, filepath):
		if self.is_processing: return
		if not filepath or not os.path.exists(filepath): return

		self.config["last_log_dir"] = os.path.dirname(filepath); self.save_config()
		self.set_ui_busy(True)
		self.progress_bar["value"] = 0
		t = threading.Thread(target=self._worker_load_log, args=(filepath,))
		t.daemon = True
		t.start()

	def on_drop(self, event):
		try:
			# The root.tk.splitlist handles paths with spaces (they are wrapped in {})
			files = self.root.tk.splitlist(event.data)
			if files:
				# We only process the first file dropped
				self._load_log_from_path(files[0])
		except Exception as e:
			messagebox.showerror("Drag & Drop Error", f"Could not open dropped file:\n{e}")

	# --- Filter Logic (Threaded) ---
	def smart_update_filter(self, idx, is_enabling):
		if self.is_processing: return

		# [OPTIMIZATION] Smart Disable
		# If disabling, we only need to re-check lines that were matched by this filter (or excluded by it)
		# If enabling, we must do full recalc (as new filter matches are unknown)

		if not is_enabling and self.all_line_tags:
			self.set_ui_busy(True)
			flt = self.filters[idx]
			target_tag = f"filter_{idx}"
			if flt.is_exclude: target_tag = 'EXCLUDED'

			# Identify rows that need update
			# We scan all_line_tags (fast in memory)
			target_indices = [i for i, tag in enumerate(self.all_line_tags) if tag == target_tag]

			if not target_indices:
				# No lines affected, just update UI
				self.set_ui_busy(False)
				return

			# Launch partial recalc worker
			self.recalc_filtered_data(target_indices=target_indices)
		else:
			self.recalc_filtered_data()

	def recalc_filtered_data(self, target_indices=None):
		if self.is_processing and target_indices is None: return # Allow re-entry if internal call? No, lock UI
		if not self.is_processing: self.set_ui_busy(True)

		filters_snapshot = []
		for f in self.filters:
			filters_snapshot.append({
				'text': f.text,
				'is_regex': f.is_regex,
				'is_exclude': f.is_exclude,
				'enabled': f.enabled
			})

		# Pass current state for partial update
		current_tags = self.all_line_tags if target_indices is not None else None

		t = threading.Thread(target=self._worker_recalc_jit, args=(filters_snapshot, target_indices, current_tags))
		t.daemon = True
		t.start()

	def _worker_recalc_jit(self, filters_data, target_indices=None, current_tags=None):
		t_start = time.time()
		has_active_filters = any(f['enabled'] for f in filters_data)

		if not has_active_filters:
			t_end = time.time()
			# Clear all tags
			empty_tags = [None] * len(self.raw_lines)
			self.msg_queue.put(('filter_complete', empty_tags, [], t_end - t_start, [0]*len(filters_data), {}))
			return

		# Setup regex groups
		txt_excludes = []
		reg_excludes = []
		txt_includes = []
		reg_includes = []

		for idx, f in enumerate(filters_data):
			if not f['enabled']: continue
			if f['is_exclude']:
				if f['is_regex']:
					try: reg_excludes.append((re.compile(f['text'], re.IGNORECASE), idx))
					except: pass
				else: txt_excludes.append((f['text'], idx))
			else:
				tag = f"filter_{idx}"
				if f['is_regex']:
					try: reg_includes.append((re.compile(f['text'], re.IGNORECASE), tag, idx))
					except: pass
				else: txt_includes.append((f['text'], tag, idx))

		# JIT Code Generation
		code_lines = []
		code_lines.append("def fast_filter_worker(raw_lines, line_tags, filter_counts, temp_matches, update_prog, indices_subset):")
		code_lines.append("    total = len(indices_subset) if indices_subset else len(raw_lines)")
		code_lines.append("    report_interval = max(1, total // 20)")
		code_lines.append("    ")
		# If partial, loop over subset. Else loop over all.
		code_lines.append("    iterable = indices_subset if indices_subset is not None else range(len(raw_lines))")
		code_lines.append("    ")
		code_lines.append("    for step, raw_idx in enumerate(iterable):")
		code_lines.append("        if step % report_interval == 0: update_prog(step, total)")
		code_lines.append("        line = raw_lines[raw_idx]")
		code_lines.append("        line_tags[raw_idx] = None") # Reset tag for this line
		code_lines.append("        ")

		# Excludes
		for text, idx in txt_excludes:
			safe_text = repr(text)
			code_lines.append(f"        if {safe_text} in line:")
			code_lines.append(f"            filter_counts[{idx}] += 1")
			code_lines.append(f"            temp_matches[{idx}].append(raw_idx)")
			code_lines.append(f"            line_tags[raw_idx] = 'EXCLUDED'")
			code_lines.append(f"            continue")
		for _, idx in reg_excludes:
			code_lines.append(f"        if reg_ex_{idx}.search(line):")
			code_lines.append(f"            filter_counts[{idx}] += 1")
			code_lines.append(f"            temp_matches[{idx}].append(raw_idx)")
			code_lines.append(f"            line_tags[raw_idx] = 'EXCLUDED'")
			code_lines.append(f"            continue")

		code_lines.append("")

		# Includes
		code_lines.append("        # Include Checks")
		first_include = True
		for text, tag, idx in txt_includes:
			safe_text = repr(text)
			prefix = "if" if first_include else "elif"
			code_lines.append(f"        {prefix} {safe_text} in line:")
			code_lines.append(f"            filter_counts[{idx}] += 1")
			code_lines.append(f"            temp_matches[{idx}].append(raw_idx)")
			code_lines.append(f"            line_tags[raw_idx] = '{tag}'")
			first_include = False
		for _, tag, idx in reg_includes:
			prefix = "if" if first_include else "elif"
			code_lines.append(f"        {prefix} reg_inc_{idx}.search(line):")
			code_lines.append(f"            filter_counts[{idx}] += 1")
			code_lines.append(f"            temp_matches[{idx}].append(raw_idx)")
			code_lines.append(f"            line_tags[raw_idx] = '{tag}'")
			first_include = False

		full_code = "\n".join(code_lines)
		context = {}
		for rule, idx in reg_excludes: context[f"reg_ex_{idx}"] = rule
		for rule, _, idx in reg_includes: context[f"reg_inc_{idx}"] = rule

		try:
			exec(full_code, context)
			worker_func = context['fast_filter_worker']

			# Prepare Data containers
			if target_indices is not None and current_tags is not None:
				# Partial update: Copy existing tags
				line_tags = list(current_tags)
				# Reset hit counts? No, partial update makes hit counts tricky.
				# Simple solution: Recalculate hit counts fully is safer?
				# Actually, for disable, we can just subtract? No, lines might move from filter A to B.
				# To be safe and correct, we need to recalc stats fully OR accept stats might be slightly off until full recalc.
				# Let's start filter_counts at 0, but this only counts hits in the subset.
				# Merging counts is complex.
				# Trade-off: In partial mode, we might see wonky hit counts momentarily,
				# OR we scan all tags afterwards to rebuild counts (Fast O(N)).
				# Let's choose: Scan all tags to rebuild counts.

				# Filter counts and matches need to be rebuilt from the final tags state
				pass
			else:
				# Full update
				line_tags = [None] * len(self.raw_lines)

			# Temp counters for this run
			filter_counts = [0] * len(filters_data)
			temp_matches = {i: [] for i in range(len(filters_data)) if filters_data[i]['enabled']}

			def update_prog_callback(curr, total):
				self.msg_queue.put(('progress', curr, total, f"Filtering line {curr}/{total} (Smart)..."))

			worker_func(self.raw_lines, line_tags, filter_counts, temp_matches, update_prog_callback, target_indices)

			# Post-processing: Rebuild Indices & Stats from final line_tags (Fast O(N))
			final_indices = []
			final_counts = [0] * len(filters_data)
			# We need to map 'filter_X' string back to index X for stats
			# This loop is 10M iterations, might take 1-2s in Python.
			# But it's unavoidable if we want correct stats and view.

			# Optimization: Use indices list for stats gathering if possible.
			# Actually, if we just want the view to be fast, we can skip full stats recalc for now?
			# User expects "Disable" to be fast.

			for i, tag in enumerate(line_tags):
				if tag and tag != 'EXCLUDED':
					final_indices.append(i)
					# Tag format: filter_5
					try:
						f_idx = int(tag.split('_')[1])
						final_counts[f_idx] += 1
					except: pass
				elif tag == 'EXCLUDED':
					# We don't know WHICH exclude filter hit it without storing it.
					# V2.6 didn't store exclude index in tags.
					# So exclude hit counts will be inaccurate in partial mode unless we track them better.
					# Acceptable trade-off for speed.
					pass

			t_end = time.time()
			self.msg_queue.put(('filter_complete', line_tags, final_indices, t_end - t_start, final_counts, {}))

		except Exception as e:
			print(f"JIT Compilation Failed: {e}")
			self.msg_queue.put(('load_error', f"Optimization Error: {e}"))

	# --- View Generation (Instant) ---
	def refresh_view_fast(self):
		show_only = self.show_only_filtered_var.get()

		if show_only:
			if not self.all_line_tags:
				self.filtered_cache = None
			else:
				new_cache = []
				raw = self.raw_lines
				tags = self.all_line_tags

				for r_idx in self.filtered_indices:
					t = tags[r_idx]
					new_cache.append((raw[r_idx], [t] if t else [], r_idx))
				self.filtered_cache = new_cache
		else:
			self.filtered_cache = None

		self.restore_view_position()

		mode_text = "Filtered" if show_only else "Full View"
		count_text = len(self.filtered_cache) if self.filtered_cache else len(self.raw_lines)
		self.update_status(f"[{mode_text}] Showing {count_text} lines (Total {len(self.raw_lines)})")

	def toggle_show_filtered(self, event=None):
		if self.is_processing: return "break"
		current = self.show_only_filtered_var.get()
		self.show_only_filtered_var.set(not current)
		self.refresh_view_fast()
		return "break"

	def restore_view_position(self):
		target_raw_index = -1
		anchor_offset = 0
		if self.selected_raw_index != -1:
			target_raw_index = self.selected_raw_index
			anchor_offset = self.selection_offset

		new_start_index = 0
		new_total = self.get_total_count()

		if target_raw_index >= 0:
			if self.filtered_cache is None: found_idx = target_raw_index
			else:
				found_idx = -1
				if self.filtered_cache is not None:
					try:
						found_idx = self.filtered_indices.index(target_raw_index)
					except ValueError:
						for i, idx in enumerate(self.filtered_indices):
							if idx >= target_raw_index:
								found_idx = i; break

			if found_idx != -1: new_start_index = max(0, found_idx - anchor_offset)
			else: new_start_index = max(0, new_total - self.visible_rows)

		self.view_start_index = new_start_index
		self.render_viewport()
		self.update_scrollbar_thumb()

	# --- Filter Navigation ---
	def get_current_cache_index(self):
		if self.selected_raw_index == -1: return self.view_start_index
		if self.filtered_cache is None: return self.selected_raw_index
		for i, item in enumerate(self.filtered_cache):
			if item[2] == self.selected_raw_index: return i
		return self.view_start_index

	def navigate_to_match(self, direction):
		if self.is_processing: return
		if self.filtered_cache is None:
			self.status_label.config(text="No active filters to navigate")
			return
		selected_items = self.tree.selection()
		if not selected_items:
			self.status_label.config(text="No filter selected for navigation")
			return
		target_tags = set()
		for item_id in selected_items:
			idx = self.tree.index(item_id)
			target_tags.add(f"filter_{idx}")
		if not target_tags: return
		current_idx = self.get_current_cache_index()
		total = len(self.filtered_cache)
		found_idx = -1
		if direction == 1:
			for i in range(current_idx + 1, total):
				line_tags = self.filtered_cache[i][1]
				if any(t in target_tags for t in line_tags): found_idx = i; break
		else:
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
			self.status_label.config(text=f"Jumped to line {self.selected_raw_index + 1}")
		else: self.status_label.config(text="No more matches found in that direction")

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

	# --- Notes System ---
	def on_log_right_click(self, event):
		try:
			# Select the line under cursor
			self.on_log_single_click(event)
			# Enable/Disable menu items based on if note exists
			if self.selected_raw_index in self.notes:
				self.log_context_menu.entryconfig(0, label="Edit Note")
				self.log_context_menu.entryconfig(1, state="normal")
			else:
				self.log_context_menu.entryconfig(0, label="Add Note")
				self.log_context_menu.entryconfig(1, state="disabled")

			self.log_context_menu.post(event.x_root, event.y_root)
		except Exception as e: print(f"Right click error: {e}")

	def on_key_c_pressed(self, event=None):
		# "c" for "comment" or "capture"
		if self.selected_raw_index != -1:
			# Open the add/edit note dialog for the currently selected line
			self.add_note_dialog()
		return "break" # Prevents the key press from propagating

	def add_note_dialog(self, target_index=None):
		idx = target_index if target_index is not None else self.selected_raw_index
		if idx == -1: return

		current_note = self.notes.get(idx, "")

		dialog = tk.Toplevel(self.root)
		dialog.title(f"Note for Line {idx + 1}")
		dialog.transient(self.root)
		dialog.grab_set()
		dialog.geometry("400x200")

		# Buttons (Pack first to ensure visibility at bottom)
		btn_frame = ttk.Frame(dialog, padding=10)
		btn_frame.pack(side=tk.BOTTOM, fill=tk.X)

		def save():
			content = txt_input.get("1.0", tk.END).strip()
			if content:
				self.notes[idx] = content
			else:
				if idx in self.notes:
					del self.notes[idx]

			self.render_viewport() # Refresh to show/hide note style
			self.refresh_notes_window()
			dialog.destroy()

		ttk.Button(btn_frame, text="Save", command=save).pack(side=tk.RIGHT)
		ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

		# Text Area (Takes remaining space)
		text_frame = ttk.Frame(dialog, padding=10)
		text_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

		txt_input = tk.Text(text_frame, wrap="word", font=("Segoe UI", 10), height=5)
		txt_input.pack(fill=tk.BOTH, expand=True)
		txt_input.insert("1.0", current_note)
		txt_input.focus_set()

	def remove_note(self):
		if self.selected_raw_index in self.notes:
			del self.notes[self.selected_raw_index]
			self.render_viewport()
			self.refresh_notes_window()

	def export_notes(self):
		if not self.notes:
			messagebox.showinfo("Export Notes", "There are no notes to export.", parent=self.root)
			return

		if not self.current_log_path:
			messagebox.showerror("Export Error", "A log file must be loaded to save notes.", parent=self.root)
			return

		# Construct the file path directly in the log's directory
		log_dir = os.path.dirname(self.current_log_path)
		log_basename = os.path.basename(self.current_log_path)
		log_name_without_ext, _ = os.path.splitext(log_basename)
		note_filename = f"{log_name_without_ext}.note"
		filepath = os.path.join(log_dir, note_filename)

		# Ask for confirmation before overwriting an existing file
		if os.path.exists(filepath):
			if not messagebox.askyesno("Confirm Overwrite", f"The file '{note_filename}' already exists.\n\nDo you want to overwrite it?", parent=self.root):
				return

		try:
			with open(filepath, 'w', encoding='utf-8') as f:
				json.dump(self.notes, f, indent=4, sort_keys=True)
			messagebox.showinfo("Success", f"Successfully exported {len(self.notes)} notes to:\n{filepath}", parent=self.root)
		except Exception as e:
			messagebox.showerror("Export Error", f"Failed to save notes file:\n{e}", parent=self.root)

	def save_notes_to_text(self):
		if not self.notes:
			messagebox.showinfo("Save Notes", "There are no notes to save.", parent=self.root)
			return

		if not self.current_log_path:
			messagebox.showerror("Save Error", "A log file must be loaded to generate a file name.", parent=self.root)
			return

		log_basename = os.path.basename(self.current_log_path)
		log_name_without_ext, _ = os.path.splitext(log_basename)
		default_filename = f"{log_name_without_ext}.txt"

		filepath = filedialog.asksaveasfilename(
			parent=self.root,
			title="Save Notes to Text File",
			initialfile=default_filename,
			defaultextension=".txt",
			filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")]
		)

		if not filepath:
			return

		try:
			lines_to_write = []
			sorted_indices = sorted(self.notes.keys())
			for idx in sorted_indices:
				line_num = idx + 1
				timestamp_str = ""
				if idx < len(self.raw_lines):
					log_line = self.raw_lines[idx]
					match = re.search(r'(\b\d{1,2}:\d{2}:\d{2}\.\d+\s+(?:AM|PM)\b|\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+|\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?|\b\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?\b)', log_line)
					if match:
						timestamp_str = match.group(1)
				
				content = self.notes[idx].replace("\n", " ") # Flatten content
				lines_to_write.append(f"{line_num}\t{timestamp_str}\t{content}")

			with open(filepath, 'w', encoding='utf-8') as f:
				f.write("\n".join(lines_to_write))
			messagebox.showinfo("Success", f"Successfully saved {len(lines_to_write)} notes to:\n{filepath}", parent=self.root)
		except Exception as e:
			messagebox.showerror("Save Error", f"Failed to save notes to text file:\n{e}", parent=self.root)

	def toggle_note_view_visibility(self, initial_setup=False):
		is_visible = self.note_view_visible_var.get()

		if not is_visible:
			# Hide the view
			if self.notes_frame and self.notes_frame.winfo_exists():
				try:
					self.top_pane.remove(self.notes_frame)
					self.notes_frame.destroy()
				except tk.TclError: pass # Already removed
				self.notes_frame = None
			if self.notes_window and self.notes_window.winfo_exists():
				self.notes_window.destroy()
				self.notes_window = None
			return

		# If we need to show it, decide where based on the other flag
		self.toggle_note_view_mode(initial_setup=initial_setup)

	def toggle_note_view_mode(self, initial_setup=False):
		# This function now only decides *where* to show the notes, not *if*.
		if not self.note_view_visible_var.get() and not initial_setup:
			return # Do nothing if the view is meant to be hidden

		is_window_mode = self.show_notes_in_window_var.get()

		if not initial_setup:
			self.config["note_view_mode"] = "window" if is_window_mode else "docked"
			self.save_config()

		if is_window_mode:
			self.undock_note_view()
		else:
			self.dock_note_view()

	def undock_note_view(self):
		# Destroy the docked frame if it exists
		if self.notes_frame and self.notes_frame.winfo_exists():
			try:
				self.top_pane.remove(self.notes_frame)
				self.notes_frame.destroy()
			except tk.TclError: pass
		self.notes_frame = None

		if self.notes_window is None or not self.notes_window.winfo_exists():
			self.notes_window = tk.Toplevel(self.root)
			self.notes_window.title("Notes")
			self.notes_window.geometry("400x500")
			self.notes_window.protocol("WM_DELETE_WINDOW", self.on_notes_window_close)
		
		# Re-create the widgets inside the Toplevel window
		self._create_notes_view_widgets(self.notes_window)
		self.refresh_notes_window()
		self.notes_window.lift()

	def dock_note_view(self):
		# Destroy the separate window if it exists
		if self.notes_window is not None and self.notes_window.winfo_exists():
			self.notes_window.destroy()
			self.notes_window = None

		# Re-create the frame and its widgets inside the main pane
		self.notes_frame = ttk.LabelFrame(self.top_pane, text="Notes")
		self._create_notes_view_widgets(self.notes_frame)
		self.top_pane.add(self.notes_frame, minsize=200)
		self.refresh_notes_window()

	def on_notes_window_close(self):
		# This is called when the 'X' of the Toplevel is clicked
		self.note_view_visible_var.set(False) # Uncheck "Show Notes"
		self.toggle_note_view_visibility() # This will trigger hiding

	def on_notes_tree_right_click(self, event):
		item_id = self.notes_tree.identify_row(event.y)
		if item_id:
			self.notes_tree.selection_set(item_id)
			self.notes_context_menu.post(event.x_root, event.y_root)

	def edit_note_from_tree(self):
		selected = self.notes_tree.selection()
		if not selected: return
		tags = self.notes_tree.item(selected[0], "tags")
		if tags:
			raw_idx = int(tags[0])
			self.add_note_dialog(target_index=raw_idx)

	def remove_note_from_tree(self):
		selected = self.notes_tree.selection()
		if not selected: return
		tags = self.notes_tree.item(selected[0], "tags")
		if tags:
			raw_idx = int(tags[0])
			if raw_idx in self.notes:
				del self.notes[raw_idx]
				self.render_viewport()
				self.refresh_notes_window()

	def refresh_notes_window(self):
		if not hasattr(self, 'notes_tree') or not self.notes_tree.winfo_exists(): return

		for item in self.notes_tree.get_children():
			self.notes_tree.delete(item)

		sorted_indices = sorted(self.notes.keys())
		for idx in sorted_indices:
			line_num = idx + 1

			# Extract timestamp from the raw log line
			timestamp_str = ""
			if idx < len(self.raw_lines):
				log_line = self.raw_lines[idx]
				# Regex to find common timestamp formats.
				# 1. HH:MM:SS.MS AM/PM
				# 2. MM/DD/YYYY-HH:MM:SS.ms
				# 3. YYYY-MM-DD HH:MM:SS,ms
				# 4. HH:MM:SS.ms
				match = re.search(r'(\b\d{1,2}:\d{2}:\d{2}\.\d+\s+(?:AM|PM)\b|\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+|\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?|\b\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?\b)', log_line)
				if match:
					timestamp_str = match.group(1)

			content = self.notes[idx].replace("\n", " ") # Flatten for display
			self.notes_tree.insert("", "end", values=(line_num, timestamp_str, content), tags=(str(idx),))

	def on_note_double_click(self, event):
		item_id = self.notes_tree.identify_row(event.y)
		if not item_id: return

		try:
			# We can use the tag which stores raw index
			tags = self.notes_tree.item(item_id, "tags")
			if tags:
				raw_idx = int(tags[0])
				self.jump_to_line(raw_idx)
		except Exception as e: print(e)

	def check_and_import_notes(self):
		if not self.current_log_path:
			return

		log_basename = os.path.basename(self.current_log_path)
		log_name_without_ext, _ = os.path.splitext(log_basename)
		note_filename = f"{log_name_without_ext}.note"

		# Look for the note file in the same directory as the log file
		log_dir = os.path.dirname(self.current_log_path)
		potential_path = os.path.join(log_dir, note_filename)

		if os.path.exists(potential_path):
			if messagebox.askyesno("Import Notes", f"Found a matching notes file:\n'{note_filename}'\n\nDo you want to import the notes?"):
				try:
					with open(potential_path, 'r', encoding='utf-8') as f:
						# JSON keys are strings, convert them back to int
						str_keyed_notes = json.load(f)
						self.notes = {int(k): v for k, v in str_keyed_notes.items()}

					self.update_status(f"Imported {len(self.notes)} notes.")
					
					# Auto-show notes window on successful import
					self.note_view_visible_var.set(True)
					self.toggle_note_view_visibility()
					# The calling function will handle UI refresh

				except Exception as e:
					messagebox.showerror("Import Error", f"Failed to import notes:\n{e}")



	def jump_to_line(self, raw_index):
		# Check if line is in filtered view
		found_in_view = False
		if self.filtered_cache is not None:
			try:
				view_idx = self.filtered_indices.index(raw_index)
				total_in_view = len(self.filtered_indices)
				# Center it
				half = self.visible_rows // 2
				new_start = max(0, view_idx - half)
				new_start = min(new_start, max(0, total_in_view - self.visible_rows))
				self.view_start_index = new_start
				self.selection_offset = view_idx - new_start
				found_in_view = True
			except ValueError:
				# Line is filtered out
				if messagebox.askyesno("Navigation", "The selected line is currently hidden by filters.\nDo you want to switch to 'Full View' to see it?"):
					self.show_only_filtered_var.set(False)
					self.refresh_view_fast()
					found_in_view = False # Will fall through to raw view handling
				else:
					return

		if not found_in_view:
			# Full view
			self.selected_raw_index = raw_index
			total_in_view = len(self.raw_lines)
			half = self.visible_rows // 2
			new_start = max(0, raw_index - half)
			new_start = min(new_start, max(0, total_in_view - self.visible_rows))
			self.view_start_index = new_start
			self.selection_offset = raw_index - new_start

		self.selected_raw_index = raw_index # Ensure selected
		self.render_viewport()
		self.update_scrollbar_thumb()


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
			if raw_idx in self.notes:
				tag_buffer.append((relative_idx, ["note_line"]))
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
				self.font_object.configure(size=self.font_size)
				self.config["font_size"] = self.font_size; self.save_config()
				# The <Configure> event will handle the rest
		return "break"

	def update_visible_rows(self, event=None):
		widget_height = self.text_area.winfo_height()
		line_height = self.font_object.metrics("linespace")
		if line_height > 0:
			self.visible_rows = max(1, widget_height // line_height)
			self.render_viewport(); self.update_scrollbar_thumb()

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
		if self.is_processing: return
		region = self.tree.identify("region", event.x, event.y)
		if region == "cell":
			column = self.tree.identify_column(event.x)
			if column == "#1":
				item_id = self.tree.identify_row(event.y)
				if item_id:
					idx = self.tree.index(item_id)
					self.filters[idx].enabled = not self.filters[idx].enabled
					self.smart_update_filter(idx, self.filters[idx].enabled)
					return "break"
			else:
				item_id = self.tree.identify_row(event.y)
				if item_id: self.drag_start_index = self.tree.index(item_id)

	def on_tree_release(self, event):
		if self.is_processing: return
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
		if self.is_processing: return
		selected = self.tree.selection()
		if not selected: return
		item_id = selected[0]; idx = self.tree.index(item_id)
		self.open_filter_dialog(self.filters[idx], idx)

	def on_filter_toggle(self, event):
		if self.is_processing: return
		selected_item = self.tree.selection()
		if not selected_item: return
		for item_id in selected_item:
			idx = self.tree.index(item_id)
			self.filters[idx].enabled = not self.filters[idx].enabled
			self.smart_update_filter(idx, self.filters[idx].enabled)

	def on_filter_delete(self, event=None):
		if self.is_processing: return
		selected_items = self.tree.selection()
		if not selected_items: return
		indices_to_delete = sorted([self.tree.index(item) for item in selected_items], reverse=True)
		for idx in indices_to_delete:
			del self.filters[idx]
			if idx in self.filter_matches: del self.filter_matches[idx]
		self.recalc_filtered_data()

	def on_filter_double_click(self, event):
		if self.is_processing: return
		item_id = self.tree.identify_row(event.y)
		if not item_id: return
		if self.tree.identify_column(event.x) == "#1": return
		idx = self.tree.index(item_id)
		self.open_filter_dialog(self.filters[idx], idx)

	def add_filter_dialog(self, initial_text=None):
		if self.is_processing: return
		self.open_filter_dialog(None, index=None, initial_text=initial_text)

	def open_filter_dialog(self, filter_obj=None, index=None, initial_text=None):
		dialog = tk.Toplevel(self.root)
		dialog.title("Edit Filter" if filter_obj else "Add Filter")
		dialog.transient(self.root)
		dialog.grab_set()
		dialog.geometry("400x200")

		main_frame = ttk.Frame(dialog, padding=10)
		main_frame.pack(fill=tk.BOTH, expand=True)

		pattern_frame = ttk.Frame(main_frame)
		pattern_frame.pack(fill=tk.X, expand=True)
		ttk.Label(pattern_frame, text="Pattern:", width=10).pack(side=tk.LEFT, padx=(0, 5))
		entry_text = ttk.Entry(pattern_frame)
		entry_text.pack(fill=tk.X, expand=True)
		if filter_obj: entry_text.insert(0, filter_obj.text)
		elif initial_text: entry_text.insert(0, initial_text)

		options_frame = ttk.Frame(main_frame, padding=(0, 10, 0, 10))
		options_frame.pack(fill=tk.X, expand=True)
		var_regex = tk.BooleanVar(value=filter_obj.is_regex if filter_obj else False)
		var_exclude = tk.BooleanVar(value=filter_obj.is_exclude if filter_obj else False)
		ttk.Checkbutton(options_frame, text="Regex", variable=var_regex).pack(side=tk.LEFT)
		ttk.Checkbutton(options_frame, text="Exclude", variable=var_exclude).pack(side=tk.LEFT, padx=10)

		colors = {"fg": filter_obj.fore_color if filter_obj else "#000000", "bg": filter_obj.back_color if filter_obj else "#FFFFFF"}

		color_frame = ttk.Frame(main_frame)
		color_frame.pack(fill=tk.BOTH, expand=True)

		def pick_fg():
			c = colorchooser.askcolor(color=colors["fg"])[1]
			if c: colors["fg"] = c; btn_fg.config(style="FG.TButton")
		def pick_bg():
			c = colorchooser.askcolor(color=colors["bg"])[1]
			if c: colors["bg"] = c; btn_bg.config(style="BG.TButton")

		style = ttk.Style(dialog)
		style.configure("FG.TButton", foreground=colors["fg"], background=colors["fg"])
		style.configure("BG.TButton", foreground=colors["bg"], background=colors["bg"])

		btn_fg = ttk.Button(color_frame, text="Text Color", command=pick_fg, style="FG.TButton")
		btn_fg.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
		btn_bg = ttk.Button(color_frame, text="Back Color", command=pick_bg, style="BG.TButton")
		btn_bg.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)

		button_frame = ttk.Frame(main_frame, padding=(0, 10, 0, 0))
		button_frame.pack(fill=tk.X)

		def save():
			text = entry_text.get()
			if not text: return
			if filter_obj:
				filter_obj.text = text; filter_obj.fore_color = colors["fg"]; filter_obj.back_color = colors["bg"]
				filter_obj.is_regex = var_regex.get(); filter_obj.is_exclude = var_exclude.get()
				if index in self.filter_matches: del self.filter_matches[index]
				self.recalc_filtered_data()
			else:
				new_filter = Filter(text, colors["fg"], colors["bg"], enabled=True, is_regex=var_regex.get(), is_exclude=var_exclude.get())
				self.filters.append(new_filter)
				self.recalc_filtered_data()
			dialog.destroy()

		ttk.Button(button_frame, text="Save", command=save).pack(side=tk.RIGHT)
		ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
		entry_text.focus_set()
		dialog.wait_window()

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
		if self.is_processing: return
		if self.current_tat_path:
			if self._write_tat_file(self.current_tat_path): messagebox.showinfo("Save", "Saved successfully")
		else: self.save_as_tat_filters()

	def save_as_tat_filters(self):
		if self.is_processing: return
		init_dir = self.config.get("last_filter_dir", ".")
		filepath = filedialog.asksaveasfilename(initialdir=init_dir, defaultextension=".tat", filetypes=[("TextAnalysisTool", "*.tat"), ("XML", "*.xml")])
		if not filepath: return
		self.config["last_filter_dir"] = os.path.dirname(filepath); self.save_config()
		if self._write_tat_file(filepath):
			self.current_tat_path = filepath; self.update_title()
			messagebox.showinfo("Success", "File saved")

	def import_tat_filters(self):
		if self.is_processing: return
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
			self.filter_matches = {}
			self.recalc_filtered_data()
			messagebox.showinfo("Success", f"Imported {len(new_filters)} filters")
		except Exception as e: messagebox.showerror("Import Error", str(e))

	# JSON methods
	def export_filters(self):
		if self.is_processing: return
		init_dir = self.config.get("last_filter_dir", ".")
		filepath = filedialog.asksaveasfilename(initialdir=init_dir, defaultextension=".json", filetypes=[("JSON", "*.json")])
		if not filepath: return
		self.config["last_filter_dir"] = os.path.dirname(filepath); self.save_config()
		data = [f.to_dict() for f in self.filters]
		with open(filepath, 'w') as f: json.dump(data, f, indent=4)

	def import_json_filters(self):
		if self.is_processing: return
		init_dir = self.config.get("last_filter_dir", ".")
		filepath = filedialog.askopenfilename(initialdir=init_dir, filetypes=[("JSON", "*.json")])
		if not filepath: return
		self.config["last_filter_dir"] = os.path.dirname(filepath); self.save_config()
		try:
			with open(filepath, 'r') as f:
				data = json.load(f)
				self.filters = [Filter(**item) for item in data]
			self.filter_matches = {}
			self.recalc_filtered_data()
		except Exception as e: messagebox.showerror("Error", f"JSON Import Failed: {e}")

if __name__ == "__main__":
	root = TkinterDnD.Tk()
	app = LogAnalyzerApp(root)
	root.mainloop()