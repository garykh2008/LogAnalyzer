import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { invoke } from '@tauri-apps/api/core';

export interface FilterItem {
  text: string;
  is_regex: boolean;
  is_exclude: boolean;
  is_event: boolean;
  idx: number;
  fg_color: string;
  bg_color: string;
  enabled: boolean;
  hits: number;
}

export interface NoteItem {
  line: number;
  text: string;
}

function parseTatFilters(xmlText: string): Omit<FilterItem, 'idx' | 'hits'>[] {
  const parser = new DOMParser();
  const xmlDoc = parser.parseFromString(xmlText, "text/xml");
  const filterElements = xmlDoc.getElementsByTagName("filter");
  const list: Omit<FilterItem, 'idx' | 'hits'>[] = [];
  
  for (let i = 0; i < filterElements.length; i++) {
    const el = filterElements[i];
    const text = el.getAttribute("text") || "";
    if (!text) continue;
    
    const enabled = el.getAttribute("enabled") !== "n";
    const is_exclude = el.getAttribute("excluding") === "y";
    const is_regex = el.getAttribute("regex") === "y";
    
    const fgRaw = el.getAttribute("foreColor");
    const bgRaw = el.getAttribute("backColor");
    
    let fg_color = "#000000";
    if (fgRaw) {
      fg_color = fgRaw.startsWith("#") ? fgRaw : "#" + fgRaw;
    }
    
    let bg_color = "";
    if (bgRaw) {
      bg_color = bgRaw.startsWith("#") ? bgRaw : "#" + bgRaw;
    }
    
    list.push({
      text,
      enabled,
      is_exclude,
      is_regex,
      is_event: false,
      fg_color,
      bg_color,
    });
  }
  return list;
}

function generateTatFiltersXml(filters: FilterItem[]): string {
  let xml = `<?xml version="1.0" encoding="utf-8"?>\n<TextAnalysisTool.NET version="2017-01-24" showOnlyFilteredLines="False">\n  <filters>\n`;
  filters.forEach(f => {
    const escapedText = f.text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');
      
    const fg = f.fg_color.replace('#', '');
    const bg = f.bg_color ? f.bg_color.replace('#', '') : '';
    
    xml += `    <filter enabled="${f.enabled ? 'y' : 'n'}" excluding="${f.is_exclude ? 'y' : 'n'}" text="${escapedText}" type="matches_text" regex="${f.is_regex ? 'y' : 'n'}" case_sensitive="n"`;
    if (fg && fg.toLowerCase() !== '000000') xml += ` foreColor="${fg}"`;
    if (bg) xml += ` backColor="${bg}"`;
    xml += ` />\n`;
  });
  xml += `  </filters>\n</TextAnalysisTool.NET>`;
  return xml;
}

interface AppState {
  // Theme & Preferences
  theme: 'dark' | 'light';
  editorFontSize: number;
  editorFontFamily: string;
  showLineNumbers: boolean;
  lineSpacing: number;
  defaultEncoding: string;
  uiFontSize: number;
  uiFontFamily: string;
  setTheme: (theme: 'dark' | 'light') => void;
  setPreferences: (prefs: Partial<Omit<AppState, 'setTheme' | 'setPreferences'>>) => void;

  // Log Files
  loadedFiles: string[];
  activeFile: string | null;
  lineCount: number;
  loading: boolean;
  setActiveFile: (file: string | null) => Promise<void>;
  loadLog: (filepath: string) => Promise<void>;
  closeLog: (filepath: string) => Promise<void>;

  // Selection
  selectedLine: number | null;
  selectedLines: number[];
  setSelectedLine: (line: number | null, isMulti?: boolean) => void;
  clearSelection: () => void;
  copySelection: () => Promise<void>;

  // Search
  searchQuery: string;
  isRegexSearch: boolean;
  isCaseSensitiveSearch: boolean;
  searchResults: number[];
  activeSearchResults: number[];
  searchIndex: number;
  isSearching: boolean;
  setSearchQuery: (query: string, isRegex: boolean, isCaseSensitive: boolean) => void;
  runSearch: () => Promise<void>;
  nextSearchMatch: () => void;
  prevSearchMatch: () => void;
  clearSearch: () => void;

