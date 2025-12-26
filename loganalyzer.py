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
		self.hit_count = 0 # Added for multi-log

	def to_dict(self): # Added for multi-log to save/load filter state
		return {
			"text": self.text,
			"fore_color": self.fore_color,
			"back_color": self.back_color,
			"enabled": self.enabled,
			"is_regex": self.is_regex,
			"is_exclude": self.is_exclude,
			"is_event": self.is_event
		}

class LogFileState:
	def __init__(self, filepath, raw_lines, rust_engine):
		self.filepath = filepath
		self.raw_lines = raw_lines
		self.rust_engine = rust_engine
		self.all_line_tags = None # Initialize to None
		self.filtered_indices = []
		self.timeline_events = []
		self.timeline_events_by_time = [] # Sorted by time
		self.timeline_events_by_index = [] # Sorted by raw_index
		self.timestamps_found = False
		self.filter_hit_counts = [0] * len(self.raw_lines) # Needs to be updated based on filters.
		# For multi-log, each LogFileState will need its own filtered_cache and timeline_events
		# when it's not the active one.
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
		if idx < 0 or idx >= len(self):
			raise IndexError("Index out of bounds")
		return self.engine.get_line(idx)

class LogAnalyzerApp:
	MERGED_VIEW_ID = "MERGED_VIEW_ID" # Constant for merged view
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
		style.configure("LogFiles.Treeview", font=("Consolas", 9), rowheight=20, indent=0)

		style.configure("TLabelFrame", padding=5)
		style.configure("TLabelFrame.Label", font=("Consolas", 10, "bold"))

		style.configure("TButton", padding=4, font=("Consolas", 10))

		style.configure("TLabel", font=("Consolas", 12))
		style.configure("TCheckbutton", font=("Consolas", 12))
		style.configure("TEntry", font=("Consolas", 12))
		style.configure("TProgressbar", thickness=15)

		# App Info
		self.APP_NAME = "Log Analyzer"
		self.VERSION = "V1.7"

		if not HAS_RUST:
			# Since we are removing Python fallbacks, we must warn the user if the engine is missing.
			messagebox.showerror("Error", "Rust extension (log_engine_rs) not found.\nPlease build the extension to use this application.")


		# Threading & Queue
		self.msg_queue = queue.Queue()
		self.is_processing = False
		self.pending_load_count = 0

		self.dark_mode = tk.BooleanVar(value=self.config.get("dark_mode", False))
		self.log_files_panel_visible = tk.BooleanVar(value=False) # Sidebar visibility state

		self.filters = [] # Store filter definitions
		self.filters_dirty = False # Track if filters have unsaved changes

		# --- Multi-Log Management ---
		self.loaded_log_files = {} # {filepath: LogFileState instance}
		self.currently_loading = set() # Track files being loaded to avoid duplicates
		self.has_active_log_been_set = False # New flag to track if an active log has been set
		self.active_log_filepath = None # Key for the currently displayed LogFileState, or special value for merged view.
		self.merged_log_data = None # Special LogFileState for merged view

		# --- Active View Proxy ---
		# These will point to the relevant properties of the active LogFileState (or merged)
		self.active_raw_lines = []
		self.active_rust_engine = None
		self.active_filtered_indices = []
		self.active_timeline_events = []
		self.active_timeline_events_by_time = []
		self.active_timeline_events_by_index = []
		self.active_timestamps_found = False

		# Filtered cache is specific to the active view
		self.filtered_cache = None

		# Store result of regex scan for ALL lines
		self.active_all_line_tags = []

		self.current_log_path = None # The path of the primary active log

		# Search Cache
		self.last_search_query = None
		self.last_search_results = None # List of raw indices from Rust
		self.last_search_case = False

		self.current_tat_path = None

		# Notes System
		# Notes are global, but context-aware. Maybe tie them to raw_index regardless of file.
		self.notes = {}  # { (filepath, raw_index): note_text (str) }
		self.notes_window = None

		# Timeline System
		# Timeline state is now driven by active_timeline_events

		# Timeline Zoom/Pan State
		self.timeline_zoom = 1.0
		self.timeline_view_offset = 0.0 # Seconds from start
		self.timeline_pan_start_x = 0
		self.timeline_pan_start_offset = 0.0

		self.view_start_index = 0
		self.visible_rows = 50

		# Font management
		self.font_size = self.config.get("font_size", 12)
		self.font_object = tkFont.Font(family="Consolas", size=self.font_size)
		self.small_font_object = tkFont.Font(family="Consolas", size=9) # For sidebar measurement

		# Dynamic Style for Notes (Scalable)
		style.configure("Notes.Treeview", font=("Consolas", self.font_size), rowheight=int(max(20, self.font_size * 2.0)))
		style.configure("Notes.Treeview.Heading", font=("Consolas", 12, "bold")) # Headings stay fixed or scalable? Let's keep headings fixed 12 for consistency with UI

		self.selected_raw_index = -1
		self.selected_indices = set() # Set of raw indices for multi-selection
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
		self.file_menu.add_command(label="Open Multiple Logs...", command=self.load_multiple_logs)
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
		self.view_menu.add_checkbutton(label="Show Log List", variable=self.log_files_panel_visible, command=self.toggle_log_panel)
		self.view_menu.add_separator()
		self.view_menu.add_command(label="Toggle Timeline", command=self.toggle_timeline_pane, state="disabled")


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

		# 3. Main Content Area (PanedWindow) - Vertical Split
		self.paned_window = tk.PanedWindow(root, orient=tk.VERTICAL, sashwidth=4, sashrelief=tk.FLAT, bg="#d9d9d9")
		self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

		# --- Top Horizontal Pane: Log Files List | Log View + Note View ---
		self.top_horizontal_pane = tk.PanedWindow(self.paned_window, orient=tk.HORIZONTAL, sashwidth=4, sashrelief=tk.FLAT, bg="#d9d9d9")

		# --- Left Side: Log Files List Panel ---
		self.log_files_panel = ttk.Frame(self.top_horizontal_pane)

		# Inner container for Tree + Scrollbar
		tree_frame = ttk.Frame(self.log_files_panel)
		tree_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

		self.log_files_tree = ttk.Treeview(tree_frame, columns=("file",), show="headings", selectmode="browse", style="LogFiles.Treeview")
		self.log_files_tree.heading("file", text="File List")
		self.log_files_tree.column("file", anchor="w", width=150)
		self.log_files_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
		self.log_files_tree.bind("<<TreeviewSelect>>", self.on_log_file_select)
		self.log_files_tree.bind("<Button-3>", self.on_log_files_right_click)

		# Context Menu for Log Files
		self.log_files_context_menu = tk.Menu(self.root, tearoff=0)
		self.log_files_context_menu.add_command(label="Remove", command=self.remove_selected_log)
		self.log_files_context_menu.add_separator()
		self.log_files_context_menu.add_command(label="Clear All Logs", command=self._clear_all_logs)

		# Scrollbar for log files tree (attached to tree_frame)
		self.log_files_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.log_files_tree.yview)
		self.log_files_scroll.pack(side=tk.RIGHT, fill=tk.Y)
		self.log_files_tree.configure(yscrollcommand=self.log_files_scroll.set)

		# --- Right Side: Main Log View + Note View --- (This is the existing 'top_pane' logic)
		top_pane = tk.PanedWindow(self.top_horizontal_pane, orient=tk.HORIZONTAL, sashwidth=4, sashrelief=tk.FLAT, bg="#d9d9d9")

		# --- Upper-Left (within top_pane): Log View ---
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
		self.text_area.bind("<Control-c>", self.copy_selection)
		self.text_area.bind("<Control-C>", self.copy_selection)
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
		self.find_history = [] # Store up to 10 search queries
		self.find_case_var = tk.BooleanVar(value=False)
		self.find_wrap_var = tk.BooleanVar(value=True)

		self.root.bind("<Control-Left>", self.on_nav_prev_match)
		self.root.bind("<Control-Right>", self.on_nav_next_match)

		top_pane.add(self.content_frame, width=750, minsize=300, stretch="always")

		# --- Upper-Right (within top_pane): Note View (Placeholder) ---
		# The actual notes_frame will be created dynamically
		self.notes_frame = None
		self.top_pane = top_pane # Store reference to the inner top_pane

		# Initial setup: Hide the notes view by default
		self.toggle_note_view_visibility(initial_setup=True)

		self.top_horizontal_pane.add(top_pane, stretch="always") # Add the existing top_pane to the new horizontal pane
		self.paned_window.add(self.top_horizontal_pane, stretch="always") # Add the new horizontal pane to the main vertical pane

		# Context Menu for Notes Tree
		self.notes_context_menu = tk.Menu(self.root, tearoff=0)
		self.notes_context_menu.add_command(label="Edit Note", command=self.edit_note_from_tree)
		self.notes_context_menu.add_command(label="Remove Note", command=self.remove_note_from_tree)

		# Context Menu for Log View
		self.log_context_menu = tk.Menu(self.root, tearoff=0)
		self.log_context_menu.add_command(label="Copy", command=self.copy_selection)
		self.log_context_menu.add_separator()
		self.log_context_menu.add_command(label="Add/Edit Note", command=self.add_note_dialog)
		self.log_context_menu.add_command(label="Remove Note", command=self.remove_note)

		# --- Middle: Timeline View ---
		self.timeline_frame = ttk.Frame(self.paned_window)
		self.timeline_canvas = tk.Canvas(self.timeline_frame, bg="#ffffff", height=60, cursor="hand2")
		self.timeline_canvas.pack(fill=tk.BOTH, expand=True)
		self.timeline_canvas.bind("<Configure>", self.on_timeline_resize)
		self.timeline_canvas.bind("<Button-1>", self.on_timeline_click)
		self.timeline_canvas.bind("<B1-Motion>", self.on_timeline_drag)
		self.timeline_canvas.bind("<Motion>", self.on_timeline_motion)
		self.timeline_canvas.bind("<MouseWheel>", self.on_timeline_zoom)
		self.timeline_canvas.bind("<Button-4>", self.on_timeline_zoom)
		self.timeline_canvas.bind("<Button-5>", self.on_timeline_zoom)
		self.timeline_canvas.bind("<ButtonPress-3>", self.on_timeline_pan_start)
		self.timeline_canvas.bind("<B3-Motion>", self.on_timeline_pan_drag)
		self.timeline_canvas.bind("<ButtonRelease-3>", self.on_timeline_pan_release)

		self.timeline_tooltip = ttk.Label(self.root, text="", background="#333333", foreground="#ffffff", relief="solid", borderwidth=1, padding=(5, 2))

		self.paned_window.add(self.timeline_frame, minsize=40, height=60, stretch="never")

		# Hide timeline pane by default on startup
		self.paned_window.forget(self.timeline_frame)

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

		self._apply_theme()
		self._update_recent_files_menu()

		# Initial Sidebar State: Hidden by default
		self.toggle_log_panel()

		self.root.bind("<Configure>", self.on_root_configure)
		self.root.protocol("WM_DELETE_WINDOW", self.on_close)
		self.root.after(200, self._restore_layout)

	def toggle_log_panel(self):
		"""Toggles the visibility of the log files list panel with auto-width and dynamic scrollbar."""
		if self.log_files_panel_visible.get():
			# 1. Calculate required width based on longest filename
			max_w = 100 # Minimum width
			for fp in self.loaded_log_files.keys():
				name = os.path.basename(fp)
				text_w = self.small_font_object.measure(name)
				if text_w > max_w: max_w = text_w

			# Add buffer for scrollbar (approx 20px) + padding (20px) = 40px
			final_w = min(450, max_w + 40)

			# 2. Update Column Width (for 'file' column in headings mode)
			self.log_files_tree.column("file", width=final_w)

			# 3. Dynamic Scrollbar: Only show if items exceed a reasonable count (e.g., 10)
			# (Or more accurately, compare with panel height if realized)
			if len(self.loaded_log_files) > 15: # Threshold for showing scrollbar
				self.log_files_scroll.pack(side=tk.RIGHT, fill=tk.Y)
			else:
				self.log_files_scroll.pack_forget()

			# Show panel
			try:
				self.top_horizontal_pane.add(self.log_files_panel, before=self.top_pane, width=final_w, minsize=50, stretch="never")
			except Exception: pass
		else:
			# Hide
			try:
				self.top_horizontal_pane.forget(self.log_files_panel)
			except Exception: pass

	def _decrement_pending_load_count(self):
		if hasattr(self, 'pending_load_count'):
			self.pending_load_count -= 1
			if self.pending_load_count <= 0:
				self.pending_load_count = 0
				self.set_ui_busy(False)
				self.update_status("All files loaded.")
		else:
			# Fallback if counter not initialized
			self.set_ui_busy(False)

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
		# --- Check for Unsaved Filter Changes ---
		if self.filters_dirty and self.filters:
			ans = messagebox.askyesnocancel("Unsaved Changes", "Your filters have been modified.\n\nDo you want to save the changes before exiting?")
			if ans is True: # Yes: Save and close
				if self.current_tat_path:
					if not self._write_tat_file(self.current_tat_path):
						return # Save failed, stay open
				else:
					# Save As...
					init_dir = self.config.get("last_filter_dir", ".")
					filepath = filedialog.asksaveasfilename(initialdir=init_dir, defaultextension=".tat", filetypes=[("TextAnalysisTool", "*.tat"), ("XML", "*.xml")])
					if filepath:
						if self._write_tat_file(filepath):
							self.current_tat_path = filepath
						else:
							return # Save failed
					else:
						return # Cancelled Save As dialog
			elif ans is None: # Cancel: Don't close
				return
			# Else (ans is False): Discard and close (fall through)

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

	def center_window(self, window, width, height):
		"""Centers a Toplevel window relative to the main root window."""
		window.withdraw() # Hide initially to avoid flicker
		window.update_idletasks() # Ensure geometry calculation is ready

		rw = self.root.winfo_width()
		rh = self.root.winfo_height()
		rx = self.root.winfo_rootx()
		ry = self.root.winfo_rooty()

		x = rx + (rw - width) // 2
		y = ry + (rh - height) // 2
		
		window.geometry(f"{width}x{height}+{x}+{y}")
		window.deiconify() # Show after positioning


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

		win.bind("<Escape>", lambda e: win.destroy())
		win.focus_set()

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
					log_state, duration = msg[1], msg[2]
					self.loaded_log_files[log_state.filepath] = log_state
					self.currently_loading.discard(log_state.filepath)
					self.merged_log_data = None # Invalidate merged data

					# 1. Get all loaded files and their start times for sorting the list
					ts_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?|\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+|\b\d{1,2}:\d{2}:\d{2}\.\d+\s+(?:AM|PM)\b|\b\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\b)')

					file_info = []
					for fp, state in self.loaded_log_files.items():
						start_ts = "9999" # Default for no timestamp
						first_line = state.rust_engine.get_line(0)
						match = ts_pattern.search(first_line)
						if match: start_ts = match.group(1)
						file_info.append((start_ts, fp))

					# Sort by start timestamp
					file_info.sort()

					# 2. Update Treeview order
					# Remove existing
					for item in self.log_files_tree.get_children():
						self.log_files_tree.delete(item)

					# Re-insert in sorted order
					if len(self.loaded_log_files) > 1:
						self.log_files_tree.insert("", 0, iid=self.MERGED_VIEW_ID, values=("[ Merged View ]",))

					for _, fp in file_info:
						self.log_files_tree.insert("", "end", iid=fp, values=(os.path.basename(fp),))

					# Update panel width and scrollbar if visible
					if self.log_files_panel_visible.get():
						self.toggle_log_panel()

					# Restore selection if active log exists
					if self.active_log_filepath:
						if self.log_files_tree.exists(self.active_log_filepath):
							self.log_files_tree.selection_set(self.active_log_filepath)

					if not self.has_active_log_been_set:
						self._set_active_log_state(log_state.filepath, load_duration=duration)
						self.has_active_log_been_set = True

					self.check_and_import_notes(log_state.filepath) # Auto-check for notes on load

					self.refresh_notes_window()
					self._decrement_pending_load_count()

					# Auto-show log list if more than 1 file is loaded
					if len(self.loaded_log_files) > 1 and not self.log_files_panel_visible.get():
						self.log_files_panel_visible.set(True)
						self.toggle_log_panel()
					elif len(self.loaded_log_files) <= 1 and self.log_files_panel_visible.get():
						self.log_files_panel_visible.set(False)
						self.toggle_log_panel()

				elif msg_type == 'load_error':
					err_msg = msg[1]
					messagebox.showerror("Load Error", err_msg)
					self.update_status("Load failed")
					self._decrement_pending_load_count()

				elif msg_type == 'filter_complete':
					line_tags, filtered_idx, duration, counts, source_filepath, timeline_events_processed, timestamps_found = msg[1], msg[2], msg[3], msg[4], msg[5], msg[6], msg[7]

					if source_filepath not in self.loaded_log_files: return

					log_state = self.loaded_log_files[source_filepath]
					log_state.all_line_tags = line_tags
					log_state.filtered_indices = filtered_idx
					log_state.filter_hit_counts = counts
					log_state.timeline_events = timeline_events_processed
					log_state.timestamps_found = timestamps_found
					self._update_timeline_data(log_state)

					# Check if we are aggregating for Merged View
					self.pending_filter_count -= 1

					if self.pending_filter_count <= 0:
						self.pending_filter_count = 0

						# Update overall filter duration
						if hasattr(self, 'filter_op_start_time'):
							total_duration = time.time() - self.filter_op_start_time
							self.filter_duration_str = f"{total_duration:.4f}s"

						if self.active_log_filepath == self.MERGED_VIEW_ID:
							self._aggregate_merged_filter_results()
						elif self.active_log_filepath == source_filepath:
							# Single file active, update UI normally
							self.active_all_line_tags = log_state.all_line_tags
							self.active_filtered_indices = log_state.filtered_indices
							self.active_timeline_events = log_state.timeline_events
							self.active_timeline_events_by_time = log_state.timeline_events_by_time
							self.active_timeline_events_by_index = log_state.timeline_events_by_index
							self.active_timestamps_found = log_state.timestamps_found

							for i, count in enumerate(self.filters):
								if i < len(log_state.filter_hit_counts):
									count.hit_count = log_state.filter_hit_counts[i]

							self.apply_tag_styles()
							self.refresh_filter_list()
							self.refresh_view_fast()
							self.draw_timeline()
							self.view_menu.entryconfig("Toggle Timeline", state="normal" if log_state.timestamps_found else "disabled")

						self.set_ui_busy(False)

				elif msg_type == 'status':
					self.update_status(msg[1])

				elif msg_type == 'merge_complete':
					merged_state, duration = msg[1], msg[2]
					self.merged_log_data = merged_state

					self.update_status(f"Merged View built in {duration:.4f}s")
					self.set_ui_busy(False) # Unblock UI before setting active state so recalc can run

					# Now that data is ready, set it as active
					self._set_active_log_state(self.MERGED_VIEW_ID, load_duration=duration)

		except queue.Empty:
			pass
		finally:
			self.root.after(100, self.check_queue)

	# --- Toast Notifications ---
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

		# Redraw timeline to apply theme changes
		self.draw_timeline()

		# Re-apply tag styles to update note color
		self.apply_tag_styles()
		self.render_viewport()

	# --- Title Update ---
	def update_title(self):
		log_name = os.path.basename(self.active_log_filepath) if self.active_log_filepath else "No file load"
		filter_name = os.path.basename(self.current_tat_path) if self.current_tat_path else "No filter file"
		self.root.title(f"[{log_name}] - [{filter_name}] - {self.APP_NAME} {self.VERSION}")

	# --- [Data Access Helpers] ---
	def get_total_count(self):
		if self.show_only_filtered_var.get():
			return len(self.active_filtered_indices)
		return len(self.active_raw_lines)

	def get_view_item(self, index):
		"""Returns (line, tags, raw_index) for the given index in the current view."""
		if self.show_only_filtered_var.get():
			if not self.active_filtered_indices: return "", [], -1
			raw_idx = self.active_filtered_indices[index]
		else:
			raw_idx = index

		if 0 <= raw_idx < len(self.active_raw_lines):
			line = self.active_raw_lines[raw_idx]
			tags = []
			if self.active_all_line_tags is not None:
				try:
					tag_val = self.active_all_line_tags[raw_idx]
					if tag_val and tag_val != 'EXCLUDED':
						tags.append(tag_val)
				except (IndexError, KeyError, TypeError):
					pass
			return line, tags, raw_idx
		return ("", [], -1)

	def _clear_all_logs(self):
		"""Clears all loaded logs and resets the UI state."""
		self.loaded_log_files.clear()
		self.notes.clear() # Clear all notes
		self.log_files_tree.delete(*self.log_files_tree.get_children())
		self.merged_log_data = None
		self.active_log_filepath = None
		self.has_active_log_been_set = False

		# Clear view proxies
		self.active_raw_lines = []
		self.active_rust_engine = None
		self.active_filtered_indices = []
		self.active_timeline_events = []
		self.active_timeline_events_by_time = []
		self.active_timeline_events_by_index = []
		self.active_timestamps_found = False

		self.selected_raw_index = -1
		self.selected_indices.clear()

		self.marker_canvas.delete("all")
		self.welcome_label.place(relx=0.5, rely=0.5, anchor="center")

		self.render_viewport() # Clear view
		self.refresh_notes_window() # Clear notes view
		self.update_title()
		self.update_status("Ready")

		# Clear timeline
		self.draw_timeline()

		# Hide log list panel on clear
		self.log_files_panel_visible.set(False)
		self.toggle_log_panel()

	def _aggregate_merged_filter_results(self):
		"""Aggregates filter results from all loaded files into the merged view state."""
		if not self.merged_log_data: return

		# 1. Sum hit counts
		total_hits = [0] * len(self.filters)
		for log_state in self.loaded_log_files.values():
			for i, count in enumerate(log_state.filter_hit_counts):
				if i < len(total_hits):
					total_hits[i] += count

		for i, flt in enumerate(self.filters):
			flt.hit_count = total_hits[i]

		self.merged_log_data.filter_hit_counts = total_hits

		# 2. Merge Filtered Indices and Timeline Events with Offsets
		merged_filtered_indices = []
		merged_timeline_events = []
		current_offset = 0

		# Use the pre-stored ordered file list
		for fp in self.merged_log_data.ordered_files:
			if fp not in self.loaded_log_files: continue
			log_state = self.loaded_log_files[fp]

			# Filtered Indices
			for local_idx in log_state.filtered_indices:
				merged_filtered_indices.append(current_offset + local_idx)

			for dt, text, local_raw_idx in log_state.timeline_events:
				merged_timeline_events.append((dt, text, current_offset + local_raw_idx))

			current_offset += len(log_state.raw_lines)

		# 3. Update Merged View State
		self.merged_log_data.filtered_indices = merged_filtered_indices
		self.merged_log_data.timeline_events = merged_timeline_events
		self._update_timeline_data(self.merged_log_data)
		self.merged_log_data.timestamps_found = bool(merged_timeline_events)

		# 4. Update UI Proxies
		self.active_all_line_tags = self.merged_log_data.all_line_tags # This is the MergedTagsProxy

		self.active_filtered_indices = self.merged_log_data.filtered_indices
		self.active_timeline_events = self.merged_log_data.timeline_events
		self.active_timeline_events_by_time = self.merged_log_data.timeline_events_by_time
		self.active_timeline_events_by_index = self.merged_log_data.timeline_events_by_index
		self.active_timestamps_found = self.merged_log_data.timestamps_found

		# 5. Refresh UI
		self.apply_tag_styles()
		self.refresh_filter_list()
		self.refresh_view_fast()
		self.draw_timeline()
		self.view_menu.entryconfig("Toggle Timeline", state="normal" if self.active_timestamps_found else "disabled")

	def _decrement_pending_load_count(self):
		if hasattr(self, 'pending_load_count'):
			self.pending_load_count -= 1
			if self.pending_load_count <= 0:
				self.pending_load_count = 0
				self.set_ui_busy(False)
				self.update_status("All files loaded.")
		else:
			self.set_ui_busy(False)

	# --- File Loading (Threaded) ---
	def load_log(self):
		if self.is_processing: return
		init_dir = self.config.get("last_log_dir", ".")
		filepath = filedialog.askopenfilename(initialdir=init_dir, filetypes=[("Log Files", "*.log *.txt"), ("All Files", "*.*")])
		if not filepath: return

		self.config["last_log_dir"] = os.path.dirname(filepath); self.save_config()

		# Single file mode: Clear existing logs first
		self._clear_all_logs()

		self.set_ui_busy(True)
		self.pending_load_count = 1
		self._load_log_file_into_state(filepath)

	def load_multiple_logs(self):
		if self.is_processing: return
		init_dir = self.config.get("last_log_dir", ".")
		filepaths = filedialog.askopenfilenames(initialdir=init_dir, filetypes=[("Log Files", "*.log *.txt"), ("All Files", "*.*")])
		if not filepaths: return

		self.config["last_log_dir"] = os.path.dirname(filepaths[0]); self.save_config()

		# Filter out duplicates (already loaded OR currently loading)
		new_filepaths = [fp for fp in filepaths if fp not in self.loaded_log_files and fp not in self.currently_loading]

		if not new_filepaths:
			self.update_status("No new files to load (duplicates ignored).")
			return

		self.set_ui_busy(True)
		self.pending_load_count += len(new_filepaths)

		# Load each new file
		for fp in new_filepaths:
			self.currently_loading.add(fp)
			self._load_log_file_into_state(fp)

	def _worker_load_log(self, filepath):
		try:
			t_start = time.time()
			rust_eng = log_engine_rs.LogEngine(filepath)
			lines = RustLinesProxy(rust_eng)
			log_state = LogFileState(filepath, lines, rust_eng)
			t_end = time.time()
			self.msg_queue.put(('load_complete', log_state, t_end - t_start))
		except Exception as e:
			self.msg_queue.put(('load_error', str(e), filepath))

	def _load_log_from_path(self, filepath):
		# Default to single file load behavior (replace)
		if filepath in self.loaded_log_files:
			self._set_active_log_state(filepath)
			return

		if filepath in self.currently_loading:
			return

		self._clear_all_logs()
		self.set_ui_busy(True)
		self.pending_load_count = 1
		self.currently_loading.add(filepath)
		self._load_log_file_into_state(filepath)

	def _load_log_file_into_state(self, filepath, is_initial_load=False):
		"""
		Initiates the loading of a single log file into a LogFileState object.
		"""
		if not filepath or not os.path.exists(filepath):
			if not is_initial_load:
				messagebox.showerror("File Error", f"Log file not found: {filepath}", parent=self.root)
			self._decrement_pending_load_count()
			return

		self._add_to_recent_files(filepath)
		t = threading.Thread(target=self._worker_load_log, args=(filepath,))
		t.daemon = True
		t.start()

	def on_drop(self, event):
		try:
			files = self.root.tk.splitlist(event.data)
			if not files: return

			if len(files) == 1:
				self._load_log_from_path(files[0])
			else:
				# Multiple files dropped: Add new ones
				new_filepaths = [fp for fp in files if fp not in self.loaded_log_files and fp not in self.currently_loading]
				if not new_filepaths:
					self.update_status("No new files to load (duplicates ignored).")
					return

				self.set_ui_busy(True)
				self.pending_load_count += len(new_filepaths)
				for fp in new_filepaths:
					self.currently_loading.add(fp)
					self._load_log_file_into_state(fp)
		except Exception as e:
			messagebox.showerror("Drag & Drop Error", f"Could not open dropped file(s):\n{e}")

	# --- Filter Logic (Threaded) ---
	def smart_update_filter(self, idx, is_enabling):
		if self.is_processing: return
		self.filters_dirty = True
		self.recalc_filtered_data()

	def recalc_filtered_data(self):
		if self.is_processing: return

		# If no active log file or no log files loaded, clear everything
		if not self.active_log_filepath or not self.loaded_log_files:
			self._reset_active_filter_state()
			self.set_ui_busy(False)
			return

		self.set_ui_busy(True)
		self.filter_op_start_time = time.time() # Record start time

		# Handle Merged View
		if self.active_log_filepath == self.MERGED_VIEW_ID:
			if self.merged_log_data:
				# Trigger filtering for ALL loaded files
				self.pending_filter_count = len(self.loaded_log_files)
				for log_state in self.loaded_log_files.values():
					self._start_rust_filter_thread(log_state)
			else:
				self._reset_active_filter_state()
				self.set_ui_busy(False)
			return

		# Handle Individual Log Files
		if not self.active_rust_engine:
			self._reset_active_filter_state()
			self.set_ui_busy(False)
			return

		self.pending_filter_count = 1
		self._start_rust_filter_thread(self.loaded_log_files[self.active_log_filepath])

	def _reset_active_filter_state(self):
		self.active_filtered_indices = []
		self.active_all_line_tags = []
		self.active_timeline_events = []
		self.active_timeline_events_by_time = []
		self.active_timeline_events_by_index = []
		self.active_timestamps_found = False
		self.refresh_filter_list()
		self.refresh_view_fast()
		self.draw_timeline()

	def _start_rust_filter_thread(self, log_state): # Accepts LogFileState object
		# Prepare filter data for Rust: List of (text, is_regex, is_exclude, is_event, original_idx)
		rust_filters = []
		for i, f in enumerate(self.filters):
			if f.enabled:
				rust_filters.append((f.text, f.is_regex, f.is_exclude, f.is_event, i))

		def run_rust():
			try:
				t_start = time.time()
				# Call Rust with the log_state's rust_engine
				tag_codes, filtered_indices, subset_counts, timeline_raw = log_state.rust_engine.filter(rust_filters)

				# Map subset counts back to full filter list
				full_counts = [0] * len(self.filters)
				for i, count in enumerate(subset_counts):
					if i < len(rust_filters):
						original_idx = rust_filters[i][4]
						full_counts[original_idx] = count

				# Convert tag_codes (u8) back to string tags for Python UI
				code_map = {0: None, 1: 'EXCLUDED'}
				for idx, (_, _, _, _, original_idx) in enumerate(rust_filters):
					code_map[2 + idx] = f"filter_{original_idx}"

				line_tags = [code_map.get(c, None) for c in tag_codes]

				# Process timeline events
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
				# Send all processed data along with the log_state.filepath
				self.msg_queue.put(('filter_complete', line_tags, filtered_indices, t_end - t_start, full_counts, log_state.filepath, timeline_events_processed, bool(timeline_events_processed)))

			except Exception as e:
				self.msg_queue.put(('load_error', f"Rust Engine Filter Error for {log_state.filepath}: {e}"))

		threading.Thread(target=run_rust, daemon=True).start()

	# --- View Generation (Instant) ---
	def refresh_view_fast(self):
		show_only = self.show_only_filtered_var.get()

		if show_only:
			if not self.active_all_line_tags:
				self.filtered_cache = None
			else:
				new_cache = []
				raw = self.active_raw_lines
				tags = self.active_all_line_tags

				for r_idx in self.active_filtered_indices:
					t = tags[r_idx]
					new_cache.append((raw[r_idx], [t] if t else [], r_idx))
				self.filtered_cache = new_cache
		else:
			self.filtered_cache = None

		self.restore_view_position()

		mode_text = "Filtered" if show_only else "Full View"
		count_text = len(self.filtered_cache) if self.filtered_cache else len(self.active_raw_lines)
		self.update_status(f"[{mode_text}] Showing {count_text} lines (Total {len(self.active_raw_lines)})")

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
						found_idx = self.active_filtered_indices.index(target_raw_index)
					except ValueError:
						for i, idx in enumerate(self.active_filtered_indices):
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
	def _get_view_index_from_raw(self, raw_idx):
		"""Returns the index in the current view (filtered/unfiltered) for a given raw_idx."""
		if self.show_only_filtered_var.get() and self.active_filtered_indices:
			import bisect
			# self.active_filtered_indices is sorted.
			idx = bisect.bisect_left(self.active_filtered_indices, raw_idx)
			if idx != len(self.active_filtered_indices) and self.active_filtered_indices[idx] == raw_idx:
				return idx
			return None
		else:
			# Unfiltered view: raw_idx is the index (assuming line 0 is index 0)
			return raw_idx

	def copy_selection(self, event=None):
		if not self.selected_indices: return "break"
		
		lines_to_copy = []
		sorted_raw = sorted(list(self.selected_indices))
		
		# Use active_raw_lines or merged view logic
		if self.active_log_filepath == self.MERGED_VIEW_ID and hasattr(self, 'active_raw_lines'):
			# For merged view, we can access by index assuming active_raw_lines supports it
			for ridx in sorted_raw:
				if 0 <= ridx < len(self.active_raw_lines):
					lines_to_copy.append(self.active_raw_lines[ridx])
		elif self.active_rust_engine:
			# Single file
			for ridx in sorted_raw:
				line = self.active_rust_engine.get_line(ridx)
				if line is not None:
					lines_to_copy.append(line)
					
		if lines_to_copy:
			text = "\n".join(lines_to_copy)
			self.root.clipboard_clear()
			self.root.clipboard_append(text)
			self.update_status(f"Copied {len(lines_to_copy)} lines to clipboard.")
			
		return "break"

	def on_log_single_click(self, event):
		self.text_area.focus_set()
		self.text_area.tag_remove("current_line", "1.0", tk.END)
		try:
			index = self.text_area.index(f"@{event.x},{event.y}")
			ui_row = int(index.split('.')[0])
			self.text_area.mark_set(tk.INSERT, index)
			# self.text_area.tag_add("current_line", f"{ui_row}.0", f"{ui_row+1}.0") # Moved to render_viewport based on selection
			# self.text_area.tag_raise("current_line")
			
			cache_index = self.view_start_index + (ui_row - 1)
			total = self.get_total_count()
			
			if 0 <= cache_index < total:
				_, _, raw_idx = self.get_view_item(cache_index)
				
				# Handle Multi-selection
				# Check for modifier keys
				# Standard Tkinter state masks: Shift=0x1, Control=0x4
				ctrl_pressed = (event.state & 0x4) != 0
				shift_pressed = (event.state & 0x1) != 0
				
				if shift_pressed and self.selected_raw_index != -1:
					# Range selection
					start_view_idx = self._get_view_index_from_raw(self.selected_raw_index)
					end_view_idx = cache_index # Current view index
					
					if start_view_idx is not None:
						low = min(start_view_idx, end_view_idx)
						high = max(start_view_idx, end_view_idx)
						
						if not ctrl_pressed:
							self.selected_indices.clear()
						
						# Add range
						for i in range(low, high + 1):
							_, _, r_idx = self.get_view_item(i)
							self.selected_indices.add(r_idx)
				
				elif ctrl_pressed:
					# Toggle selection
					if raw_idx in self.selected_indices:
						self.selected_indices.remove(raw_idx)
					else:
						self.selected_indices.add(raw_idx)
					self.selected_raw_index = raw_idx # Update anchor
					
				else:
					# Single selection
					self.selected_indices.clear()
					self.selected_indices.add(raw_idx)
					self.selected_raw_index = raw_idx # Update anchor
				
				self.selection_offset = ui_row - 1
				
			else:
				# Clicked empty space - clear selection unless modifier held?
				# Standard behavior: clicking empty space usually deselects
				if not (event.state & 0x4) and not (event.state & 0x1):
					self.selected_raw_index = -1
					self.selected_indices.clear()
					self.selection_offset = 0

			# Clear native selection to avoid visual conflicts
			self.text_area.tag_remove("sel", "1.0", tk.END)
			self.render_viewport()
			return "break" # Prevent native selection behavior

		except Exception as e: print(f"Click error: {e}")

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
			# Determine which line was clicked
			index = self.text_area.index(f"@{event.x},{event.y}")
			ui_row = int(index.split('.')[0])
			cache_index = self.view_start_index + (ui_row - 1)
			total = self.get_total_count()
			
			clicked_raw_idx = -1
			if 0 <= cache_index < total:
				_, _, clicked_raw_idx = self.get_view_item(cache_index)

			# If clicked line is not in selection, select it (exclusive)
			if clicked_raw_idx != -1 and clicked_raw_idx not in self.selected_indices:
				self.on_log_single_click(event)
			
			# Enable/Disable menu items based on if note exists for the ANCHOR line
			# Menu indices: 0=Copy, 1=Sep, 2=Add/Edit Note, 3=Remove Note
			if self.selected_raw_index in self.notes:
				self.log_context_menu.entryconfig(2, label="Edit Note")
				self.log_context_menu.entryconfig(3, state="normal")
			else:
				self.log_context_menu.entryconfig(2, label="Add Note")
				self.log_context_menu.entryconfig(3, state="disabled")

			self.log_context_menu.post(event.x_root, event.y_root)
		except Exception as e: print(f"Right click error: {e}")

	def on_key_c_pressed(self, event=None):
		# "c" for "comment" or "capture"
		if self.selected_raw_index != -1:
			# Open the add/edit note dialog for the currently selected line
			self.add_note_dialog()
		return "break" # Prevents the key press from propagating

	def add_note_dialog(self, target_index=None):
		if not self.active_log_filepath:
			messagebox.showinfo("Add Note", "Please load a log file first to add notes.", parent=self.root)
			return

		idx = target_index if target_index is not None else self.selected_raw_index
		if idx == -1: return

		note_key = (self.active_log_filepath, idx)
		if self.active_log_filepath == self.MERGED_VIEW_ID and hasattr(self.active_raw_lines, 'get_original_ref'):
			orig_fp, orig_idx = self.active_raw_lines.get_original_ref(idx)
			if orig_fp:
				note_key = (orig_fp, orig_idx)

		current_note = self.notes.get(note_key, "")

		dialog = tk.Toplevel(self.root)
		dialog.withdraw()
		dialog.title(f"Note for Line {idx + 1}")
		self._apply_icon(dialog)
		dialog.transient(self.root)
		dialog.grab_set()
		self.center_window(dialog, 400, 200)
		dialog.config(bg=self.root.cget("bg")) # Match theme
		dialog.bind("<Escape>", lambda e: dialog.destroy())

		# Buttons (Pack first to ensure visibility at bottom)
		btn_frame = ttk.Frame(dialog, padding=10)
		btn_frame.pack(side=tk.BOTTOM, fill=tk.X)

		def save():
			content = txt_input.get("1.0", tk.END).strip()
			if content:
				self.notes[note_key] = content
			else:
				# If content is empty, delete the note
				if note_key in self.notes:
					del self.notes[note_key]
			self.render_viewport()
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
		if not self.active_log_filepath or self.selected_raw_index == -1: return

		note_key = (self.active_log_filepath, self.selected_raw_index)
		if self.active_log_filepath == self.MERGED_VIEW_ID and hasattr(self.active_raw_lines, 'get_original_ref'):
			orig_fp, orig_idx = self.active_raw_lines.get_original_ref(self.selected_raw_index)
			if orig_fp:
				note_key = (orig_fp, orig_idx)

		if note_key in self.notes:
			del self.notes[note_key]
			self.render_viewport()
			self.refresh_notes_window()

	def export_notes(self):
		if not self.active_log_filepath:
			messagebox.showerror("Export Error", "A log file must be loaded to save notes.", parent=self.root)
			return

		if self.active_log_filepath == self.MERGED_VIEW_ID and self.merged_log_data:
			# Merged View: Batch export for all loaded files
			updated_count = 0
			error_count = 0

			for fp in self.merged_log_data.ordered_files:
				# Filter notes for this specific file
				notes_to_export = {str(raw_idx): content for (filepath, raw_idx), content in self.notes.items() if filepath == fp}

				if not notes_to_export:
					continue # No notes for this file, skip

				log_dir = os.path.dirname(fp)
				log_basename = os.path.basename(fp)
				log_name_without_ext, _ = os.path.splitext(log_basename)
				note_filename = f"{log_name_without_ext}.note"
				filepath = os.path.join(log_dir, note_filename)

				try:
					# For batch export in merged view, we overwrite silently or maybe we should ask?
					# To avoid spamming dialogs, we'll overwrite silently or log it.
					# Let's overwrite silently for now as "Export" implies saving current state.
					with open(filepath, 'w', encoding='utf-8') as f:
						json.dump(notes_to_export, f, indent=4, sort_keys=True)
					updated_count += 1
				except Exception:
					error_count += 1

			if updated_count > 0 or error_count > 0:
				msg = f"Batch Export Complete.\nUpdated notes for {updated_count} file(s)."
				if error_count > 0:
					msg += f"\nFailed to update {error_count} file(s)."
				messagebox.showinfo("Export Notes", msg, parent=self.root)
			else:
				messagebox.showinfo("Export Notes", "No notes found to export for any of the merged files.", parent=self.root)
			return

		# Single File Export (Existing Logic)
		# Filter notes to only include those for the active log file
		notes_to_export = {str(raw_idx): content for (filepath, raw_idx), content in self.notes.items() if filepath == self.active_log_filepath}

		if not notes_to_export:
			messagebox.showinfo("Export Notes", "There are no notes for the active log file to export.", parent=self.root)
			return

		# Construct the file path directly in the log's directory
		log_dir = os.path.dirname(self.active_log_filepath)
		log_basename = os.path.basename(self.active_log_filepath)
		log_name_without_ext, _ = os.path.splitext(log_basename)
		note_filename = f"{log_name_without_ext}.note"
		filepath = os.path.join(log_dir, note_filename)

		# Ask for confirmation before overwriting an existing file
		if os.path.exists(filepath):
			if not messagebox.askyesno("Confirm Overwrite", f"The file '{note_filename}' already exists.\n\nDo you want to overwrite it?", parent=self.root):
				return

		try:
			with open(filepath, 'w', encoding='utf-8') as f:
				json.dump(notes_to_export, f, indent=4, sort_keys=True)
			messagebox.showinfo("Success", f"Successfully exported {len(notes_to_export)} notes to:\n{filepath}", parent=self.root)
		except Exception as e:
			messagebox.showerror("Export Error", f"Failed to save notes file:\n{e}", parent=self.root)

	def save_notes_to_text(self):
		if not self.active_log_filepath:
			messagebox.showinfo("Save Notes", "Please load a log file first to save notes.", parent=self.root)
			return

		lines_to_write = []
		default_filename = "notes.txt"

		if self.active_log_filepath == self.MERGED_VIEW_ID and self.merged_log_data:
			# Merged View: Export notes as seen in the merged list
			default_filename = "merged_notes.txt"

			# We need to iterate through the merged view to get line numbers correct
			# Similar to refresh_notes_window logic for merged view

			current_offset = 0
			for fp in self.merged_log_data.ordered_files:
				if fp in self.loaded_log_files:
					# Check for notes belonging to this file
					file_notes = {k: v for (n_fp, k), v in self.notes.items() if n_fp == fp}
					sorted_indices = sorted(file_notes.keys())

					for raw_idx in sorted_indices:
						merged_idx = current_offset + raw_idx
						line_num = merged_idx + 1

						# Get timestamp from the line in merged view
						timestamp_str = ""
						if merged_idx < len(self.active_raw_lines):
							log_line = self.active_raw_lines[merged_idx]
							match = re.search(r'(\b\d{1,2}:\d{2}:\d{2}\.\d+\s+(?:AM|PM)\b|\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+|\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?|\b\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?\b)', log_line)
							if match:
								timestamp_str = match.group(1)

						content = file_notes[raw_idx].replace("\n", " ")
						# Optionally include filename for context in merged export
						filename_str = os.path.basename(fp)
						lines_to_write.append(f"{line_num}\t{timestamp_str}\t[{filename_str}] {content}")

					current_offset += self.loaded_log_files[fp].rust_engine.line_count()

			# Sort by merged line number (though our iteration order naturally does this if notes are sorted per file and files are sorted in merge)
			# But to be safe if files overlap in time? Wait, merge view is currently just concatenated. So order is preserved.

		else:
			# Single File Export
			active_notes = {k: v for (filepath, k), v in self.notes.items() if filepath == self.active_log_filepath}
			if not active_notes:
				messagebox.showinfo("Save Notes", "There are no notes for the active log file to save.", parent=self.root)
				return

			log_basename = os.path.basename(self.active_log_filepath)
			log_name_without_ext, _ = os.path.splitext(log_basename)
			default_filename = f"{log_name_without_ext}.txt"

			sorted_indices = sorted(active_notes.keys())
			for idx in sorted_indices:
				line_num = idx + 1
				timestamp_str = ""
				if idx < len(self.active_raw_lines):
					log_line = self.active_raw_lines[idx]
					match = re.search(r'(\b\d{1,2}:\d{2}:\d{2}\.\d+\s+(?:AM|PM)\b|\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+|\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?|\b\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?\b)', log_line)
					if match:
						timestamp_str = match.group(1)

				content = active_notes[idx].replace("\n", " ") # Flatten for display
				lines_to_write.append(f"{line_num}\t{timestamp_str}\t{content}")

		if not lines_to_write and self.active_log_filepath != self.MERGED_VIEW_ID:
			# For merged view, we might want to allow empty export or show message?
			# Actually logic above returns early for single file if empty.
			# For merged, check list
			messagebox.showinfo("Save Notes", "No notes found to save.", parent=self.root)
			return
		elif not lines_to_write and self.active_log_filepath == self.MERGED_VIEW_ID:
			messagebox.showinfo("Save Notes", "No notes found in any of the merged files.", parent=self.root)
			return


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
		if tags and self.active_log_filepath: # Ensure active_log_filepath is available
			raw_idx = int(tags[0])
			self.add_note_dialog(target_index=raw_idx)

	def remove_note_from_tree(self):
		selected = self.notes_tree.selection()
		if not selected: return
		tags = self.notes_tree.item(selected[0], "tags")
		if tags and self.active_log_filepath:
			raw_idx = int(tags[0])
			note_key = (self.active_log_filepath, raw_idx)

			if self.active_log_filepath == self.MERGED_VIEW_ID and hasattr(self.active_raw_lines, 'get_original_ref'):
				orig_fp, orig_idx = self.active_raw_lines.get_original_ref(raw_idx)
				if orig_fp:
					note_key = (orig_fp, orig_idx)

			if note_key in self.notes:
				del self.notes[note_key]
				self.render_viewport()
				self.refresh_notes_window()

	def refresh_notes_window(self):
		if not hasattr(self, 'notes_tree') or not self.notes_tree.winfo_exists(): return

		for item in self.notes_tree.get_children():
			self.notes_tree.delete(item)

		if not self.active_log_filepath: return

		active_notes = {} # {display_index: content}

		if self.active_log_filepath == self.MERGED_VIEW_ID and self.merged_log_data:
			# Merged View: iterate through all loaded files and find their notes
			# We need to calculate offsets to map original index -> merged index
			current_offset = 0
			# self.merged_log_data.ordered_files contains the file paths in order
			for fp in self.merged_log_data.ordered_files:
				if fp in self.loaded_log_files:
					# Check for notes belonging to this file
					# Iterate all notes to find matches (could be optimized but self.notes is usually small)
					for (note_fp, note_raw_idx), content in self.notes.items():
						if note_fp == fp:
							merged_idx = current_offset + note_raw_idx
							active_notes[merged_idx] = content

					current_offset += self.loaded_log_files[fp].rust_engine.line_count()
		else:
			# Single File View
			for (fp, k), v in self.notes.items():
				if fp == self.active_log_filepath:
					active_notes[k] = v

		sorted_indices = sorted(active_notes.keys())

		for i, idx in enumerate(sorted_indices):
			line_num = idx + 1

			# Extract timestamp from the raw log line
			timestamp_str = ""
			if idx < len(self.active_raw_lines):
				log_line = self.active_raw_lines[idx]
				# Regex to find common timestamp formats.
				# 1. HH:MM:SS.MS AM/PM
				# 2. MM/DD/YYYY-HH:MM:SS.ms
				# 3. YYYY-MM-DD HH:MM:SS,ms
				# 4. HH:MM:SS.ms
				match = re.search(r'(\b\d{1,2}:\d{2}:\d{2}\.\d+\s+(?:AM|PM)\b|\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+|\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?|\b\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?\b)', log_line)
				if match:
					timestamp_str = match.group(1)

			content = active_notes[idx].replace("\n", " ") # Flatten for display
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

	def check_and_import_notes(self, target_filepath=None):
		filepath = target_filepath if target_filepath else self.active_log_filepath
		if not filepath:
			return

		log_basename = os.path.basename(filepath)
		log_name_without_ext, _ = os.path.splitext(log_basename)
		note_filename = f"{log_name_without_ext}.note"

		# Look for the note file in the same directory as the log file
		log_dir = os.path.dirname(filepath)
		potential_path = os.path.join(log_dir, note_filename)

		if os.path.exists(potential_path):
			if messagebox.askyesno("Import Notes", f"Found a matching notes file:\n'{note_filename}'\n\nDo you want to import the notes?"):
				try:
					with open(potential_path, 'r', encoding='utf-8') as f:
						# JSON keys are strings, convert them back to int, and associate with filepath
						str_keyed_notes = json.load(f)
						for raw_idx_str, note_content in str_keyed_notes.items():
							raw_idx = int(raw_idx_str)
							self.notes[(filepath, raw_idx)] = note_content

					self.update_status(f"Imported {len(str_keyed_notes)} notes for {os.path.basename(filepath)}.")

					# Auto-show notes window on successful import if it's the active file
					if filepath == self.active_log_filepath:
						if not self.note_view_visible_var.get():
							self.note_view_visible_var.set(True)
							self.toggle_note_view_visibility()
						self.refresh_notes_window()

				except Exception as e:
					messagebox.showerror("Import Error", f"Failed to import notes:\n{e}")



	def jump_to_line(self, raw_index):
		if not self.active_log_filepath: return
		if self.active_log_filepath != self.MERGED_VIEW_ID and self.active_log_filepath not in self.loaded_log_files: return

		# Check if line is in filtered view
		found_in_view = False
		if self.show_only_filtered_var.get(): # Check if currently in filtered mode
			try:
				view_idx = self.active_filtered_indices.index(raw_index)
				total_in_view = len(self.active_filtered_indices)
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
					self.recalc_filtered_data() # Recalculate and refresh view in full mode
					found_in_view = False # Will fall through to raw view handling
				else:
					return

		if not found_in_view: # This also covers the case where show_only_filtered is False
			# Full view
			self.selected_raw_index = raw_index
			total_in_view = len(self.active_raw_lines)
			half = self.visible_rows // 2
			new_start = max(0, raw_index - half)
			new_start = min(new_start, max(0, total_in_view - self.visible_rows))
			self.view_start_index = new_start
			self.selection_offset = raw_index - new_start

		self.selected_raw_index = raw_index # Ensure selected
		self.selected_indices.clear()
		self.selected_indices.add(raw_index)
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
		dialog.withdraw()
		dialog.title("Go to Line")
		self._apply_icon(dialog)
		dialog.transient(self.root)
		dialog.grab_set()
		self.center_window(dialog, 300, 120)
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

	# --- Embedded Timeline Logic ---

	def _update_timeline_data(self, log_state): # Accepts LogFileState object
		"""Sorts events for the timeline."""
		if log_state.timeline_events:
			log_state.timeline_events_by_time = sorted(log_state.timeline_events, key=lambda x: x[0])
			log_state.timeline_events_by_index = sorted(log_state.timeline_events, key=lambda x: x[2])
		else:
			log_state.timeline_events_by_time = []
			log_state.timeline_events_by_index = []

	def get_approx_time(self, raw_idx):
		"""Estimates the timestamp for a given raw line index using event data, with interpolation."""
		if not self.active_timeline_events_by_index: return None

		# Events are (time, filter_text, raw_index)
		event_indices = [e[2] for e in self.active_timeline_events_by_index]

		idx = bisect.bisect_left(event_indices, raw_idx)

		if idx < len(event_indices) and event_indices[idx] == raw_idx:
			# Exact match
			return self.active_timeline_events_by_index[idx][0]
		elif idx == 0:
			# raw_idx is before or at the first event's raw_index
			return self.active_timeline_events_by_index[0][0]
		elif idx >= len(event_indices): # raw_idx is after or at the last event's raw_index
			return self.active_timeline_events_by_index[-1][0]
		else:
			# raw_idx is between active_timeline_events_by_index[idx-1] and active_timeline_events_by_index[idx]
			event_before = self.active_timeline_events_by_index[idx-1]
			event_after = self.active_timeline_events_by_index[idx]

			time_before, raw_idx_before = event_before[0], event_before[2]
			time_after, raw_idx_after = event_after[0], event_after[2]

			if raw_idx_after == raw_idx_before: # Safeguard against division by zero
				return time_before

			# Linear interpolation of time based on raw_index
			fraction = (raw_idx - raw_idx_before) / (raw_idx_after - raw_idx_before)
			interpolated_timedelta = (time_after - time_before) * fraction
			return time_before + interpolated_timedelta

	def get_approx_index_from_time(self, target_time):
		"""Finds the nearest line index for a given timestamp."""
		if not self.active_timeline_events_by_time: return 0

		# Bisect to find time
		idx = bisect.bisect_left(self.active_timeline_events_by_time, target_time, key=lambda x: x[0])

		if idx < len(self.active_timeline_events_by_time):
			return self.active_timeline_events_by_time[idx][2]
		elif idx > 0:
			return self.active_timeline_events_by_time[idx-1][2]
		return 0

	def draw_timeline(self):
		"""Full redraw of the timeline."""
		self.timeline_canvas.delete("all")
		width = self.timeline_canvas.winfo_width()
		height = self.timeline_canvas.winfo_height()

		if width <= 1: return

		is_dark = self.dark_mode.get()
		bg_color = "#2e2e2e" if is_dark else "#ffffff"
		self.timeline_canvas.config(bg=bg_color)

		if not self.active_timeline_events_by_time:
			self.timeline_canvas.create_text(width//2, height//2, text="No events marked", fill="#888888")
			return

		# Draw Events
		self._draw_timeline_events_layer(width, height)

		# Draw Viewport
		self._draw_timeline_viewport_layer(width, height)

	def _draw_timeline_events_layer(self, width, height):
		if not self.active_timeline_events_by_time: return

		# 1. Determine Actual Event Range (Cropping empty time)
		first_event_time = self.active_timeline_events_by_time[0][0]
		last_event_time = self.active_timeline_events_by_time[-1][0]

		# Add 1% padding to the range
		total_range_sec = (last_event_time - first_event_time).total_seconds()
		if total_range_sec <= 0: total_range_sec = 1

		padding = total_range_sec * 0.01
		start_time = first_event_time - datetime.timedelta(seconds=padding)
		end_time = last_event_time + datetime.timedelta(seconds=padding)
		total_duration = (end_time - start_time).total_seconds()

		# Zoom logic (on top of the cropped range)
		visible_duration = total_duration / self.timeline_zoom
		view_start_time_offset = self.timeline_view_offset
		t_view_start = start_time + datetime.timedelta(seconds=view_start_time_offset)
		t_view_end = t_view_start + datetime.timedelta(seconds=visible_duration)

		# 2. Setup Colors
		is_dark = self.dark_mode.get()
		filter_color_map = {}
		for f in self.filters:
			key = f.text.strip()
			bg = fix_color(f.back_color, "#FFFFFF")
			fg = fix_color(f.fore_color, "#000000")

			rgb_bg = hex_to_rgb(bg)
			lum_bg = (0.299 * rgb_bg[0] + 0.587 * rgb_bg[1] + 0.114 * rgb_bg[2]) / 255.0

			use_fg = False
			if not is_dark and lum_bg > 0.9: use_fg = True
			elif is_dark and lum_bg < 0.2: use_fg = True

			if use_fg:
				rgb_fg = hex_to_rgb(fg)
				lum_fg = (0.299 * rgb_fg[0] + 0.587 * rgb_fg[1] + 0.114 * rgb_fg[2]) / 255.0
				if (not is_dark and lum_fg > 0.9) or (is_dark and lum_fg < 0.2):
					filter_color_map[key] = "#0078D7"
				else:
					filter_color_map[key] = fg
			else:
				filter_color_map[key] = bg

		# 3. Draw Axis/Labels (Bottom 15px)
		axis_height = 15
		plot_height = height - axis_height
		label_color = "#888888" if is_dark else "#555555"

		# Draw 3 markers (Start, Middle, End)
		for i in range(3):
			ratio = i / 2.0
			x = int(ratio * width)
			t_marker = t_view_start + datetime.timedelta(seconds=ratio * visible_duration)
			t_str = t_marker.strftime("%H:%M:%S")
			anchor = "w" if i == 0 else ("e" if i == 2 else "center")
			self.timeline_canvas.create_text(x, height - 5, text=t_str, fill=label_color, font=("Consolas", 8), anchor=anchor)
			self.timeline_canvas.create_line(x, plot_height, x, plot_height + 5, fill=label_color)

		# 4. Bucket and Draw Events (Block style)
		self.timeline_buckets = [ [] for _ in range(width) ]
		import bisect
		idx_start = bisect.bisect_left(self.active_timeline_events_by_time, t_view_start, key=lambda x: x[0])

		for i in range(idx_start, len(self.active_timeline_events_by_time)):
			dt, f_text, r_idx = self.active_timeline_events_by_time[i]
			if dt > t_view_end: break

			offset_in_view = (dt - t_view_start).total_seconds()
			x = int((offset_in_view / visible_duration) * width)
			if 0 <= x < width:
				self.timeline_buckets[x].append((dt, f_text, r_idx))

		max_count = 0
		for b in self.timeline_buckets:
			if len(b) > max_count: max_count = len(b)
		if max_count == 0: return

		from collections import Counter
		for x, events in enumerate(self.timeline_buckets):
			if not events: continue
			count = len(events)

			bar_h = int((count / max_count) * plot_height)
			if bar_h < 5: bar_h = 5 # Minimum height for visibility

			event_colors = [filter_color_map.get(e[1].strip(), "#0078D7") for e in events]
			most_common_color = Counter(event_colors).most_common(1)[0][0]

			# Draw rectangle (2px wide) for better visibility
			x1 = x - 1
			x2 = x + 1
			y1 = plot_height
			y2 = plot_height - bar_h
			self.timeline_canvas.create_rectangle(x1, y1, x2, y2, fill=most_common_color, outline="", tags="events")

	def _draw_timeline_viewport_layer(self, width, height):
		self.timeline_canvas.delete("viewport")

		if not self.active_timeline_events_by_time: return
		if not hasattr(self, 'view_start_index') or not hasattr(self, 'current_displayed_lines'): return

		start_time = self.active_timeline_events_by_time[0][0]
		end_time = self.active_timeline_events_by_time[-1][0]
		total_duration = (end_time - start_time).total_seconds()
		if total_duration <= 0: return

		visible_duration = total_duration / self.timeline_zoom
		view_start_time_offset = self.timeline_view_offset

		# Viewport Window Time - current view on timeline
		t_timeline_view_start = start_time + datetime.timedelta(seconds=view_start_time_offset)

		# Get time for start and end of LOG view (the highlighted box)
		first_displayed_raw_idx = self.get_view_item(self.view_start_index)[2]
		# Ensure last_displayed_raw_idx doesn't go beyond total lines
		last_displayed_raw_idx = self.get_view_item(min(self.view_start_index + self.current_displayed_lines - 1, self.get_total_count() - 1))[2]

		t_log_start = self.get_approx_time(first_displayed_raw_idx)
		t_log_end = self.get_approx_time(last_displayed_raw_idx)

		if t_log_start and t_log_end:
			offset_start = (t_log_start - t_timeline_view_start).total_seconds()
			offset_end = (t_log_end - t_timeline_view_start).total_seconds()

			x1 = (offset_start / visible_duration) * width
			x2 = (offset_end / visible_duration) * width

			# Clamp to canvas width
			x1 = max(0, x1)
			x2 = min(width, x2)

			if x2 - x1 < 1: # Ensure it has at least 1 pixel width to be visible
				# If range is too small, make it a single pixel line at x1
				x2 = x1 + 1

			is_dark = self.dark_mode.get()
			indicator_fill_color = "#cccccc" if is_dark else "#333333" # Greyish color
			indicator_outline_color = "#ffffff" if is_dark else "#000000"

			# Use fill with a thin outline, possibly with stipple for transparency if desired
			self.timeline_canvas.create_rectangle(x1, 0, x2, height,
												fill=indicator_fill_color, # Solid fill for now
												outline=indicator_outline_color,
												width=1, tags="viewport") # Thinner outline
	def update_timeline_viewport(self):
		"""Only redraws the viewport indicator (fast)."""
		width = self.timeline_canvas.winfo_width()
		height = self.timeline_canvas.winfo_height()
		if width <= 1: return
		self._draw_timeline_viewport_layer(width, height)

	def on_timeline_resize(self, event):
		self.draw_timeline()

	def on_timeline_motion(self, event):
		x = event.x
		width = self.timeline_canvas.winfo_width()

		# Check bounds and data existence
		if not hasattr(self, 'timeline_buckets') or x < 0 or x >= len(self.timeline_buckets):
			self.timeline_tooltip.place_forget()
			return

		bucket = self.timeline_buckets[x]
		if not bucket:
			self.timeline_tooltip.place_forget()
			return

		# Prepare tooltip info
		count = len(bucket)
		start_t = bucket[0][0].strftime("%H:%M:%S")
		end_t = bucket[-1][0].strftime("%H:%M:%S")

		from collections import Counter
		texts = [e[1] for e in bucket]
		top_text_item = Counter(texts).most_common(1)[0] # (text, count)

		msg = f"Time: {start_t} - {end_t}\nTotal Events: {count}\nTop: {top_text_item[0]} ({top_text_item[1]})"

		# Calculate Position (Avoid clipping)
		rx, ry = self.timeline_canvas.winfo_rootx(), self.timeline_canvas.winfo_rooty()
		tx = rx + x + 15
		ty = ry - 60 # Above the cursor

		# Adjust if off-screen right
		screen_w = self.root.winfo_screenwidth()
		# Or just root width if not fullscreen. Use root geometry.
		root_x = self.root.winfo_rootx()
		root_w = self.root.winfo_width()

		if tx + 200 > root_x + root_w:
			tx = rx + x - 210

		# Place relative to root
		rel_x = tx - root_x
		rel_y = ty - self.root.winfo_rooty()

		self.timeline_tooltip.config(text=msg)
		self.timeline_tooltip.place(x=rel_x, y=rel_y)
		self.timeline_tooltip.lift()

	def on_timeline_zoom(self, event):
		if not self.active_timeline_events_by_time: return

		# Determine direction
		if event.num == 4 or event.delta > 0:
			zoom_factor = 1.1
		else:
			zoom_factor = 0.9

		new_zoom = self.timeline_zoom * zoom_factor
		if new_zoom < 1.0: new_zoom = 1.0 # Min zoom 1.0 (fit all)

		# Zoom centered on mouse X
		width = self.timeline_canvas.winfo_width()
		start_time = self.active_timeline_events_by_time[0][0]
		end_time = self.active_timeline_events_by_time[-1][0]
		total_duration = (end_time - start_time).total_seconds()
		if total_duration <= 0: return

		# Time at cursor before zoom
		old_visible_duration = total_duration / self.timeline_zoom
		cursor_ratio = event.x / width
		time_offset_at_cursor = self.timeline_view_offset + (cursor_ratio * old_visible_duration)

		self.timeline_zoom = new_zoom
		new_visible_duration = total_duration / self.timeline_zoom

		# Adjust offset so time_offset_at_cursor remains at cursor_ratio
		new_view_offset = time_offset_at_cursor - (cursor_ratio * new_visible_duration)

		# Clamp
		max_offset = total_duration - new_visible_duration
		self.timeline_view_offset = max(0.0, min(new_view_offset, max_offset))

		self.draw_timeline()
		return "break"

	def on_timeline_pan_start(self, event):
		self.timeline_pan_start_x = event.x
		self.timeline_pan_start_offset = self.timeline_view_offset
		self.timeline_canvas.config(cursor="fleur")

	def on_timeline_pan_drag(self, event):
		width = self.timeline_canvas.winfo_width()
		if not self.active_timeline_events_by_time: return
		start_time = self.active_timeline_events_by_time[0][0]
		end_time = self.active_timeline_events_by_time[-1][0]
		total_duration = (end_time - start_time).total_seconds()
		if total_duration <= 0: return

		visible_duration = total_duration / self.timeline_zoom

		dx = self.timeline_pan_start_x - event.x # Drag left to move view right
		dt_per_pixel = visible_duration / width

		new_offset = self.timeline_pan_start_offset + (dx * dt_per_pixel)

		# Clamp
		max_offset = total_duration - visible_duration
		self.timeline_view_offset = max(0.0, min(new_offset, max_offset))

		self.draw_timeline()

	def on_timeline_pan_release(self, event):
		self.timeline_canvas.config(cursor="hand2")

	def on_timeline_click(self, event):
		self._handle_timeline_nav(event.x)

	def on_timeline_drag(self, event):
		self._handle_timeline_nav(event.x)

	def _handle_timeline_nav(self, x):
		if not self.active_timeline_events_by_time: return
		width = self.timeline_canvas.winfo_width()
		if width <= 0: return

		# Map x to time considering zoom/offset
		start_time = self.active_timeline_events_by_time[0][0]
		end_time = self.active_timeline_events_by_time[-1][0]
		total_duration = (end_time - start_time).total_seconds()
		visible_duration = total_duration / self.timeline_zoom

		ratio = x / width
		offset_in_view = ratio * visible_duration
		target_time_offset = self.timeline_view_offset + offset_in_view

		target_time = start_time + datetime.timedelta(seconds=target_time_offset)

		# Find index
		target_idx = self.get_approx_index_from_time(target_time)

		# Jump
		self.jump_to_line(target_idx)

	def toggle_timeline_pane(self):
		"""Toggles the visibility of the timeline pane."""
		# If mapped (visible), hide it.
		if self.timeline_frame.winfo_manager():
			self.paned_window.forget(self.timeline_frame)
		else:
			# Show it. Insert at index 1 (between Log View [0] and Filter View [Last])
			# If Filter View is hidden/removed, it might be the last one.
			# But PanedWindow index logic is simple.
			# We want it below the content frame.

			# Current panes:
			panes = self.paned_window.panes()

			# We assume top pane is always there (index 0).
			# We insert at index 1.
			if len(panes) >= 1:
				self.paned_window.add(self.timeline_frame, after=panes[0], minsize=40, height=60, stretch="never")
			else:
				self.paned_window.add(self.timeline_frame, minsize=40, height=60, stretch="never")

		# Force a redraw if showing
		if self.timeline_frame.winfo_manager():
			self.draw_timeline()



	def render_viewport(self):
		# Use active_raw_lines for total count when not filtered
		total = self.get_total_count()

		self.text_area.config(state=tk.NORMAL); self.text_area.delete("1.0", tk.END)
		self.line_number_area.config(state=tk.NORMAL); self.line_number_area.delete("1.0", tk.END)

		if total == 0:
			self.text_area.config(state=tk.DISABLED); self.line_number_area.config(state=tk.DISABLED); return

		# Ensure we have a valid active log or merged view
		if not self.active_log_filepath:
			self.text_area.config(state=tk.DISABLED); self.line_number_area.config(state=tk.DISABLED); return

		if self.active_log_filepath != self.MERGED_VIEW_ID and self.active_log_filepath not in self.loaded_log_files:
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

			# Check notes for the current active file and raw_idx
			note_key = (self.active_log_filepath, raw_idx)
			if self.active_log_filepath == self.MERGED_VIEW_ID and hasattr(self.active_raw_lines, 'get_original_ref'):
				orig_fp, orig_idx = self.active_raw_lines.get_original_ref(raw_idx)
				if orig_fp:
					note_key = (orig_fp, orig_idx)

			if note_key in self.notes:
				tag_buffer.append((relative_idx, ["note_line"]))

			if raw_idx in self.selected_indices:
				tag_buffer.append((relative_idx, ["current_line"]))

		full_text = "".join(display_buffer)
		self.text_area.insert("1.0", full_text)

		line_nums_text = "\n".join(line_nums_buffer)
		self.line_number_area.insert("1.0", line_nums_text)
		self.line_number_area.tag_add("right_align", "1.0", "end")

		# Re-enable tags
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
		self.current_displayed_lines = int(self.text_area.index('end-1c').split('.')[0]) # Get actual number of lines displayed
		self.update_timeline_viewport()

	def update_scrollbar_thumb(self):
		total = self.get_total_count()
		if total == 0: self.scrollbar_y.set(0, 1)
		else:
			# Use the number of lines actually displayed in the text area for page_size
			displayed_lines = self.current_displayed_lines if hasattr(self, 'current_displayed_lines') else 1
			page_size = displayed_lines / total
			start = self.view_start_index / total
			end = start + page_size
			self.scrollbar_y.set(start, end)

	def on_scroll_y(self, *args):
		total = self.get_total_count()
		if total == 0: return
		op = args[0]
		if op == "scroll":
			units = int(args[1]); what = args[2]
			page_size = self.current_displayed_lines if hasattr(self, 'current_displayed_lines') else 1
			step = page_size if what == "pages" else 1
			new_start = self.view_start_index + (units * step)
		elif op == "moveto":
			fraction = float(args[1]); new_start = int(total * fraction)
		new_start = max(0, min(new_start, total - (self.current_displayed_lines if hasattr(self, 'current_displayed_lines') else 1)))
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
		new_start = max(0, min(new_start, total - (self.current_displayed_lines if hasattr(self, 'current_displayed_lines') else 1)))
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
		self.find_window.withdraw()
		self.find_window.title("Find")
		self._apply_icon(self.find_window)
		self.find_window.transient(self.root)
		self.find_window.resizable(False, False)
		self.find_window.protocol("WM_DELETE_WINDOW", self.close_find_bar)
		self.find_window.config(bg=self.root.cget("bg"))

		self.center_window(self.find_window, 550, 80)

		frame = ttk.Frame(self.find_window, padding=5)
		frame.pack(fill=tk.BOTH, expand=True)

		ttk.Label(frame, text="Find:").pack(side=tk.LEFT, padx=(0, 5))
		self.find_entry = ttk.Combobox(frame, values=self.find_history, width=25)
		self.find_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
		self.find_entry.bind("<Return>", self.on_find_confirm)
		if self.last_search_query:
			self.find_entry.set(self.last_search_query)
			self.find_entry.selection_range(0, tk.END)

		ttk.Button(frame, text="Find", command=self.on_find_confirm, width=6).pack(side=tk.LEFT, padx=2)

		ttk.Checkbutton(frame, text="Case", variable=self.find_case_var).pack(side=tk.LEFT, padx=(10, 0))
		ttk.Checkbutton(frame, text="Wrap", variable=self.find_wrap_var).pack(side=tk.LEFT, padx=(5, 0))

		self.find_entry.focus_set()
		self.find_window.bind("<Escape>", self.close_find_bar)
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
		self.update_status(f"Showing {self.get_total_count()} lines (Total {len(self.active_raw_lines)})")
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
		self.update_status(f"Showing {self.get_total_count()} lines (Total {len(self.active_raw_lines)})")
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
		# Check if raw_idx is in active_filtered_indices (which is sorted)
		i = bisect.bisect_left(self.active_filtered_indices, raw_idx)
		if i != len(self.active_filtered_indices) and self.active_filtered_indices[i] == raw_idx:
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
				idx = bisect.bisect_left(self.active_filtered_indices, raw_idx)
				if idx < len(self.active_filtered_indices) and self.active_filtered_indices[idx] == raw_idx:
					y = int((idx / total_view_items) * h)
					unique_y.add(y)
		else:
			# Full mode: raw_idx is directly useful
			total_raw = len(self.active_raw_lines)
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

		# 1. Update Search History
		if query in self.find_history:
			self.find_history.remove(query)
		self.find_history.insert(0, query)
		self.find_history = self.find_history[:10]
		if self.find_entry and self.find_entry.winfo_exists():
			self.find_entry.config(values=self.find_history)

		case_sensitive = self.find_case_var.get()

		# 1. Perform Search (if query changed or cache missing)
		if (query != self.last_search_query or
			case_sensitive != self.last_search_case or
			self.last_search_results is None):

			self.set_ui_busy(True)
			try:
				if self.active_log_filepath == self.MERGED_VIEW_ID:
					# Merged View: Aggregate search results from all files
					all_results = []
					current_offset = 0
					# Follow the same order as in Merged View build
					for fp in self.merged_log_data.ordered_files:
						if fp in self.loaded_log_files:
							log_state = self.loaded_log_files[fp]
							# Search in original file's engine
							local_results = log_state.rust_engine.search(query, False, case_sensitive)
							# Offset results
							for r in local_results:
								all_results.append(current_offset + r)
							current_offset += len(log_state.raw_lines)
					self.last_search_results = all_results
				elif self.active_rust_engine: # Use active rust engine (Single File)
					# Call Rust: search(query, is_regex, case_sensitive)
					self.last_search_results = self.active_rust_engine.search(query, False, case_sensitive)
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

		# Find the first candidate (regardless of visibility)
		if candidates:
			target_raw_index = matches[candidates[0]]
			found = True

		if found:
			# Check visibility and auto-disable filter mode if needed
			if not self._is_visible(target_raw_index) and self.show_only_filtered_var.get():
				self.show_only_filtered_var.set(False)
				self.recalc_filtered_data() # Refresh view mode
				self.update_status("Switched to Full View to show match.")

			self.jump_to_line(target_raw_index)
			if self.find_entry and self.find_entry.winfo_exists():
				self.find_entry.config(foreground="black")
			self.update_status(f"Found match on line {target_raw_index + 1}")

			# Schedule highlight (UI update needs a moment after jump)
			self.text_area.tag_remove("find_match", "1.0", tk.END)
			self.root.after(50, lambda: self._highlight_find_match(query, case_sensitive))
		else:
			if self.find_entry and self.find_entry.winfo_exists():
				self.find_entry.config(foreground="black") # Reset color if wrapping around or starting new
			
			# If we didn't find anything in candidates, it means we hit the end/start and wrap is off
			if self.find_entry and self.find_entry.winfo_exists():
				self.find_entry.config(foreground="red")
			self.update_status("No more matches found.")

	def find_next(self, event=None): self._find(backward=False); return "break"
	def find_previous(self, event=None): self._find(backward=True); return "break"

	def refresh_filter_list(self):
		for item in self.tree.get_children(): self.tree.delete(item)
		is_dark = self.dark_mode.get()

		# Get hit counts from the active log file state
		active_log_hit_counts = []
		is_merged = (self.active_log_filepath == self.MERGED_VIEW_ID)

		if not is_merged and self.active_log_filepath and self.active_log_filepath in self.loaded_log_files:
			active_log_hit_counts = self.loaded_log_files[self.active_log_filepath].filter_hit_counts

		for idx, flt in enumerate(self.filters):
			en_str = "☑" if flt.enabled else "☐"
			type_str = "Excl" if flt.is_exclude else ("Regex" if flt.is_regex else "Text")

			if is_merged:
				hit_count_str = str(flt.hit_count)
			else:
				hit_count_str = "0"
				if idx < len(active_log_hit_counts):
					hit_count_str = str(active_log_hit_counts[idx])

			event_str = "✓" if flt.is_event else ""
			item_id = self.tree.insert("", "end", values=(en_str, type_str, flt.text, hit_count_str, event_str))
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
				self.filters_dirty = True
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
		self.filters_dirty = True
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
		self.filters_dirty = True
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
		self.filters_dirty = True
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
		self.filters_dirty = True
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
		dialog.withdraw()
		dialog.title("Edit Filter" if filter_obj else "Add Filter")
		self._apply_icon(dialog)
		dialog.transient(self.root) # Make it a child of the main window
		dialog.grab_set()
		self.center_window(dialog, 600, 200)
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

		def get_contrast_color(hex_color):
			rgb = hex_to_rgb(hex_color)
			lum = (0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2])
			return "#000000" if lum > 128 else "#FFFFFF"

		def pick_fg():
			c = colorchooser.askcolor(color=colors["fg"])[1]
			if c:
				colors["fg"] = c
				style.configure("FG.TButton", foreground=get_contrast_color(c), background=c)

		def pick_bg():
			c = colorchooser.askcolor(color=colors["bg"])[1]
			if c:
				colors["bg"] = c
				style.configure("BG.TButton", foreground=get_contrast_color(c), background=c)

		style = ttk.Style(dialog)
		style.configure("FG.TButton", foreground=get_contrast_color(colors["fg"]), background=colors["fg"])
		style.configure("BG.TButton", foreground=get_contrast_color(colors["bg"]), background=colors["bg"])

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
				self.filters_dirty = True
				self.recalc_filtered_data()
			else:
				new_filter = Filter(text, colors["fg"], colors["bg"], enabled=True, is_regex=var_regex.get(), is_exclude=var_exclude.get(), is_event=var_event.get())
				self.filters.append(new_filter)
				self.filters_dirty = True
				self.recalc_filtered_data()
			dialog.destroy()

		ttk.Button(button_frame, text="Save", command=save).pack(side=tk.RIGHT)
		ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.RIGHT, padx=5)
		
		entry_text.bind("<Return>", lambda e: save())
		dialog.bind("<Escape>", lambda e: dialog.destroy())
		
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
			self.filters_dirty = False # Changes saved
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
			self.filters_dirty = False # Newly loaded, not dirty
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
			self.filters_dirty = False # Reset dirty flag after recalc
		except Exception as e: messagebox.showerror("Error", f"JSON Import Failed: {e}")

	# --- Multi-Log File Support ---
	def load_multiple_logs(self):
		if self.is_processing: return
		init_dir = self.config.get("last_log_dir", ".")
		filepaths = filedialog.askopenfilenames(initialdir=init_dir, filetypes=[("Log Files", "*.log *.txt"), ("All Files", "*.*")])
		if not filepaths: return

		self.config["last_log_dir"] = os.path.dirname(filepaths[0]); self.save_config()
		self.set_ui_busy(True) # Set busy once for the whole multi-load operation

		# Load each selected file
		for fp in filepaths:
			self._load_log_file_into_state(fp)

	def _set_active_log_state(self, filepath, load_duration=None):
		"""Sets the specified log file as the active one, updating all proxy variables and refreshing UI."""
		if filepath == self.MERGED_VIEW_ID:
			if not self.merged_log_data: # If merged data not built yet
				self.set_ui_busy(True)
				self.update_status("Building Merged View... This may take a moment.")
				self.show_toast("Building Merged View...", duration=3000)
				self.root.update_idletasks()
				threading.Thread(target=self._worker_build_merged_view, daemon=True).start()
				return

			active_state = self.merged_log_data
			self.active_log_filepath = self.MERGED_VIEW_ID
			display_log_name = "Merged View"
		elif filepath not in self.loaded_log_files:
			print(f"ERROR: Attempted to set active log to unknown filepath: {filepath}")
			return
		else:
			active_state = self.loaded_log_files[filepath]
			self.active_log_filepath = filepath
			display_log_name = os.path.basename(filepath)

		# Update all proxy variables
		self.active_raw_lines = active_state.raw_lines
		self.active_rust_engine = active_state.rust_engine
		self.active_all_line_tags = active_state.all_line_tags
		self.active_filtered_indices = active_state.filtered_indices
		self.active_timeline_events = active_state.timeline_events
		self.active_timeline_events_by_time = active_state.timeline_events_by_time
		self.active_timeline_events_by_index = active_state.timeline_events_by_index
		self.active_timestamps_found = active_state.timestamps_found
		self.current_log_path = active_state.filepath # Keep for consistency with original current_log_path (or virtual for merged)

		# Reset view
		self.view_start_index = 0
		self.selected_raw_index = -1
		self.selection_offset = 0
		self.last_search_query = None
		self.last_search_results = None
		self.marker_canvas.delete("all")
		self.welcome_label.place_forget()

		# Adjust line number area width
		max_digits = len(str(len(self.active_raw_lines)))
		self.line_number_area.config(width=max(7, max_digits))

		# Update UI components
		self.update_title()
		if load_duration is not None:
			self.load_duration_str = f"{load_duration:.4f}s"

		self.update_status(f"Loaded {len(self.active_raw_lines)} lines from {display_log_name}")

		# Recalculate filters for the new active state
		self.recalc_filtered_data() # This will update filter_complete and draw_timeline

		# Select in treeview if not already selected (Skip for MERGED_VIEW_ID)
		if filepath != self.MERGED_VIEW_ID and self.log_files_tree.selection() != (filepath,):
			if self.log_files_tree.exists(filepath):
				self.log_files_tree.selection_set(filepath)

		# Ensure the timeline has the correct active data (this is implicitly handled by recalc_filtered_data now)
		# self._update_timeline_data(active_state) # Explicitly update timeline data for active_state
		# self.draw_timeline()

		self.refresh_notes_window()



	def _worker_build_merged_view(self):
		"""Builds a merged view sorted by file start times (Concatenation Mode)."""
		try:
			t_start = time.time()
			self.msg_queue.put(('status', "Merging logs: Sorting files by start time..."))

			ts_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d+)?|\d{2}/\d{2}/\d{4}-\d{2}:\d{2}:\d{2}\.\d+|\b\d{1,2}:\d{2}:\d{2}\.\d+\s+(?:AM|PM)\b|\b\d{2}:\d{2}:\d{2}(?:[.,]\d+)?\b)')

			file_info = []
			for fp, log_state in self.loaded_log_files.items():
				# Get start time from the very first line
				first_line = log_state.rust_engine.get_line(0)
				match = ts_pattern.search(first_line)
				start_ts = match.group(1) if match else "9999"
				file_info.append((start_ts, fp))

			# Sort file paths by their start timestamp
			file_info.sort()

			merged_refs = []
			total_files = len(file_info)
			for i, (ts, fp) in enumerate(file_info, 1):
				self.msg_queue.put(('status', f"Merging logs: Adding file {i}/{total_files}..."))
				log_state = self.loaded_log_files[fp]
				count = log_state.rust_engine.line_count()
				# Efficiently add all line references for this file
				for raw_idx in range(count):
					merged_refs.append((fp, raw_idx))

			if not merged_refs:
				self.msg_queue.put(('load_error', "No lines found to merge."))
				return

			# Create proxies (Dynamic fetching)
			class MergedLinesProxy:
				def __init__(self, app_ref, data):
					self.app = app_ref
					self.data = data # List of (fp, raw_idx)
				def __len__(self):
					return len(self.data)
				def __getitem__(self, idx):
					if idx < 0 or idx >= len(self.data):
						raise IndexError("Index out of bounds")
					fp, raw_idx = self.data[idx]
					if fp in self.app.loaded_log_files:
						return self.app.loaded_log_files[fp].rust_engine.get_line(raw_idx)
					return "<Error: File not loaded>"
				def get_original_ref(self, idx):
					if 0 <= idx < len(self.data): return self.data[idx]
					return None, None

			merged_raw_lines_proxy = MergedLinesProxy(self, merged_refs)

			# Proxy for line tags in merged view
			class MergedTagsProxy:
				def __init__(self, app_ref, data):
					self.app = app_ref
					self.data = data # List of (fp, raw_idx)
				def __len__(self):
					return len(self.data)
				def __getitem__(self, idx):
					if idx < 0 or idx >= len(self.data): return None
					fp, raw_idx = self.data[idx]
					if fp in self.app.loaded_log_files:
						state = self.app.loaded_log_files[fp]
						tags = state.all_line_tags
						if tags and raw_idx < len(tags):
							return tags[raw_idx]
					return None

			merged_tags_proxy = MergedTagsProxy(self, merged_refs)

			class MergedRustEngineStub:
				def __init__(self, count): self._count = count
				def line_count(self): return self._count
				def filter(self, rust_filters): return [], [], [], []

			merged_state = LogFileState(self.MERGED_VIEW_ID, merged_raw_lines_proxy, MergedRustEngineStub(len(merged_refs)))
			merged_state.all_line_tags = merged_tags_proxy
			merged_state.ordered_files = [item[1] for item in file_info] # Store sorted file paths
			merged_state.timestamps_found = True
			merged_state.filtered_indices = list(range(len(merged_refs)))
			merged_state.filter_hit_counts = [0] * len(self.filters)

			t_end = time.time()
			self.msg_queue.put(('merge_complete', merged_state, t_end - t_start))
		except Exception as e:
			self.msg_queue.put(('load_error', f"Merge failed: {e}"))


	def on_log_files_right_click(self, event):
		item_id = self.log_files_tree.identify_row(event.y)
		if item_id:
			self.log_files_tree.selection_set(item_id)
			# Disable "Remove" for Merged View node
			state = "disabled" if item_id == self.MERGED_VIEW_ID else "normal"
			self.log_files_context_menu.entryconfig(0, state=state)
			self.log_files_context_menu.post(event.x_root, event.y_root)

	def remove_selected_log(self):
		selected = self.log_files_tree.selection()
		if not selected: return

		filepath = selected[0]
		if filepath == self.MERGED_VIEW_ID: return

		if filepath in self.loaded_log_files:
			# Remove from state
			del self.loaded_log_files[filepath]
			self.log_files_tree.delete(filepath)

			# Invalidate merged view
			self.merged_log_data = None

			# 1. Update list and sidebar visibility
			if len(self.loaded_log_files) < 2:
				if hasattr(self, 'merge_btn'):
					self.merge_btn.pack_forget()

				if self.log_files_tree.exists(self.MERGED_VIEW_ID):
					self.log_files_tree.delete(self.MERGED_VIEW_ID)

				if self.log_files_panel_visible.get():
					self.log_files_panel_visible.set(False)
					self.toggle_log_panel()

			# 2. Handle View Switching
			if self.active_log_filepath == filepath:
				remaining = self.log_files_tree.get_children()
				if remaining:
					self._set_active_log_state(remaining[0])
				else:
					self._clear_all_logs()
			else:
				# If we didn't clear everything but changed the file set, redraw viewport to be safe
				self.render_viewport()

	def on_log_file_select(self, event):
		selected_item = self.log_files_tree.selection()
		if not selected_item: return

		filepath = selected_item[0]
		if filepath in self.loaded_log_files:
			self._set_active_log_state(filepath)
		elif filepath == self.MERGED_VIEW_ID:
			self._set_active_log_state(self.MERGED_VIEW_ID)

		# Hide the welcome label if a log is selected
		self.welcome_label.place_forget()

if __name__ == "__main__":
	if HAS_DND:
		root = TkinterDnD.Tk()
	else:
		root = tk.Tk()
	app = LogAnalyzerApp(root)
	root.mainloop()