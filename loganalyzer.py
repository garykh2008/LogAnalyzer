import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox, ttk
try:
	from tkinterdnd2 import DND_FILES, TkinterDnD
	HAS_DND = True
except ImportError:
	HAS_DND = False
import tkinter.font as tkFont
import re
import json
import xml.etree.ElementTree as ET
import os
import time
import threading
import datetime
import queue
import webbrowser
import sys
import bisect
import ctypes

# --- Rust Extension Import ---
try:
	import log_engine_rs
	HAS_RUST = True
except ImportError:
	HAS_RUST = False

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

def hex_to_rgb(hex_str):
	hex_str = hex_str.lstrip('#')
	if not hex_str: return (0, 0, 0)
	if len(hex_str) == 3: hex_str = "".join(c*2 for c in hex_str)
	try:
		return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))
	except: return (0, 0, 0)

def adjust_color_for_theme(hex_color, is_background, is_dark_mode):
	"""
	Dynamically adjusts filter colors for Dark Mode to prevent jarring contrast.
	- White backgrounds become dark/transparent.
	- Black text becomes light text.
	- Bright pastel backgrounds are dimmed.
	- Dark text is lightened.
	"""
	if not hex_color: return hex_color
	hex_color = hex_color.strip().lower()
	if not hex_color.startswith("#"): hex_color = "#" + hex_color

	if not is_dark_mode:
		return hex_color

	# 1. Handle Defaults
	if is_background and (hex_color == "#ffffff" or hex_color == "#fff"):
		return "#1e1e1e" # Match dark theme bg
	if not is_background and (hex_color == "#000000" or hex_color == "#000"):
		return "#d4d4d4" # Match dark theme text

	# 2. Smart Adjustment based on Luminance
	rgb = hex_to_rgb(hex_color)
	lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]) / 255.0

	if is_background and lum > 0.4: # Too bright for dark mode bg
		return '#{:02x}{:02x}{:02x}'.format(*tuple(int(c * 0.25) for c in rgb))
	if not is_background and lum < 0.5: # Too dark for dark mode text
		return '#{:02x}{:02x}{:02x}'.format(*tuple(int(c + (255 - c) * 0.6) for c in rgb))

	return hex_color

# --- Core Classes ---

class Filter:
	def __init__(self, text, fore_color="#000000", back_color="#FFFFFF", enabled=True, is_regex=False, is_exclude=False, is_event=False):
		self.text = text
		self.fore_color = fore_color
		self.back_color = back_color
		self.enabled = enabled
		self.is_regex = is_regex
		self.is_exclude = is_exclude
		self.is_event = is_event
		self.hit_count = 0

	def to_dict(self):
		d = self.__dict__.copy()
		if 'hit_count' in d: del d['hit_count']
		return d

class RustLinesProxy:
	"""Proxies list access to the Rust LogEngine to avoid copying strings to Python."""
	def __init__(self, engine):
		self.engine = engine

	def __len__(self):
		return self.engine.line_count()

	def __getitem__(self, idx):
		return self.engine.get_line(idx)