  // Filters
  filters: FilterItem[];
  showFilteredOnly: boolean;
  tagCodes: number[];
  filteredIndices: number[] | null;
  filterPalette: Record<number, { fg: string; bg: string }>;
  timelineEvents: Array<[string, string, number]>;
  currentFilterFile: string | null;
  filtersModified: boolean;
  filterDebounceTimer: ReturnType<typeof setTimeout> | null;
  debouncedApplyFilters: () => void;
  addFilter: (filter: Omit<FilterItem, 'idx' | 'hits'>) => void;
  updateFilter: (index: number, filter: Partial<FilterItem>) => void;
  removeFilter: (index: number) => void;
  moveFilter: (fromIndex: number, toIndex: number) => void;
  toggleShowFilteredOnly: () => void;
  applyFilters: () => Promise<void>;
  importFilters: () => Promise<boolean>;
  loadFiltersFromPath: (path: string) => Promise<boolean>;
  saveFiltersAs: () => Promise<boolean>;
  quickSaveFilters: () => Promise<boolean>;
  clearFilters: () => void;

  // Filter Editor Lifted State
  isAddingFilter: boolean;
  editingFilterIdx: number | null;
  filterText: string;
  filterIsRegex: boolean;
  filterIsExclude: boolean;
  filterIsEvent: boolean;
  filterFgColor: string;
  filterBgColor: string;
  setFilterEditor: (state: Partial<{ isAddingFilter: boolean, editingFilterIdx: number | null, filterText: string, filterIsRegex: boolean, filterIsExclude: boolean, filterIsEvent: boolean, filterFgColor: string, filterBgColor: string }>) => void;
  openAddFilter: (initialText: string) => void;
  resetFilterEditor: () => void;

  // Workspace layout states
  activeTab: 'files' | 'filters' | 'notes';
  isSidebarOpen: boolean;
  setActiveTab: (tab: 'files' | 'filters' | 'notes') => void;
  setIsSidebarOpen: (isOpen: boolean) => void;
  selectedFilterIdx: number | null;
  setSelectedFilterIdx: (idx: number | null) => void;
  navigateFilterHit: (reverse?: boolean) => void;

  // Notes
  notes: Record<string, Record<number, string>>;
  noteEditLine: number | null;
  setNoteEditLine: (line: number | null) => void;
  addNote: (filepath: string, line: number, text: string) => void;
  deleteNote: (filepath: string, line: number) => void;
  saveNotes: () => Promise<void>;
  loadNotesForFile: (filepath: string) => Promise<void>;

  // Recent Files
  recentFiles: string[];
  addRecentFile: (filepath: string) => void;
  clearRecentFiles: () => void;
}

export const useStore = create<AppState>()(
  persist(
    (set, get) => ({
  theme: 'light',
  editorFontSize: 12,
  editorFontFamily: 'Consolas',
  showLineNumbers: true,
  lineSpacing: 0,
  defaultEncoding: 'UTF-8',
  uiFontSize: 12,
  uiFontFamily: 'Inter',

  setTheme: (theme) => {
    set({ theme });
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  },
  setPreferences: (prefs) => set(() => prefs as Partial<AppState>),

  loadedFiles: [],
  activeFile: null,
  lineCount: 0,
  loading: false,

  recentFiles: [],

  addRecentFile: (filepath) => {
    const current = get().recentFiles;
    const filtered = current.filter((f) => f !== filepath);
    const updated = [filepath, ...filtered].slice(0, 10);
    set({ recentFiles: updated });
  },

  clearRecentFiles: () => {
    set({ recentFiles: [] });
  },

  setActiveFile: async (file) => {
    if (!file) {
      set({ activeFile: null, lineCount: 0, selectedLine: null, selectedLines: [], searchResults: [], searchIndex: -1 });
      return;
    }
    set({ activeFile: file, loading: true });
    try {
      const lineCount = await invoke<number>('load_log', { filepath: file });
      set({ lineCount, loading: false });
      await get().loadNotesForFile(file);
      await get().applyFilters();
    } catch (err) {
      console.error('Failed to switch to file:', err);
      set({ loading: false });
    }
  },

  loadLog: async (filepath) => {
    set({ loading: true });
    try {
      const lineCount = await invoke<number>('load_log', { filepath });
      const currentLoaded = get().loadedFiles;
      const updated = currentLoaded.includes(filepath) ? currentLoaded : [...currentLoaded, filepath];
      set({
        loadedFiles: updated,
        activeFile: filepath,
        lineCount,
        loading: false,
        selectedLine: null,
        selectedLines: [],
      });
      get().addRecentFile(filepath);
      await get().loadNotesForFile(filepath);
      await get().applyFilters();
    } catch (err) {
      console.error('Failed to load log:', err);
      set({ loading: false });
    }
  },

  closeLog: async (filepath) => {
    try {
      await invoke('close_log', { filepath });
      const updated = get().loadedFiles.filter((f) => f !== filepath);
      let nextActive = get().activeFile;
      if (get().activeFile === filepath) {
        nextActive = updated.length > 0 ? updated[0] : null;
      }
      set({ loadedFiles: updated });
      await get().setActiveFile(nextActive);
    } catch (err) {
      console.error('Failed to close log:', err);
    }
  },

  // Selection
  selectedLine: null,
  selectedLines: [],
  setSelectedLine: (line, isMulti = false) => {
    const { selectedLines, showFilteredOnly, filteredIndices } = get();
    if (line === null) {
      set({ selectedLine: null, selectedLines: [] });
      return;
    }

    // Smart Jump: If filtered view is active and target line is hidden, turn off filter mode to reveal it
    if (showFilteredOnly && filteredIndices && !filteredIndices.includes(line)) {
      set({ showFilteredOnly: false });
      get().applyFilters();
    }

    if (isMulti) {
      const newLines = selectedLines.includes(line)
        ? selectedLines.filter((l) => l !== line)
        : [...selectedLines, line].sort((a, b) => a - b);
      set({ selectedLines: newLines, selectedLine: line });
    } else {
      set({ selectedLine: line, selectedLines: [line] });
    }
  },
  clearSelection: () => set({ selectedLine: null, selectedLines: [] }),
  copySelection: async () => {
    const { selectedLines, activeFile } = get();
    if (selectedLines.length === 0 || !activeFile) return;
    const sorted = [...selectedLines].sort((a, b) => a - b);
    try {
      const lines = await invoke<string[]>('get_lines', { filepath: activeFile, indices: sorted });
      const clipboardText = lines.map(l => l.replace(/[\r\n]+$/, '')).join('\n');
      await navigator.clipboard.writeText(clipboardText);
    } catch (err) {
      console.error('Copy failed:', err);
    }
  },

  // Search
  searchQuery: '',
  isRegexSearch: false,
  isCaseSensitiveSearch: false,
  searchResults: [],
  activeSearchResults: [],
  searchIndex: -1,
  isSearching: false,

  setSearchQuery: (query, isRegex, isCaseSensitive) => {
    set({ searchQuery: query, isRegexSearch: isRegex, isCaseSensitiveSearch: isCaseSensitive });
  },

  runSearch: async () => {
    const { activeFile, searchQuery, isRegexSearch, isCaseSensitiveSearch, showFilteredOnly, filteredIndices } = get();
    if (!activeFile || !searchQuery) {
      set({ searchResults: [], activeSearchResults: [], searchIndex: -1 });
      return;
    }
    set({ isSearching: true });
    try {
      const results = await invoke<number[]>('search_log', {
        filepath: activeFile,
        query: searchQuery,
        isRegex: isRegexSearch,
        caseSensitive: isCaseSensitiveSearch,
      });

      let activeResults = results;
      if (showFilteredOnly && filteredIndices) {
        const filterSet = new Set(filteredIndices);
        activeResults = results.filter((r) => filterSet.has(r));
      }

      set({
        searchResults: results,
        activeSearchResults: activeResults,
        searchIndex: activeResults.length > 0 ? 0 : -1,
        isSearching: false,
      });
    } catch (err) {
      console.error('Search failed:', err);
      set({ isSearching: false, searchResults: [], activeSearchResults: [], searchIndex: -1 });
    }
  },

  nextSearchMatch: () => {
    const { activeSearchResults, selectedLine } = get();
    if (activeSearchResults.length === 0) return;

    let nextIdx = 0;
    if (selectedLine !== null) {
      const idx = activeSearchResults.findIndex((r) => r > selectedLine);
      if (idx !== -1) {
        nextIdx = idx;
      } else {
        nextIdx = 0;
      }
    }

    const targetLine = activeSearchResults[nextIdx];
    set({ searchIndex: nextIdx, selectedLine: targetLine, selectedLines: [targetLine] });
  },

  prevSearchMatch: () => {
    const { activeSearchResults, selectedLine } = get();
    if (activeSearchResults.length === 0) return;

    let prevIdx = activeSearchResults.length - 1;
    if (selectedLine !== null) {
      let foundIdx = -1;
      for (let i = activeSearchResults.length - 1; i >= 0; i--) {
        if (activeSearchResults[i] < selectedLine) {
          foundIdx = i;
          break;
        }
      }
      if (foundIdx !== -1) {
        prevIdx = foundIdx;
      } else {
        prevIdx = activeSearchResults.length - 1;
      }
    }

    const targetLine = activeSearchResults[prevIdx];
    set({ searchIndex: prevIdx, selectedLine: targetLine, selectedLines: [targetLine] });
  },

  clearSearch: () => set({ searchQuery: '', searchResults: [], activeSearchResults: [], searchIndex: -1 }),

  // Filters
  filters: [],
  showFilteredOnly: false,
  tagCodes: [],
  filteredIndices: null,
  filterPalette: {},
  timelineEvents: [],
  currentFilterFile: null,
  filtersModified: false,
  filterDebounceTimer: null as ReturnType<typeof setTimeout> | null,

  // Debounced filter re-application to prevent race conditions on rapid edits
  debouncedApplyFilters: () => {
    const state = get();
    if (state.filterDebounceTimer) {
      clearTimeout(state.filterDebounceTimer);
    }
    const timer = setTimeout(() => {
      get().applyFilters();
    }, 150);
    set({ filterDebounceTimer: timer });
  },

  addFilter: (f) => {
    const filters = get().filters;
    const newFilter: FilterItem = {
      ...f,
      idx: filters.length,
      hits: 0,
    };
    set({ filters: [...filters, newFilter], filtersModified: true });
    get().debouncedApplyFilters();
  },

  updateFilter: (index, f) => {
    const updated = get().filters.map((item, i) => (i === index ? { ...item, ...f } : item));
    set({ filters: updated, filtersModified: true });
    get().debouncedApplyFilters();
  },

  removeFilter: (index) => {
    const updated = get().filters.filter((_, i) => i !== index).map((f, i) => ({ ...f, idx: i }));
    set({ filters: updated, filtersModified: true });
    get().debouncedApplyFilters();
  },

  moveFilter: (fromIndex, toIndex) => {
    const updated = [...get().filters];
    const [moved] = updated.splice(fromIndex, 1);
    updated.splice(toIndex, 0, moved);
    const reindexed = updated.map((f, i) => ({ ...f, idx: i }));
    set({ filters: reindexed, filtersModified: true });
    get().debouncedApplyFilters();
  },

  clearFilters: () => {
    set({ filters: [], currentFilterFile: null, filtersModified: false });
    get().applyFilters();
  },

  toggleShowFilteredOnly: () => {
    set((state) => ({ showFilteredOnly: !state.showFilteredOnly }));
    get().applyFilters();
  },

  applyFilters: async () => {
    const { activeFile, filters, showFilteredOnly } = get();
    if (!activeFile) return;

    const rustFilters = filters
      .filter((f) => f.enabled)
      .map((f) => ({
        text: f.text,
        is_regex: f.is_regex,
        is_exclude: f.is_exclude,
        is_event: f.is_event,
        idx: f.idx,
      }));

    try {
      const [tagCodes, filteredIndices, hitCounts, events] = await invoke<[number[], number[], number[], Array<[string, string, number]>]>(
        'filter_log',
        { filepath: activeFile, filters: rustFilters }
      );

      const palette: Record<number, { fg: string; bg: string }> = {};
      let activeCount = 0;
      filters.forEach((f) => {
        if (f.enabled) {
          palette[activeCount + 2] = { fg: f.fg_color, bg: f.bg_color };
          activeCount++;
        }
      });

      const updatedFilters = get().filters.map((f) => {
        const enabledIdx = rustFilters.findIndex((rf) => rf.idx === f.idx);
        return {
          ...f,
          hits: enabledIdx !== -1 ? hitCounts[enabledIdx] : 0,
        };
      });

      const searchResults = get().searchResults;
      let activeResults = searchResults;
      if (showFilteredOnly) {
        const filterSet = new Set(filteredIndices);
        activeResults = searchResults.filter((r) => filterSet.has(r));
      }

      set({
        tagCodes,
        filteredIndices: showFilteredOnly ? filteredIndices : null,
        filterPalette: palette,
        timelineEvents: events,
        filters: updatedFilters,
        activeSearchResults: activeResults,
      });
    } catch (err) {
      console.error('Filter execution failed:', err);
    }
  },

  importFilters: async () => {
    try {
      const path = await invoke<string | null>('open_file_dialog');
      if (!path) return false;
      const xmlText = await invoke<string>('read_text_file', { path });
      const loaded = parseTatFilters(xmlText);
      
      const newFilters = loaded.map((f, i) => ({
        ...f,
        idx: i,
        hits: 0,
      }));

      set({ filters: newFilters, currentFilterFile: path, filtersModified: false });
      await get().applyFilters();
      return true;
    } catch (err) {
      console.error('Failed to import filters:', err);
      return false;
    }
  },

  loadFiltersFromPath: async (path: string) => {
    try {
      const xmlText = await invoke<string>('read_text_file', { path });
      const loaded = parseTatFilters(xmlText);
      const newFilters = loaded.map((f, i) => ({
        ...f,
        idx: i,
        hits: 0,
      }));
      set({ filters: newFilters, currentFilterFile: path, filtersModified: false });
      await get().applyFilters();
      return true;
    } catch (err) {
      console.error('Failed to load filters from path:', err);
      return false;
    }
  },

  saveFiltersAs: async () => {
    try {
      const path = await invoke<string | null>('save_file_dialog', { defaultName: 'filters.tat', extension: 'tat' });
      if (!path) return false;
      const xmlContent = generateTatFiltersXml(get().filters);
      await invoke('write_text_file', { path, content: xmlContent });
      set({ currentFilterFile: path, filtersModified: false });
      return true;
    } catch (err) {
      console.error('Failed to save filters as:', err);
      return false;
    }
  },

  quickSaveFilters: async () => {
    const { currentFilterFile, filters } = get();
    if (!currentFilterFile) {
      return get().saveFiltersAs();
    }
    try {
      const xmlContent = generateTatFiltersXml(filters);
      await invoke('write_text_file', { path: currentFilterFile, content: xmlContent });
      set({ filtersModified: false });
      return true;
    } catch (err) {
      console.error('Failed to quick save filters:', err);
      return false;
    }
  },

  // Filter Editor Lifted State
  isAddingFilter: false,
  editingFilterIdx: null,
  filterText: '',
  filterIsRegex: false,
  filterIsExclude: false,
  filterIsEvent: false,
  filterFgColor: '#000000',
  filterBgColor: 'transparent',
  setFilterEditor: (state) => set(state),
  openAddFilter: (initialText) => {
    set({
      isAddingFilter: true,
      editingFilterIdx: null,
      filterText: initialText,
      filterIsRegex: false,
      filterIsExclude: false,
      filterIsEvent: false,
      filterFgColor: '#000000',
      filterBgColor: '#ffffff'
    });
  },
  resetFilterEditor: () => set({
    isAddingFilter: false,
    editingFilterIdx: null,
    filterText: '',
    filterIsRegex: false,
    filterIsExclude: false,
    filterIsEvent: false,
    filterFgColor: '#000000',
    filterBgColor: 'transparent'
  }),

  // Workspace layout states
  activeTab: 'filters',
  isSidebarOpen: true,
  setActiveTab: (tab) => set({ activeTab: tab }),
  setIsSidebarOpen: (isOpen) => set({ isSidebarOpen: isOpen }),
  selectedFilterIdx: null,
  setSelectedFilterIdx: (idx) => set({ selectedFilterIdx: idx }),
  navigateFilterHit: (reverse = false) => {
    const { filters, tagCodes, selectedLine, selectedFilterIdx, activeFile } = get();
    if (!activeFile || selectedFilterIdx === null || selectedFilterIdx < 0 || tagCodes.length === 0) return;

    // Find the target tag code for the selected filter
    let targetCode = -1;
    let currJ = 0;
    filters.forEach((f, i) => {
      if (f.enabled) {
        if (i === selectedFilterIdx) {
          targetCode = currJ + 2;
        }
        currJ++;
      }
    });

    if (targetCode === -1) return;

    const start = selectedLine !== null ? selectedLine : 0;
    let found = -1;

    if (reverse) {
      for (let r = start - 1; r >= 0; r--) {
        if (tagCodes[r] === targetCode) {
          found = r;
          break;
        }
      }
      // Wrap around to bottom if not found from current pos
      if (found === -1) {
        for (let r = tagCodes.length - 1; r > start; r--) {
          if (tagCodes[r] === targetCode) {
            found = r;
            break;
          }
        }
      }
    } else {
      for (let r = start + 1; r < tagCodes.length; r++) {
        if (tagCodes[r] === targetCode) {
          found = r;
          break;
        }
      }
      // Wrap around to top if not found from current pos
      if (found === -1) {
        for (let r = 0; r < start; r++) {
          if (tagCodes[r] === targetCode) {
            found = r;
            break;
          }
        }
      }
    }

    if (found !== -1) {
      get().setSelectedLine(found);
    }
  },

  // Notes
  notes: {},
  noteEditLine: null,
  setNoteEditLine: (line) => set({ noteEditLine: line }),
  addNote: (filepath, line, text) => {
    set((state) => {
      const fileNotes = state.notes[filepath] || {};
      return {
        notes: {
          ...state.notes,
          [filepath]: {
            ...fileNotes,
            [line]: text,
          },
        },
      };
    });
  },
  deleteNote: (filepath, line) => {
    set((state) => {
      const fileNotes = { ...(state.notes[filepath] || {}) };
      delete fileNotes[line];
      return {
        notes: {
          ...state.notes,
          [filepath]: fileNotes,
        },
      };
    });
  },
  saveNotes: async () => {
    const { activeFile, notes } = get();
    if (!activeFile) return;

    const lastDotIdx = activeFile.lastIndexOf('.');
    const notePath = lastDotIdx !== -1 
      ? activeFile.substring(0, lastDotIdx) + '.note'
      : activeFile + '.note';

    const fileNotes = notes[activeFile] || {};

    try {
      await invoke('write_text_file', {
        path: notePath,
        content: JSON.stringify(fileNotes, null, 2),
      });
      console.log('Notes saved successfully to', notePath);
    } catch (err) {
      console.error('Failed to save notes:', err);
      throw err;
    }
  },
  loadNotesForFile: async (filepath) => {
    if (get().notes[filepath] && Object.keys(get().notes[filepath]).length > 0) return;

    const lastDotIdx = filepath.lastIndexOf('.');
    const notePath = lastDotIdx !== -1 
      ? filepath.substring(0, lastDotIdx) + '.note'
      : filepath + '.note';

    try {
      const content = await invoke<string>('read_text_file', { path: notePath });
      if (content) {
        const parsed = JSON.parse(content);
        const fileNotes: Record<number, string> = {};
        for (const [key, value] of Object.entries(parsed)) {
          fileNotes[parseInt(key)] = value as string;
        }
        set((state) => ({
          notes: {
            ...state.notes,
            [filepath]: fileNotes,
          },
        }));
      }
    } catch (err) {
      console.log('No existing notes file found for', filepath);
    }
  },
}),
    {
      name: 'log-analyzer-prefs',
      // Persist user preference keys only — filters are per-session (not persisted)
      partialize: (state) => ({
        theme: state.theme,
        editorFontSize: state.editorFontSize,
        editorFontFamily: state.editorFontFamily,
        showLineNumbers: state.showLineNumbers,
        lineSpacing: state.lineSpacing,
        defaultEncoding: state.defaultEncoding,
        uiFontSize: state.uiFontSize,
        uiFontFamily: state.uiFontFamily,
        recentFiles: state.recentFiles,
      }),
      onRehydrateStorage: () => (state) => {
        // Re-apply theme class to DOM after rehydration
        if (state?.theme === 'dark') {
          document.documentElement.classList.add('dark');
        } else {
          document.documentElement.classList.remove('dark');
        }
      },
    }
  )
);