class LogAnalyzerApp:
	def __init__(self, root):
		self.root = root

		# Config
		self.config_file = "app_config.json"
		self.config = self.load_config()
		self.non_maximized_geometry = self.config.get("main_window_geometry", "1000x750")
		self.root.geometry(self.non_maximized_geometry)
		if self.config.get("window_maximized", False):
			try:
				self.root.state("zoomed")
			except Exception: pass

		# Set application icon
		self.icon_path = None
		try:
			icon_path = self.resource_path("loganalyzer.ico")
			self.root.iconbitmap(icon_path)
			self.icon_path = icon_path
		except Exception:
			# Fallback for systems that might not support .ico or if file is missing
			pass


		# --- UI Theme ---
		style = ttk.Style(self.root)
		style.theme_use("clam")

		# Modern Treeview Style
		style.configure("Treeview", rowheight=28, font=("Consolas", 11), borderwidth=1, relief="solid")
		style.configure("Treeview.Heading", font=("Consolas", 10, "bold"), borderwidth=1, relief="groove")

		style.configure("TLabelFrame", padding=5)
		style.configure("TLabelFrame.Label", font=("Consolas", 10, "bold"))

		style.configure("TButton", padding=4, font=("Consolas", 10))

		style.configure("TLabel", font=("Consolas", 12))
		style.configure("TCheckbutton", font=("Consolas", 12))
		style.configure("TEntry", font=("Consolas", 12))
		style.configure("TProgressbar", thickness=15)

		# App Info
		self.APP_NAME = "Log Analyzer"
		self.VERSION = "V1.6.3"

		if not HAS_RUST:
			# Since we are removing Python fallbacks, we must warn the user if the engine is missing.
			messagebox.showerror("Error", "Rust extension (log_engine_rs) not found.\nPlease build the extension to use this application.")


		# Threading & Queue
		self.msg_queue = queue.Queue()
		self.is_processing = False

		self.dark_mode = tk.BooleanVar(value=self.config.get("dark_mode", False))

		self.filters = []
		self.raw_lines = []
		self.rust_engine = None # Instance of log_engine_rs.LogEngine

		# Cache structure: [(line_content, tags, raw_index), ...]
		# If None, it means "Raw Mode"
		self.filtered_cache = None

		# Store result of regex scan for ALL lines
		self.all_line_tags = []

		# Pre-computed indices for filtered view [idx1, idx2, ...]
		self.filtered_indices = []

		self.current_log_path = None

		# Search Cache
		self.last_search_query = None
		self.last_search_results = None # List of raw indices from Rust
		self.last_search_case = False

		self.current_tat_path = None

		# Notes System
		self.notes = {}  # { raw_index (int): note_text (str) }
		self.notes_window = None

		# Timeline System
		self.timeline_events = [] # List of (datetime_obj, filter_text, raw_index)
		self.timestamps_found = False
		self.timeline_win = None # Reference to the Toplevel timeline window
		self.timeline_draw_func = None # Reference to the draw_timeline function

		self.view_start_index = 0
		self.visible_rows = 50

		# Font management
		self.font_size = self.config.get("font_size", 12)
		self.font_object = tkFont.Font(family="Consolas", size=self.font_size)

		# Dynamic Style for Notes (Scalable)
		style.configure("Notes.Treeview", font=("Consolas", self.font_size), rowheight=int(max(20, self.font_size * 2.0)))
		style.configure("Notes.Treeview.Heading", font=("Consolas", 12, "bold")) # Headings stay fixed or scalable? Let's keep headings fixed 12 for consistency with UI

		self.selected_raw_index = -1
		self.selection_offset = 0

		self.note_view_visible_var = tk.BooleanVar(value=False)
		note_view_mode = self.config.get("note_view_mode", "docked")
		self.show_notes_in_window_var = tk.BooleanVar(value=(note_view_mode == "window"))
		self.show_only_filtered_var = tk.BooleanVar(value=False)

		# Duration strings
		self.load_duration_str = "0.000s"
		self.filter_duration_str = "0.000s"

		# Drag & Drop State
		self.drag_start_index = None
		self.drag_target_id = None
		self.drag_position = None # 'before' or 'after'
		self.drop_indicator = None # Will be created after tree

		# --- UI Layout ---

		# 1. Menu Bar
		self.menubar = tk.Menu(root)
		root.config(menu=self.menubar)

		# [File Menu]
		self.file_menu = tk.Menu(self.menubar, tearoff=0)
		self.menubar.add_cascade(label="File", menu=self.file_menu)

		self.file_menu.add_command(label="Open Log...", command=self.load_log)
		self.recent_files_menu = tk.Menu(self.file_menu, tearoff=0)
		self.file_menu.add_cascade(label="Open Recent", menu=self.recent_files_menu, state="disabled")
		self.file_menu.add_separator()

		self.file_menu.add_command(label="Load Filters", command=self.import_tat_filters)
		self.file_menu.add_command(label="Save Filters", command=self.quick_save_tat)
		self.file_menu.add_command(label="Save Filters As", command=self.save_as_tat_filters)

		# JSON Features (Hidden)
		# self.file_menu.add_separator()
		# self.file_menu.add_command(label="Import JSON", command=self.import_json_filters)
		# self.file_menu.add_command(label="Export JSON", command=self.export_filters)

		self.file_menu.add_separator()
		self.file_menu.add_command(label="Exit", command=self.on_close)

		# [Filter Menu]
		self.filter_menu = tk.Menu(self.menubar, tearoff=0)
		self.menubar.add_cascade(label="Filter", menu=self.filter_menu)

		self.filter_menu.add_command(label="Add Filter", command=self.add_filter_dialog)
		self.filter_menu.add_checkbutton(label="Show Filtered Only", onvalue=True, offvalue=False,
										 variable=self.show_only_filtered_var,
										 command=self.toggle_show_filtered,
										 accelerator="Ctrl+H")

		# [View Menu]
		self.view_menu = tk.Menu(self.menubar, tearoff=0)
		self.menubar.add_cascade(label="View", menu=self.view_menu)
		self.view_menu.add_command(label="Find...", accelerator="Ctrl+F", command=self.show_find_bar)
		self.view_menu.add_command(label="Go to Line...", accelerator="Ctrl+G", command=self.show_goto_dialog)
		self.view_menu.add_separator()
		self.view_menu.add_checkbutton(label="Dark Mode", variable=self.dark_mode, command=self.toggle_dark_mode)
		self.view_menu.add_separator()
		self.view_menu.add_command(label="Show Timeline", command=self.show_timeline_window, state="disabled")


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

		self.status_label = ttk.Label(status_frame, text="Ready", anchor=tk.W)
		self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

		# Update initial title and status
		self.update_title()
		self.update_status("Ready")

		# 3. Main Content Area (PanedWindow)
		self.paned_window = tk.PanedWindow(root, orient=tk.VERTICAL, sashwidth=4, sashrelief=tk.FLAT, bg="#d9d9d9")
		self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

		# --- Upper: Log View ---
		# --- Upper Pane: Contains both Log View and Note View ---
		top_pane = tk.PanedWindow(self.paned_window, orient=tk.HORIZONTAL, sashwidth=4, sashrelief=tk.FLAT, bg="#d9d9d9")

		# --- Upper-Left: Log View ---
		self.content_frame = ttk.Frame(top_pane)

		self.scrollbar_y = ttk.Scrollbar(self.content_frame, command=self.on_scroll_y)
		self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

		# Search Marker Canvas (Minimap)
		self.marker_canvas = tk.Canvas(self.content_frame, width=12, bg="#f0f0f0", bd=0, highlightthickness=0)
		self.marker_canvas.pack(side=tk.RIGHT, fill=tk.Y)
		self.marker_canvas.bind("<Button-1>", self.on_marker_click)
		self.marker_canvas.bind("<Configure>", self.on_marker_resize)

		self.line_number_area = tk.Text(self.content_frame, width=7, wrap="none", font=self.font_object,
										state="disabled", bg="#f0f0f0", bd=0, highlightthickness=0, takefocus=0)
		self.line_number_area.pack(side=tk.LEFT, fill=tk.Y)
		self.line_number_area.tag_configure("right_align", justify="right")

		self.text_area = tk.Text(self.content_frame, wrap="none", font=self.font_object)
		self.scrollbar_x = ttk.Scrollbar(self.content_frame, orient="horizontal", command=self.text_area.xview)
		self.text_area.configure(xscrollcommand=self.scrollbar_x.set)

		self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
		self.text_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

		# Welcome Label (Empty State)
		self.welcome_label = tk.Label(self.text_area, text="Drag & Drop Log File Here\nor use File > Open Log",
									  font=("Consolas", 14), fg="#888888", bg="#ffffff")
		self.welcome_label.place(relx=0.5, rely=0.5, anchor="center")

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

		self.root.bind("<Control-f>", self.show_find_bar)
		self.root.bind("<Control-F>", self.show_find_bar)
		self.root.bind("<F3>", self.find_next)
		self.root.bind("<F2>", self.find_previous)
		self.root.bind("<Escape>", self.on_escape)

		self.root.bind("<Control-g>", self.show_goto_dialog)
		self.root.bind("<Control-G>", self.show_goto_dialog)

		# --- Find Bar State ---
		self.find_window = None
		self.find_entry = None
		self.find_case_var = tk.BooleanVar(value=False)
		self.find_wrap_var = tk.BooleanVar(value=True)

		self.root.bind("<Control-Left>", self.on_nav_prev_match)
		self.root.bind("<Control-Right>", self.on_nav_next_match)

		top_pane.add(self.content_frame, width=750, minsize=300, stretch="always")

		# --- Upper-Right: Note View (Placeholder) ---
		# The actual notes_frame will be created dynamically
		self.notes_frame = None
		self.top_pane = top_pane

		# Initial setup: Hide the notes view by default
		self.toggle_note_view_visibility(initial_setup=True)

		self.paned_window.add(top_pane, height=450, minsize=100, stretch="always")

		# Context Menu for Notes Tree
		self.notes_context_menu = tk.Menu(self.root, tearoff=0)
		self.notes_context_menu.add_command(label="Edit Note", command=self.edit_note_from_tree)
		self.notes_context_menu.add_command(label="Remove Note", command=self.remove_note_from_tree)

		# Log Context Menu
		self.log_context_menu = tk.Menu(self.root, tearoff=0)
		self.log_context_menu.add_command(label="Add/Edit Note", command=self.add_note_dialog)
		self.log_context_menu.add_command(label="Remove Note", command=self.remove_note)

		# --- Lower: Filter View ---
		filter_frame = ttk.LabelFrame(self.paned_window, text="Filters")

		cols = ("enabled", "type", "pattern", "hits", "event")
		self.tree = ttk.Treeview(filter_frame, columns=cols, show="headings")

		self.tree.heading("enabled", text="En")
		self.tree.column("enabled", width=30, minwidth=30, stretch=False, anchor="center")
		self.tree.heading("type", text="Type")
		self.tree.column("type", width=50, minwidth=50, stretch=False, anchor="center")
		self.tree.heading("pattern", text="Pattern / Regex")
		self.tree.column("pattern", width=600, anchor="w")
		self.tree.heading("hits", text="Hits")
		self.tree.column("hits", width=80, minwidth=80, stretch=False, anchor="center")
		self.tree.heading("event", text="Event")
		self.tree.column("event", width=50, minwidth=50, stretch=False, anchor="center")

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
		self.tree.bind("<B1-Motion>", self.on_tree_drag_motion)

		# Create Drop Indicator (Hidden by default)
		self.drop_indicator = tk.Frame(self.tree, height=2, bg="black")

		# Context Menu
		self.event_menu_var = tk.BooleanVar()
		self.context_menu = tk.Menu(self.root, tearoff=0)
		self.context_menu.add_checkbutton(label="Set as Event", variable=self.event_menu_var, command=self.toggle_selected_filters_as_event)
		self.context_menu.add_separator()
		self.context_menu.add_command(label="Remove Filter", command=self.on_filter_delete)
		self.context_menu.add_command(label="Edit Filter", command=self.edit_selected_filter)
		self.context_menu.add_command(label="Add Filter", command=self.add_filter_dialog)
		self.context_menu.add_separator()
		self.context_menu.add_command(label="Move to Top", command=self.move_filter_to_top)
		self.context_menu.add_command(label="Move to Bottom", command=self.move_filter_to_bottom)

		self.paned_window.add(filter_frame, minsize=100, stretch="never")

		# Start Queue Checker
		self.check_queue()

		# --- Drag and Drop ---
		if HAS_DND:
			self.root.drop_target_register(DND_FILES)
			self.root.dnd_bind('<<Drop>>', self.on_drop)

		# Apply initial theme
		self._apply_theme()
		self._update_recent_files_menu()

		self.root.bind("<Configure>", self.on_root_configure)
		self.root.protocol("WM_DELETE_WINDOW", self.on_close)
		self.root.after(200, self._restore_layout)

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
		self.notes_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", style="Notes.Treeview")
		self.notes_tree.heading("line", text="Line")
		self.notes_tree.column("line", width=80, minwidth=80, stretch=False, anchor="center")
		self.notes_tree.heading("timestamp", text="Timestamp")
		self.notes_tree.column("timestamp", width=230, minwidth=200, stretch=False, anchor="w")
		self.notes_tree.heading("content", text="Note Content")
		self.notes_tree.column("content", width=350, anchor="w")
		scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.notes_tree.yview)
		self.notes_tree.configure(yscrollcommand=scroll.set)
		scroll.pack(side=tk.RIGHT, fill=tk.Y)
		self.notes_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
		self.notes_tree.bind("<Double-1>", self.on_note_double_click)
		self.notes_tree.bind("<Button-3>", self.on_notes_tree_right_click)

	def _restore_layout(self):
		sash_y = self.config.get("sash_main_y")
		if sash_y:
			try:
				self.paned_window.sash_place(0, 0, sash_y)
			except Exception: pass

	def on_root_configure(self, event):
		if event.widget == self.root:
			# Only update stored geometry if the window is in 'normal' state (not maximized/zoomed or iconic)
			try:
				if self.root.state() == "normal":
					self.non_maximized_geometry = self.root.geometry()
			except Exception: pass

	def on_close(self):
		self._save_notes_window_geometry()

		is_maximized = False
		try:
			if self.root.state() == "zoomed": is_maximized = True
		except Exception: pass
		self.config["window_maximized"] = is_maximized

		self.config["main_window_geometry"] = self.non_maximized_geometry

		self.config["note_view_visible"] = self.note_view_visible_var.get()

		try:
			self.config["sash_main_y"] = self.paned_window.sash_coord(0)[1]
		except Exception: pass

		self.save_config()
		self.root.destroy()
		sys.exit(0)

	def _apply_icon(self, toplevel_window):
		"""Applies the application icon to a toplevel window."""
		if self.icon_path:
			try:
				toplevel_window.iconbitmap(self.icon_path)
			except Exception:
				pass # Ignore if it fails for a specific window


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
			("General & View", ""),
			("Ctrl + F", "Open the Find window"),
			("Ctrl + G", "Go to a specific line number"),
			("Ctrl + H", "Toggle between 'Show Filtered Only' and 'Show All'"),
			("Ctrl + Scroll", "Adjust font size in the log view"),
			("", ""),
			("Find & Navigation", ""),
			("F2", "Find previous occurrence"),
			("F3", "Find next occurrence"),
			("Ctrl + Left/Right", "Jump to previous/next match for a selected filter"),
			("", ""),
			("Log View", ""),
			("Double-Click", "Select text to quickly add a new filter"),
			("'c' key", "Add or edit a note for the selected line"),
			("", ""),
			("Filter List", ""),
			("Double-Click", "Edit the selected filter"),
			("Spacebar", "Enable or disable the selected filter"),
			("Delete key", "Remove the selected filter(s)"),
		]

		win = tk.Toplevel(self.root)
		win.title("Keyboard Shortcuts")
		self._apply_icon(win)
		win.transient(self.root)
		win.grab_set()
		win.geometry("750x550")

		frame = ttk.Frame(win, padding=15)
		frame.pack(fill=tk.BOTH, expand=True)

		for i, (key, desc) in enumerate(shortcuts):
			if not key and not desc:
				ttk.Separator(frame, orient='horizontal').grid(row=i, columnspan=2, sticky='ew', pady=5)
				continue
			ttk.Label(frame, text=key, font=("Consolas", 12, "bold")).grid(row=i, column=0, sticky='w', padx=(0, 10))
			ttk.Label(frame, text=desc).grid(row=i, column=1, sticky='w')

	# --- Status Update ---
	def update_status(self, msg):
		full_text = f"{msg}    |    Load Time: {self.load_duration_str}    |    Filter Time: {self.filter_duration_str}"
		if not hasattr(self, 'status_label'): return
		self.status_label.config(text=full_text)

	# --- Tag Configuration ---
	def apply_tag_styles(self):
		is_dark = self.dark_mode.get()
		for i, flt in enumerate(self.filters):
			tag_name = f"filter_{i}"
			# Adjust colors for theme without modifying the filter object
			fg = adjust_color_for_theme(flt.fore_color, False, is_dark)
			bg = adjust_color_for_theme(flt.back_color, True, is_dark)
			self.text_area.tag_config(tag_name, foreground=fg, background=bg)

			# Update Filter List (Treeview) colors as well
			self.tree.tag_configure(f"row_{i}", foreground=fg, background=bg)

		self.text_area.tag_config("current_line", background="#0078D7", foreground="#FFFFFF")
		if self.dark_mode.get():
			self.text_area.tag_config("note_line", background="#3a3d41", foreground="#d4d4d4")
		else:
			self.text_area.tag_config("note_line", background="#fffbdd", foreground="#000000")

		self.text_area.tag_config("find_match", background="#FFA500", foreground="#000000")
		# New tag for all matches
		find_all_bg = "#4a4a21" if is_dark else "#FFFFE0"
		find_all_fg = "#d4d4d4" if is_dark else "#000000"
		self.text_area.tag_config("find_match_all", background=find_all_bg, foreground=find_all_fg)

	# --- Threading Infrastructure ---
	def check_queue(self):
		try:
			while True:
				msg = self.msg_queue.get_nowait()
				msg_type = msg[0]

				if msg_type == 'load_complete':
					lines, duration, filepath, rust_eng = msg[1], msg[2], msg[3], msg[4]
					self.rust_engine = rust_eng
					self.raw_lines = lines

					# Adjust line number area width based on total lines
					max_digits = len(str(len(lines)))
					self.line_number_area.config(width=max(7, max_digits))

					self.load_duration_str = f"{duration:.4f}s"
					self.current_log_path = filepath
					self.update_title()
					self.selected_raw_index = -1
					self.selection_offset = 0
					self.last_search_query = None
					self.last_search_results = None
					self.marker_canvas.delete("all")
					self.welcome_label.place_forget()

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
					line_tags, filtered_idx, duration, counts = msg[1], msg[2], msg[3], msg[4]

					self.timeline_events, self.timestamps_found = msg[6], msg[7]
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

					self.apply_tag_styles()
					self.refresh_filter_list()
					self.refresh_view_fast()
					# Update timeline data before redrawing
					if self.timeline_win and self.timeline_win.winfo_exists():
						self.timeline_win.sorted_events = sorted(self.timeline_events, key=lambda x: x[0]) if self.timeline_events else []
						self.timeline_win.first_time = self.timeline_win.sorted_events[0][0] if self.timeline_win.sorted_events else None
						self.timeline_win.last_time = self.timeline_win.sorted_events[-1][0] if self.timeline_win.sorted_events else None
					# If timeline window is open, refresh it
					if self.timeline_win and self.timeline_win.winfo_exists() and self.timeline_draw_func:
						self.timeline_draw_func()
					self.view_menu.entryconfig("Show Timeline", state="normal" if self.timestamps_found else "disabled")

					self.set_ui_busy(False)

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
			self.menubar.entryconfig("View", state=state)
			self.menubar.entryconfig("Help", state=state)
		except: pass
		self.tree.state(("disabled",) if is_busy else ("!disabled",))
		self.root.config(cursor="watch" if is_busy else "")

	# --- Toast Notifications ---
	def show_toast(self, message, duration=2000, is_error=False):
		try:
			toast = tk.Toplevel(self.root)
			toast.overrideredirect(True)

			is_dark = self.dark_mode.get()
			bg = "#323232" if is_dark else "#333333"
			fg = "#ffffff"
			if is_error: bg = "#a31515"

			toast.config(bg=bg)
			# Use tk.Label for direct color control
			lbl = tk.Label(toast, text=message, bg=bg, fg=fg, font=("Consolas", 10), padx=15, pady=8)
			lbl.pack()

			# Center horizontally, near bottom
			self.root.update_idletasks()
			rw, rh = self.root.winfo_width(), self.root.winfo_height()
			rx, ry = self.root.winfo_x(), self.root.winfo_y()
			tw, th = lbl.winfo_reqwidth(), lbl.winfo_reqheight()

			x = rx + (rw - tw) // 2
			y = ry + rh - 100
			toast.geometry(f"+{x}+{y}")
			toast.attributes("-alpha", 0.0)

			# Animation
			def fade_in(curr_alpha=0):
				if curr_alpha < 0.9:
					curr_alpha += 0.1
					toast.attributes("-alpha", curr_alpha)
					self.root.after(20, lambda: fade_in(curr_alpha))
				else:
					self.root.after(duration, fade_out)

			def fade_out(curr_alpha=0.9):
				if curr_alpha > 0:
					curr_alpha -= 0.1
					toast.attributes("-alpha", curr_alpha)
					self.root.after(20, lambda: fade_out(curr_alpha))
				else:
					toast.destroy()

			fade_in()
		except Exception: pass

	# --- Config Management ---
	def load_config(self):
		if os.path.exists(self.config_file):
			try:
				with open(self.config_file, 'r') as f: return json.load(f)
			except: pass
		return {}

	def save_config(self):
		try:
			with open(self.config_file, 'w') as f: json.dump(self.config, f, indent=4)
		except: pass

	# --- Recent Files ---
	def _add_to_recent_files(self, filepath):
		"""Adds a file to the top of the recent files list."""
		recent_files = self.config.get("recent_files", [])

		# Remove if already exists to move it to the top
		if filepath in recent_files:
			recent_files.remove(filepath)

		# Add to the top
		recent_files.insert(0, filepath)

		# Trim the list to a max size (e.g., 10)
		self.config["recent_files"] = recent_files[:10]
		self.save_config()
		self._update_recent_files_menu()

	def _update_recent_files_menu(self):
		"""Clears and repopulates the 'Open Recent' menu."""
		self.recent_files_menu.delete(0, tk.END)
		recent_files = self.config.get("recent_files", [])

		if not recent_files:
			self.file_menu.entryconfig("Open Recent", state="disabled")
			return

		self.file_menu.entryconfig("Open Recent", state="normal")
		for filepath in recent_files:
			# Use a lambda with a default argument to capture the filepath correctly
			self.recent_files_menu.add_command(label=filepath, command=lambda p=filepath: self._load_log_from_path(p))

		self.recent_files_menu.add_separator()
		self.recent_files_menu.add_command(label="Clear List", command=self._clear_recent_files)

	def _clear_recent_files(self):
		"""Clears the recent files list from config and updates the menu."""
		if "recent_files" in self.config and self.config["recent_files"]:
			self.config["recent_files"] = []
			self.save_config()
			self._update_recent_files_menu()

	# --- Theming ---
	def toggle_dark_mode(self):
		self.config["dark_mode"] = self.dark_mode.get()
		self.save_config()
		self._apply_theme()

	def _apply_theme(self):
		is_dark = self.dark_mode.get()

		# Define color palettes
		# VS Code-inspired Palette
		c = {
			"bg": "#1e1e1e" if is_dark else "#f3f3f3",
			"fg": "#cccccc" if is_dark else "#1f1f1f",
			"bg_widget": "#1e1e1e" if is_dark else "#ffffff",
			"fg_widget": "#d4d4d4" if is_dark else "#1f1f1f",
			"bg_disabled": "#2d2d2d" if is_dark else "#e0e0e0",
			"fg_disabled": "#6e6e6e" if is_dark else "#888888",
			"bg_select": "#264f78" if is_dark else "#0060c0",
			"fg_select": "#ffffff",
			"bg_pane": "#252526" if is_dark else "#d0d0d0",
			"bg_line_num": "#1e1e1e" if is_dark else "#f8f8f8",
			"fg_line_num": "#858585" if is_dark else "#2b91af",
			"bg_tree": "#252526" if is_dark else "#ffffff",
			"fg_tree": "#cccccc" if is_dark else "#000000",
			"bg_head": "#333333" if is_dark else "#e1e1e1",
			"fg_head": "#eeeeee" if is_dark else "#000000",
			"scrollbar_bg": "#2e2e2e" if is_dark else "#f3f3f3",
			"scrollbar_thumb": "#424242" if is_dark else "#c1c1c1",
			"scrollbar_hover": "#4f4f4f" if is_dark else "#a8a8a8",
			"stripe_odd": "#252526" if is_dark else "#ffffff",
			"stripe_even": "#2d2d2d" if is_dark else "#f9f9f9",
		}

		# Windows Title Bar Dark Mode
		if sys.platform == "win32":
			try:
				# DWMWA_USE_IMMERSIVE_DARK_MODE = 20
				value = 1 if is_dark else 0
				hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
				if hwnd == 0: hwnd = self.root.winfo_id()

				ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(ctypes.c_int(value)), 4)
			except Exception:
				pass

		# --- Apply to root and standard tk widgets ---
		self.root.config(bg=c["bg"])
		self.paned_window.config(bg=c["bg_pane"])
		self.top_pane.config(bg=c["bg_pane"])

		if self.find_window and self.find_window.winfo_exists():
			self.find_window.config(bg=c["bg"])

		# Log View
		self.text_area.config(bg=c["bg_widget"], fg=c["fg_widget"], insertbackground=c["fg_widget"])
		self.line_number_area.config(bg=c["bg_line_num"], fg=c["fg_line_num"])
		self.welcome_label.config(bg=c["bg_widget"], fg=c["fg_disabled"])

		self.marker_canvas.config(bg=c["bg_line_num"]) # Match line number bg or scrollbar track
		# --- Apply to ttk Styles ---
		style = ttk.Style(self.root)
		style.configure(".", background=c["bg"], foreground=c["fg"], fieldbackground=c["bg_widget"])
		style.map(".", background=[("disabled", c["bg_disabled"])], foreground=[("disabled", c["fg_disabled"])])

		style.configure("TFrame", background=c["bg"])
		style.configure("TLabel", background=c["bg"], foreground=c["fg"])
		style.configure("TButton", background=c["bg_widget"], foreground=c["fg"])
		style.map("TButton",
			background=[("active", c["bg_select"]), ("pressed", c["bg_select"])],
			foreground=[("active", c["fg_select"]), ("pressed", c["fg_select"])]
		)
		style.configure("TCheckbutton", background=c["bg"], foreground=c["fg"])
		style.map("TCheckbutton", background=[("active", c["bg"])])

		# Paned Window Sash
		style.configure("Sash", background=c["bg_pane"])

		# Scrollbars (Flat Modern Look)
		# Remove grip, border, and 3D relief for a clean look
		style.configure("Vertical.TScrollbar", gripcount=0, borderwidth=0, relief="flat",
						background=c["scrollbar_thumb"], darkcolor=c["scrollbar_bg"], lightcolor=c["scrollbar_bg"],
						troughcolor=c["scrollbar_bg"], bordercolor=c["scrollbar_bg"], arrowcolor=c["fg"])
		style.map("Vertical.TScrollbar", background=[("active", c["scrollbar_hover"]), ("pressed", c["bg_select"])])

		style.configure("Horizontal.TScrollbar", gripcount=0, borderwidth=0, relief="flat",
						background=c["scrollbar_thumb"], darkcolor=c["scrollbar_bg"], lightcolor=c["scrollbar_bg"],
						troughcolor=c["scrollbar_bg"], bordercolor=c["scrollbar_bg"], arrowcolor=c["fg"])
		style.map("Horizontal.TScrollbar", background=[("active", c["scrollbar_hover"]), ("pressed", c["bg_select"])])

		# Treeview
		style.configure("Treeview", background=c["bg_tree"], foreground=c["fg_tree"], fieldbackground=c["bg_tree"])
		style.map("Treeview", background=[("selected", c["bg_select"])], foreground=[("selected", c["fg_select"])])
		style.configure("Treeview.Heading", background=c["bg_head"], foreground=c["fg_head"])

		# Status Bar
		self.status_label.config(background=c["bg"], foreground=c["fg"])

		# Drop Indicator
		if self.drop_indicator:
			self.drop_indicator.config(bg=c["fg"])

		# Apply Stripes to Notes Treeview if it exists
		if hasattr(self, 'notes_tree') and self.notes_tree.winfo_exists():
			self.notes_tree.tag_configure("odd", background=c["stripe_odd"])
			self.notes_tree.tag_configure("even", background=c["stripe_even"])

		# Re-apply tag styles to update note color
		self.apply_tag_styles()
		self.render_viewport()

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
		self._add_to_recent_files(filepath) # Add to recent list
		t = threading.Thread(target=self._worker_load_log, args=(filepath,))
		t.daemon = True
		t.start()

	def _worker_load_log(self, filepath):
		try:
			t_start = time.time()
			file_size = os.path.getsize(filepath)

			lines = []
			rust_eng = None

			# Use Rust to load file (Zero-copy for Python)
			# We assume HAS_RUST is True or handled at startup
			rust_eng = log_engine_rs.LogEngine(filepath)
			lines = RustLinesProxy(rust_eng)

			t_end = time.time()
			self.msg_queue.put(('load_complete', lines, t_end - t_start, filepath, rust_eng))
		except Exception as e:
			self.msg_queue.put(('load_error', str(e)))

	def _load_log_from_path(self, filepath):
		if self.is_processing: return
		if not filepath or not os.path.exists(filepath): return

		self._add_to_recent_files(filepath) # Add to recent list
		self.set_ui_busy(True)
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
		self.recalc_filtered_data()

	def recalc_filtered_data(self):
		if self.is_processing: return
		if not self.is_processing: self.set_ui_busy(True)

		# We now rely solely on the Rust engine for filtering.
		# If rust_engine is not loaded (no file), we can't filter.
		if not self.rust_engine:
			self.refresh_filter_list()
			self.set_ui_busy(False)
			return

		# Start the Rust filter thread
		self._start_rust_filter_thread()

	def _start_rust_filter_thread(self):
		# Prepare filter data for Rust: List of (text, is_regex, is_exclude, is_event, original_idx)
		# Note: Rust expects this specific tuple structure
		rust_filters = []
		for i, f in enumerate(self.filters):
			if f.enabled:
				rust_filters.append((f.text, f.is_regex, f.is_exclude, f.is_event, i))

		def run_rust():
			try:
				t_start = time.time()
				# Call Rust
				# Returns: (tag_codes, filtered_indices, hit_counts, timeline_events) - matches dict is empty/removed
				tag_codes, filtered_indices, subset_counts, timeline_raw = self.rust_engine.filter(rust_filters)

				# Map subset counts back to full filter list
				full_counts = [0] * len(self.filters)
				for i, count in enumerate(subset_counts):
					if i < len(rust_filters):
						original_idx = rust_filters[i][4]
						full_counts[original_idx] = count

				# Convert tag_codes (u8) back to string tags for Python UI
				# 0 -> None, 1 -> 'EXCLUDED', 2+i -> 'filter_{i}'
				# We need to map the 'i' back to the original filter index from rust_filters

				# Create a map for fast lookup: code -> tag_string
				code_map = {0: None, 1: 'EXCLUDED'}
				for idx, (_, _, _, _, original_idx) in enumerate(rust_filters):
					code_map[2 + idx] = f"filter_{original_idx}"

				# Convert all tags (Fast list comprehension)
				line_tags = [code_map.get(c, None) for c in tag_codes]

				# Process timeline events
				# Rust returns (ts_str, filter_text, raw_idx)
				timeline_events_processed = []
				ts_formats = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%m/%d/%Y-%H:%M:%S.%f", "%I:%M:%S.%f %p", "%H:%M:%S"]

				for ts_str, f_text, r_idx in timeline_raw:
					for fmt in ts_formats:
						try:
							dt_obj = datetime.datetime.strptime(ts_str.split('.')[0] if "%f" not in fmt else ts_str, fmt)
							timeline_events_processed.append((dt_obj, f_text, r_idx))
							break
						except ValueError: continue

				t_end = time.time()
				self.msg_queue.put(('filter_complete', line_tags, filtered_indices, t_end - t_start, full_counts, {}, timeline_events_processed, bool(timeline_events_processed)))

			except Exception as e:
				self.msg_queue.put(('load_error', f"Rust Engine Error: {e}"))

		threading.Thread(target=run_rust, daemon=True).start()

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
		self._draw_search_markers() # Redraw markers as relative positions change
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
			self.text_area.tag_add("current_line", f"{ui_row}.0", f"{ui_row+1}.0")
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
		self._apply_icon(dialog)
		dialog.transient(self.root)
		dialog.grab_set()
		dialog.geometry("400x200")
		dialog.config(bg=self.root.cget("bg")) # Match theme

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

		txt_input = tk.Text(text_frame, wrap="word", font=("Consolas", 12), height=5)
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
				self._save_notes_window_geometry()
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
			self._apply_icon(self.notes_window)
			geom = self.config.get("notes_window_geometry", "400x500")
			self.notes_window.geometry(geom)
			self.notes_window.config(bg=self.root.cget("bg")) # Match theme
			self.notes_window.protocol("WM_DELETE_WINDOW", self.on_notes_window_close)

		# Re-create the widgets inside the Toplevel window
		self._create_notes_view_widgets(self.notes_window)
		self.refresh_notes_window()
		self.notes_window.lift()

	def dock_note_view(self):
		# Destroy the separate window if it exists
		if self.notes_window is not None and self.notes_window.winfo_exists():
			self._save_notes_window_geometry()
			self.notes_window.destroy()
			self.notes_window = None

		# Check if already docked to prevent duplicates
		if self.notes_frame and self.notes_frame.winfo_exists():
			self.refresh_notes_window()
			return

		# Re-create the frame and its widgets inside the main pane
		self.notes_frame = ttk.LabelFrame(self.top_pane, text="Notes")
		self._create_notes_view_widgets(self.notes_frame)

		# Calculate current available width for defaults or validation
		current_total_w = self.top_pane.winfo_width()
		if current_total_w <= 1: # Startup/Not realized
			current_total_w = 1000

		target_notes_w = int(current_total_w / 3)
		# Update Log View width to match the remaining 2/3 space.
		# This ensures Tkinter maintains the 2:1 ratio during window resizing.
		self.top_pane.paneconfigure(self.content_frame, width=current_total_w - target_notes_w)
		self.top_pane.add(self.notes_frame, minsize=200, width=target_notes_w, stretch="always")

		self.refresh_notes_window()

	def _save_notes_window_geometry(self):
		if self.notes_window and self.notes_window.winfo_exists():
			self.config["notes_window_geometry"] = self.notes_window.geometry()
			self.save_config()

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
		for i, idx in enumerate(sorted_indices):
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
			tag_stripe = "even" if i % 2 == 0 else "odd"
			self.notes_tree.insert("", "end", values=(line_num, timestamp_str, content), tags=(str(idx), tag_stripe))

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
					if not self.note_view_visible_var.get():
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

	def show_goto_dialog(self, event=None):
		"""Shows a dialog to jump to a specific line number."""
		if self.is_processing: return "break"

		total_lines = self.get_total_count()
		if total_lines == 0:
			self.update_status("No log file loaded to go to a line.")
			return "break"

		dialog = tk.Toplevel(self.root)
		dialog.title("Go to Line")
		self._apply_icon(dialog)
		dialog.transient(self.root)
		dialog.grab_set()
		dialog.geometry("300x120")
		dialog.resizable(False, False)
		dialog.config(bg=self.root.cget("bg")) # Match theme

		main_frame = ttk.Frame(dialog, padding=10)
		main_frame.pack(fill=tk.BOTH, expand=True)

		ttk.Label(main_frame, text=f"Enter line number (1 - {total_lines}):").pack(anchor="w")

		entry = ttk.Entry(main_frame)
		entry.pack(fill=tk.X, pady=5)
		entry.focus_set()

		def on_go():
			try:
				line_num = int(entry.get())
				if 1 <= line_num <= total_lines:
					dialog.destroy()
					# User input is 1-based, jump_to_line expects 0-based index
					self.jump_to_line(line_num - 1)
				else:
					messagebox.showerror("Invalid Line Number", f"Please enter a number between 1 and {total_lines}.", parent=dialog)
			except ValueError:
				messagebox.showerror("Invalid Input", "Please enter a valid number.", parent=dialog)

		button_frame = ttk.Frame(main_frame)
		button_frame.pack(fill=tk.X, side=tk.BOTTOM)
		ttk.Button(button_frame, text="Go", command=on_go).pack(side=tk.RIGHT)
		ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)

		entry.bind("<Return>", lambda e: on_go())
		dialog.bind("<Escape>", lambda e: dialog.destroy())
		return "break"

	# --- Timeline Window ---
	def show_timeline_window(self):
		if not self.timeline_events:
			messagebox.showinfo("Timeline", "No events found to display on the timeline.", parent=self.root)
			return

		if self.timeline_win and self.timeline_win.winfo_exists():
			self.timeline_win.lift() # Bring to front if already open
			return

		self.timeline_win = tk.Toplevel(self.root)
		self.timeline_win.title("Event Timeline")
		self._apply_icon(self.timeline_win)
		self.timeline_win.geometry("800x250")
		self.timeline_win.protocol("WM_DELETE_WINDOW", self._on_timeline_window_close)
		self.timeline_win.config(bg=self.root.cget('bg')) # Inherit theme

		# Canvas for drawing
		canvas = tk.Canvas(self.timeline_win, bg="white")
		canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

		# Store data directly on the window object to allow external updates
		self.timeline_win.sorted_events = sorted(self.timeline_events, key=lambda x: x[0])
		self.timeline_win.first_time = self.timeline_win.sorted_events[0][0]
		self.timeline_win.last_time = self.timeline_win.sorted_events[-1][0]
		total_duration = (self.timeline_win.last_time - self.timeline_win.first_time).total_seconds()
		if total_duration == 0: total_duration = 1 # Avoid division by zero

		# --- State for Zoom & Pan ---
		zoom_level = 1.0  # 1.0 = 100% zoom
		view_offset_seconds = 0.0 # Pan offset from the start

		# --- State for Panning ---
		pan_start_x = 0
		pan_start_offset = 0

		# Tooltip
		# --- Aesthetic Tooltip ---
		tooltip = ttk.Label(
			self.timeline_win, text="",
			background="#3C3C3C",      # Fixed dark background for visibility
			foreground="#FFFFFF",      # White text
			relief="flat",             # No border
			padding=(8, 5))            # Horizontal and vertical padding

		# Helper functions for coordinate conversion
		# Helper to convert a datetime object to an X coordinate
		def time_to_x(dt, width, margin, start_seconds, duration_seconds, first_time):
			if not dt or not first_time: return -1
			time_since_start = (dt - first_time).total_seconds()
			# Use a small tolerance (epsilon) for floating point comparisons at the edges
			epsilon = 1e-9
			if time_since_start < (start_seconds - epsilon) or time_since_start > (start_seconds + duration_seconds + epsilon):
				return -1 # Not in view, with tolerance

			relative_pos = (time_since_start - start_seconds) / duration_seconds
			return margin + relative_pos * (width - 2 * margin)

		# Helper to convert an X coordinate back to a time offset in seconds
		def x_to_time_offset(x_coord, width, margin, start_seconds, duration_seconds):
			if (width - 2 * margin) <= 0: return start_seconds
			relative_pos = (x_coord - margin) / (width - 2 * margin)
			return start_seconds + relative_pos * duration_seconds

		# Main drawing function
		def draw_timeline():
			canvas.delete("all")
			width = canvas.winfo_width()
			height = canvas.winfo_height()
			margin = 20
			y_axis = height - 30

			# Adapt canvas to theme
			is_dark = self.dark_mode.get()
			canvas_bg = "#2e2e2e" if is_dark else "white"
			axis_color = "#dcdcdc" if is_dark else "black"
			canvas.config(bg=canvas_bg)

			# Use data from the window object
			sorted_events = self.timeline_win.sorted_events
			first_time = self.timeline_win.first_time
			last_time = self.timeline_win.last_time
			if not sorted_events or not first_time or not last_time: return
			total_duration = (last_time - first_time).total_seconds()

			# --- Calculate visible time range based on zoom and pan ---
			visible_duration_seconds = total_duration / zoom_level
			start_time_seconds = view_offset_seconds
			end_time_seconds = start_time_seconds + visible_duration_seconds

			# Draw axis
			canvas.create_line(margin, y_axis, width - margin, y_axis, fill=axis_color)

			# Draw labels
			def format_time_with_ms(dt_obj):
				if dt_obj and dt_obj.microsecond > 0:
					return dt_obj.strftime("%H:%M:%S.%f")[:-3] # Trim to ms
				elif dt_obj:
					return dt_obj.strftime("%H:%M:%S")
				else:
					return ""
			canvas.create_text(margin, y_axis + 10, text=format_time_with_ms(first_time + datetime.timedelta(seconds=start_time_seconds)), anchor="w", fill=axis_color)
			canvas.create_text(width - margin, y_axis + 10, text=format_time_with_ms(first_time + datetime.timedelta(seconds=end_time_seconds)), anchor="e", fill=axis_color)

			# Store drawn items for hit-testing
			canvas.drawn_items = []

			# Draw events
			for dt, f_text, r_idx in sorted_events:
				time_offset = (dt - first_time).total_seconds()
				if time_offset < start_time_seconds or time_offset > end_time_seconds:
					continue # Skip events outside the current view
				x_pos = time_to_x(dt, width, margin, start_time_seconds, visible_duration_seconds, first_time)
				# Find the filter to get its color
				color = "#0078D7" # Default color
				for flt in self.filters:
					if flt.text == f_text:
						color = flt.back_color
						break

				item_id = canvas.create_oval(x_pos - 4, y_axis - 4, x_pos + 4, y_axis + 4, fill=color, outline="black")
				canvas.drawn_items.append({
					"id": item_id,
					"raw_index": r_idx,
					"datetime": dt,
					"filter_text": f_text
				})

		def on_resize(event):
			draw_timeline()

		def on_zoom(event):
			nonlocal zoom_level, view_offset_seconds

			# --- Zoom logic ---
			zoom_factor = 1.2 if event.delta > 0 else 1 / 1.2
			new_zoom_level = max(1.0, zoom_level * zoom_factor) # Don't zoom out past 100%

			# --- Zoom centered on cursor ---
			width = canvas.winfo_width()
			margin = 20
			# Time at cursor position before zoom
			time_at_cursor_before = x_to_time_offset(event.x, width, margin, view_offset_seconds, total_duration / zoom_level)

			# Update zoom level
			zoom_level = new_zoom_level

			# After zoom, the same time point should ideally be under the cursor.
			# We adjust the view_offset to achieve this.
			visible_duration_after = total_duration / zoom_level
			cursor_pos_fraction = (event.x - margin) / (width - 2 * margin)

			new_offset = time_at_cursor_before - (cursor_pos_fraction * visible_duration_after)

			# Clamp offset to valid range
			max_offset = total_duration - visible_duration_after
			view_offset_seconds = max(0.0, min(new_offset, max_offset))

			draw_timeline()
			# Stop the event from propagating to the parent window (e.g., main log view scroll)
			return "break"

		# Mouse motion for tooltips
		def on_motion(event):
			x, y = event.x, event.y
			canvas_width = canvas.winfo_width()
			found_item = None

			# Find the topmost item under the cursor
			for item in reversed(canvas.find_withtag("all")):
				coords = canvas.coords(item)
				if len(coords) == 4 and coords[0] <= x <= coords[2] and coords[1] <= y <= coords[3]:
					for drawn in canvas.drawn_items:
						if drawn["id"] == item:
							found_item = drawn; break
				if found_item: break

			if found_item:
				# 1. Construct tooltip text with timestamp
				dt_obj = found_item["datetime"]
				ts_str = dt_obj.strftime("%H:%M:%S.%f")[:-3] if dt_obj.microsecond > 0 else dt_obj.strftime("%H:%M:%S")
				tooltip_text = f"{ts_str}\nL{found_item['raw_index']+1}: {found_item['filter_text']}"
				tooltip.config(text=tooltip_text, justify=tk.LEFT)
				tooltip.update_idletasks() # Update geometry to get correct width

				# 2. Adjust position to prevent clipping
				tooltip_width = tooltip.winfo_width()
				place_x = x + 15
				if place_x + tooltip_width > canvas_width:
					place_x = x - tooltip_width - 10 # Place on the left

				tooltip.place(x=place_x, y=y + 10)
			else:
				tooltip.place_forget()

		# Panning start
		def on_pan_start(event):
			nonlocal pan_start_x, pan_start_offset
			pan_start_x = event.x
			pan_start_offset = view_offset_seconds
			canvas.config(cursor="fleur")

		def on_pan_drag(event):
			# Panning drag
			nonlocal view_offset_seconds
			dx = event.x - pan_start_x

			width = canvas.winfo_width()
			margin = 20
			# Convert pixel delta to time delta
			time_per_pixel = (total_duration / zoom_level) / (width - 2 * margin)
			time_delta = dx * time_per_pixel

			# Clamp new offset
			max_offset = total_duration - (total_duration / zoom_level)
			view_offset_seconds = max(0.0, min(pan_start_offset - time_delta, max_offset))
			draw_timeline()


		canvas.bind("<Configure>", on_resize)
		canvas.bind("<MouseWheel>", on_zoom) # For Windows/macOS trackpad
		canvas.bind("<Button-4>", on_zoom)   # For Linux scroll up
		canvas.bind("<Button-5>", on_zoom)   # For Linux scroll down
		canvas.bind("<Motion>", on_motion)
		canvas.bind("<ButtonPress-1>", on_pan_start)
		canvas.bind("<B1-Motion>", on_pan_drag)

		# We need a separate click handler for release, because B1-Motion captures the drag
		def on_pan_release(event):
			canvas.config(cursor="")
			# Check if it was a click (no drag)
			if abs(event.x - pan_start_x) < 3: # Click tolerance
				x, y = event.x, event.y
				found_item = None
				for item in reversed(canvas.find_withtag("all")):
					coords = canvas.coords(item)
					if len(coords) == 4 and coords[0] <= x <= coords[2] and coords[1] <= y <= coords[3]:
						for drawn in canvas.drawn_items:
							if drawn["id"] == item:
								found_item = drawn; break
					if found_item: break
				if found_item: self.jump_to_line(found_item["raw_index"])

		canvas.bind("<ButtonRelease-1>", on_pan_release)

		# Store the draw function for external calls
		self.timeline_draw_func = draw_timeline
		draw_timeline() # Initial draw

	def _on_timeline_window_close(self):
		self.timeline_win.destroy(); self.timeline_win = None; self.timeline_draw_func = None

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
			for tag in tags: self.text_area.tag_add(tag, f"{rel_idx}.0", f"{rel_idx+1}.0")

		# Highlight all search matches
		if self.last_search_query:
			query = self.last_search_query
			case_sensitive = self.last_search_case
			start_index = "1.0"
			while True:
				pos = self.text_area.search(query, start_index, stopindex=tk.END, nocase=not case_sensitive)
				if not pos: break
				end_pos = f"{pos}+{len(query)}c"
				self.text_area.tag_add("find_match_all", pos, end_pos)
				start_index = end_pos

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

				# Update Notes Treeview scaling
				style = ttk.Style(self.root)
				style.configure("Notes.Treeview", font=("Consolas", self.font_size), rowheight=int(max(20, self.font_size * 2.0)))

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
	def show_find_bar(self, event=None):
		"""Displays the find bar in a separate window."""
		if self.find_window and self.find_window.winfo_exists():
			self.find_window.lift()
			self.find_entry.focus_set()
			self.find_entry.select_range(0, tk.END)
			return "break"

		self.find_window = tk.Toplevel(self.root)
		self.find_window.title("Find")
		self._apply_icon(self.find_window)
		self.find_window.transient(self.root)
		self.find_window.resizable(False, False)
		self.find_window.protocol("WM_DELETE_WINDOW", self.close_find_bar)
		self.find_window.config(bg=self.root.cget("bg"))

		# Center relative to root
		rw = self.root.winfo_width()
		rh = self.root.winfo_height()
		rx = self.root.winfo_rootx()
		ry = self.root.winfo_rooty()
		w = 400; h = 80
		x = rx + (rw - w) // 2
		y = ry + (rh - h) // 2
		self.find_window.geometry(f"+{x}+{y}")

		frame = ttk.Frame(self.find_window, padding=5)
		frame.pack(fill=tk.BOTH, expand=True)

		ttk.Label(frame, text="Find:").pack(side=tk.LEFT, padx=(0, 5))
		self.find_entry = ttk.Entry(frame, width=25)
		self.find_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
		self.find_entry.bind("<Return>", self.on_find_confirm)
		if self.last_search_query:
			self.find_entry.insert(0, self.last_search_query)
			self.find_entry.select_range(0, tk.END)

		ttk.Button(frame, text="Find", command=self.on_find_confirm, width=6).pack(side=tk.LEFT, padx=2)

		ttk.Checkbutton(frame, text="Case", variable=self.find_case_var).pack(side=tk.LEFT, padx=(10, 0))
		ttk.Checkbutton(frame, text="Wrap", variable=self.find_wrap_var).pack(side=tk.LEFT, padx=(5, 0))

		self.find_entry.focus_set()
		return "break"

	def on_find_confirm(self, event=None):
		self._find(backward=False)
		if self.last_search_results:
			self.close_find_bar()
		return "break"

	def close_find_bar(self, event=None):
		"""Closes the find bar but keeps search highlights."""
		if self.find_window:
			self.find_window.destroy()
			self.find_window = None
			self.find_entry = None
		self.text_area.focus_set()
		return "break"

	def cancel_search(self, event=None):
		"""Clears search highlights and state."""
		if self.find_window:
			self.close_find_bar()

		# Clear highlights from the view
		self.text_area.tag_remove("find_match", "1.0", tk.END)
		self.text_area.tag_remove("find_match_all", "1.0", tk.END)

		# Clear search state to fully cancel the search
		if self.last_search_query:
			self.last_search_query = None
			self.last_search_results = None
			# A viewport refresh is needed to remove the 'find_match_all' tags
			self.render_viewport()

		self.marker_canvas.delete("all") # Clear markers
		return "break"

	def on_escape(self, event=None):
		if self.find_window and self.find_window.winfo_exists():
			self.close_find_bar()
		else:
			self.cancel_search()
		return "break"

	def _is_visible(self, raw_idx):
		"""Check if a raw line index is currently visible (not filtered out)."""
		if not self.show_only_filtered_var.get(): return True
		# Check if raw_idx is in filtered_indices (which is sorted)
		i = bisect.bisect_left(self.filtered_indices, raw_idx)
		if i != len(self.filtered_indices) and self.filtered_indices[i] == raw_idx:
			return True
		return False

	def _highlight_find_match(self, query, case_sensitive):
		"""Highlights the match in the currently visible text area."""
		# The jump_to_line has already positioned the view.
		# We search only the visible text widget content (fast).
		pos = self.text_area.search(query, "1.0", stopindex=tk.END, nocase=not case_sensitive)
		if pos:
			end_pos = f"{pos}+{len(query)}c"
			self.text_area.tag_add("find_match", pos, end_pos)

	def _draw_search_markers(self):
		self.marker_canvas.delete("all")
		if not self.last_search_results: return

		h = self.marker_canvas.winfo_height()
		if h <= 1: return

		show_filtered = self.show_only_filtered_var.get()
		total_view_items = self.get_total_count()
		if total_view_items == 0: return

		unique_y = set()
		color = "#FFA500" # Orange match color

		# Optimization: If too many results, sample them to avoid UI lag
		results = self.last_search_results
		limit = 5000
		step = 1
		if len(results) > limit:
			step = len(results) // limit

		if show_filtered:
			# Filtered mode: Need to map raw_idx -> view_idx
			# This is slower because of bisect, so sampling is important
			for i in range(0, len(results), step):
				raw_idx = results[i]
				# Check visibility
				idx = bisect.bisect_left(self.filtered_indices, raw_idx)
				if idx < len(self.filtered_indices) and self.filtered_indices[idx] == raw_idx:
					y = int((idx / total_view_items) * h)
					unique_y.add(y)
		else:
			# Full mode: raw_idx is directly useful
			total_raw = len(self.raw_lines)
			for i in range(0, len(results), step):
				raw_idx = results[i]
				y = int((raw_idx / total_raw) * h)
				unique_y.add(y)

		for y in unique_y:
			self.marker_canvas.create_line(0, y, 15, y, fill=color, width=1)

	def on_marker_resize(self, event):
		if self.last_search_results:
			self._draw_search_markers()

	def on_marker_click(self, event):
		h = self.marker_canvas.winfo_height()
		if h <= 0: return
		y = event.y
		ratio = y / h

		total = self.get_total_count()
		target_idx = int(total * ratio)

		# Scroll view to that position
		self.view_start_index = max(0, min(target_idx, total - self.visible_rows))
		self.render_viewport()
		self.update_scrollbar_thumb()

	def _find(self, backward=False):
		"""Core find logic."""
		query = None
		if self.find_entry and self.find_entry.winfo_exists():
			query = self.find_entry.get()
		elif self.last_search_query:
			query = self.last_search_query

		if not query: return

		case_sensitive = self.find_case_var.get()

		# 1. Perform Search (if query changed or cache missing)
		if (query != self.last_search_query or
			case_sensitive != self.last_search_case or
			self.last_search_results is None):

			self.set_ui_busy(True)
			try:
				if self.rust_engine:
					# Call Rust: search(query, is_regex, case_sensitive)
					# Note: UI Find bar currently assumes text search (is_regex=False)
					self.last_search_results = self.rust_engine.search(query, False, case_sensitive)
				else:
					self.last_search_results = []

				self.last_search_query = query
				self.last_search_case = case_sensitive
				self._draw_search_markers() # Draw markers on new search
			except Exception as e:
				print(f"Search error: {e}")
				self.last_search_results = []
			finally:
				self.set_ui_busy(False)

		if not self.last_search_results:
			self.find_entry.config(foreground="red")
			self.update_status("No matches found.")
			return

		# 2. Navigate to Next/Prev Match
		# Find current position in the sorted results
		curr = self.selected_raw_index
		if backward:
			idx = bisect.bisect_left(self.last_search_results, curr)
		else:
			idx = bisect.bisect_right(self.last_search_results, curr)

		matches = self.last_search_results
		count = len(matches)
		target_raw_index = -1
		found = False

		# Generate candidates based on direction and wrapping
		candidates = []
		if backward:
			# From idx-1 down to 0, then wrap if needed
			candidates = range(idx - 1, -1, -1)
			if self.find_wrap_var.get():
				candidates = list(candidates) + list(range(count - 1, idx - 1, -1))
		else:
			# From idx up to end, then wrap if needed
			candidates = range(idx, count)
			if self.find_wrap_var.get():
				candidates = list(candidates) + list(range(0, idx))

		# Find the first candidate that is visible
		for i in candidates:
			raw_idx = matches[i]
			if self._is_visible(raw_idx):
				target_raw_index = raw_idx
				found = True
				break

		if found:
			self.jump_to_line(target_raw_index)
			if self.find_entry and self.find_entry.winfo_exists():
				self.find_entry.config(foreground="black")
			self.update_status(f"Found match on line {target_raw_index + 1}")

			# Schedule highlight (UI update needs a moment after jump)
			self.text_area.tag_remove("find_match", "1.0", tk.END)
			self.root.after(50, lambda: self._highlight_find_match(query, case_sensitive))
		else:
			if self.find_entry and self.find_entry.winfo_exists():
				self.find_entry.config(foreground="black")
			# Use red text if wrapped and still not found (e.g. filtered out)
			if self.show_only_filtered_var.get():
				if self.find_entry and self.find_entry.winfo_exists():
					self.find_entry.config(foreground="red")
				self.update_status("Match found but hidden by filters.")
			else:
				if self.find_entry and self.find_entry.winfo_exists():
					self.find_entry.config(foreground="red")
				self.update_status("No more matches found.")

	def find_next(self, event=None): self._find(backward=False); return "break"
	def find_previous(self, event=None): self._find(backward=True); return "break"

	def refresh_filter_list(self):
		for item in self.tree.get_children(): self.tree.delete(item)
		is_dark = self.dark_mode.get()
		for idx, flt in enumerate(self.filters):
			en_str = "☑" if flt.enabled else "☐"
			type_str = "Excl" if flt.is_exclude else ("Regex" if flt.is_regex else "Text")
			event_str = "✓" if flt.is_event else ""
			item_id = self.tree.insert("", "end", values=(en_str, type_str, flt.text, str(flt.hit_count), event_str))
			tag_name = f"row_{idx}"
			self.tree.item(item_id, tags=(tag_name,))

			fg = adjust_color_for_theme(flt.fore_color, False, is_dark)
			bg = adjust_color_for_theme(flt.back_color, True, is_dark)
			self.tree.tag_configure(tag_name, foreground=fg, background=bg)

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

	def on_tree_drag_motion(self, event):
		if self.drag_start_index is None: return
		target_id = self.tree.identify_row(event.y)

		if not target_id:
			self.drop_indicator.place_forget()
			self.drag_target_id = None
			return

		bbox = self.tree.bbox(target_id)
		if not bbox: return

		# bbox = (x, y, width, height)
		y, h = bbox[1], bbox[3]

		# Determine if we are in the top half or bottom half
		if event.y < y + h / 2:
			self.drag_position = 'before'
			y_line = y
		else:
			self.drag_position = 'after'
			y_line = y + h

		self.drop_indicator.place(x=0, y=y_line, width=self.tree.winfo_width(), height=2)
		self.drop_indicator.lift()
		self.drag_target_id = target_id

	def on_tree_release(self, event):
		self.drop_indicator.place_forget()
		if self.is_processing: return
		if self.drag_start_index is None: return

		if self.drag_target_id:
			start_idx = self.drag_start_index
			target_idx = self.tree.index(self.drag_target_id)

			if self.drag_position == 'after':
				target_idx += 1

			# Adjust index if moving downwards
			if target_idx > start_idx:
				target_idx -= 1

			if start_idx != target_idx:
				item = self.filters.pop(self.drag_start_index)
				self.filters.insert(target_idx, item)
				self.recalc_filtered_data() # Order changed, must full recalc
		self.drag_start_index = None
		self.drag_target_id = None

	def on_tree_right_click(self, event):
		item_id = self.tree.identify_row(event.y)
		if item_id:
			if item_id not in self.tree.selection():
				self.tree.selection_set(item_id)
			# Update the context menu's checkbutton state based on the selected filter
			idx = self.tree.index(item_id)
			self.event_menu_var.set(self.filters[idx].is_event)
			self.context_menu.entryconfig("Set as Event", state="normal")
			self.context_menu.entryconfig("Remove Filter", state="normal")
			self.context_menu.entryconfig("Edit Filter", state="normal")
			self.context_menu.entryconfig("Move to Top", state="normal")
			self.context_menu.entryconfig("Move to Bottom", state="normal")
		else:
			self.tree.selection_remove(self.tree.selection())
			self.context_menu.entryconfig("Set as Event", state="disabled")
			self.context_menu.entryconfig("Remove Filter", state="disabled")
			self.context_menu.entryconfig("Edit Filter", state="disabled")
			self.context_menu.entryconfig("Move to Top", state="disabled")
			self.context_menu.entryconfig("Move to Bottom", state="disabled")
		self.context_menu.post(event.x_root, event.y_root)

	def toggle_selected_filters_as_event(self):
		if self.is_processing: return
		selected_items = self.tree.selection()
		if not selected_items: return

		new_state = self.event_menu_var.get()
		for item_id in selected_items:
			idx = self.tree.index(item_id)
			self.filters[idx].is_event = new_state
		self.recalc_filtered_data()

	def move_filter_to_top(self):
		if self.is_processing: return
		selected_items = self.tree.selection()
		if not selected_items: return

		indices = sorted([self.tree.index(item) for item in selected_items])
		items_to_move = []
		# Remove in reverse order to keep indices valid
		for idx in reversed(indices):
			items_to_move.insert(0, self.filters.pop(idx))

		# Insert at top
		for item in reversed(items_to_move):
			self.filters.insert(0, item)
		self.recalc_filtered_data()

	def move_filter_to_bottom(self):
		if self.is_processing: return
		selected_items = self.tree.selection()
		if not selected_items: return

		indices = sorted([self.tree.index(item) for item in selected_items])
		items_to_move = []
		for idx in reversed(indices):
			items_to_move.insert(0, self.filters.pop(idx))

		# Append to bottom
		self.filters.extend(items_to_move)
		self.recalc_filtered_data()

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
		self._apply_icon(dialog)
		dialog.transient(self.root) # Make it a child of the main window
		dialog.grab_set()
		dialog.geometry("400x200")
		dialog.config(bg=self.root.cget("bg")) # Match theme

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
		var_event = tk.BooleanVar(value=filter_obj.is_event if filter_obj else False)
		ttk.Checkbutton(options_frame, text="Regex", variable=var_regex).pack(side=tk.LEFT)
		ttk.Checkbutton(options_frame, text="Exclude", variable=var_exclude).pack(side=tk.LEFT, padx=10)
		ttk.Checkbutton(options_frame, text="As Event", variable=var_event).pack(side=tk.LEFT, padx=10)

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
				filter_obj.is_event = var_event.get()
				self.recalc_filtered_data()
			else:
				new_filter = Filter(text, colors["fg"], colors["bg"], enabled=True, is_regex=var_regex.get(), is_exclude=var_exclude.get(), is_event=var_event.get())
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
				if flt.is_event: f_node.set("is_event", "y") # Add our custom attribute
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
			if self._write_tat_file(self.current_tat_path): self.show_toast("Filters saved successfully")
		else: self.save_as_tat_filters()

	def save_as_tat_filters(self):
		if self.is_processing: return
		init_dir = self.config.get("last_filter_dir", ".")
		filepath = filedialog.asksaveasfilename(initialdir=init_dir, defaultextension=".tat", filetypes=[("TextAnalysisTool", "*.tat"), ("XML", "*.xml")])
		if not filepath: return
		self.config["last_filter_dir"] = os.path.dirname(filepath); self.save_config()
		if self._write_tat_file(filepath):
			self.current_tat_path = filepath; self.update_title()
			self.show_toast("Filters saved successfully")

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
				is_event = is_true(f.get('is_event')) # Read our custom attribute, defaults to False if not found
				if text: new_filters.append(Filter(text, fore, back, enabled, is_regex, is_exclude, is_event=is_event))
			self.filters = new_filters
			self.current_tat_path = filepath; self.update_title()
			self.recalc_filtered_data()
			self.show_toast(f"Imported {len(new_filters)} filters")
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
			self.recalc_filtered_data()
		except Exception as e: messagebox.showerror("Error", f"JSON Import Failed: {e}")

if __name__ == "__main__":
	if HAS_DND:
		root = TkinterDnD.Tk()
	else:
		root = tk.Tk()
	app = LogAnalyzerApp(root)
	root.mainloop()