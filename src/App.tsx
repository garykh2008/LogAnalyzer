import React, { useState, useEffect } from 'react';
import { useStore, StreamDelta } from './store';
import { LogViewport } from './components/LogViewport';
import { SidebarPanels } from './components/SidebarPanels';
import { SearchOverlay } from './components/SearchOverlay';
import { invoke } from '@tauri-apps/api/core';
import { getCurrentWindow } from '@tauri-apps/api/window';
import { listen } from '@tauri-apps/api/event';
import readmeContent from '../README.md?raw';
import appLogo from './assets/logo.png';
import {
  Folder,
  Filter,
  BookOpen,
  Settings,
  Minus,
  Square,
  X,
  Check,
  Sun,
  Moon,
  Info
} from 'lucide-react';

const appWindow = getCurrentWindow();

export default function App() {
  const theme = useStore((s) => s.theme);
  const setTheme = useStore((s) => s.setTheme);
  const activeFile = useStore((s) => s.activeFile);
  const loadLog = useStore((s) => s.loadLog);
  const lineCount = useStore((s) => s.lineCount);
  const selectedLine = useStore((s) => s.selectedLine);
  const setSelectedLine = useStore((s) => s.setSelectedLine);
  const selectedLines = useStore((s) => s.selectedLines);
  const copySelection = useStore((s) => s.copySelection);
  const saveLog = useStore((s) => s.saveLog);
  const selectAll = useStore((s) => s.selectAll);
  const filters = useStore((s) => s.filters);
  const showFilteredOnly = useStore((s) => s.showFilteredOnly);
  const toggleShowFilteredOnly = useStore((s) => s.toggleShowFilteredOnly);
  const importFilters = useStore((s) => s.importFilters);
  const saveFiltersAs = useStore((s) => s.saveFiltersAs);
  const quickSaveFilters = useStore((s) => s.quickSaveFilters);
  const clearFilters = useStore((s) => s.clearFilters);
  const notes = useStore((s) => s.notes);
  const deleteNote = useStore((s) => s.deleteNote);
  const saveNotes = useStore((s) => s.saveNotes);
  const recentFiles = useStore((s) => s.recentFiles);
  const clearRecentFiles = useStore((s) => s.clearRecentFiles);
  const filtersModified = useStore((s) => s.filtersModified);
  const activeTab = useStore((s) => s.activeTab);
  const setActiveTab = useStore((s) => s.setActiveTab);
  const isSidebarOpen = useStore((s) => s.isSidebarOpen);
  const setIsSidebarOpen = useStore((s) => s.setIsSidebarOpen);
  const setNoteEditLine = useStore((s) => s.setNoteEditLine);
  const editorFontSize = useStore((s) => s.editorFontSize);
  const editorFontFamily = useStore((s) => s.editorFontFamily);
  const showLineNumbers = useStore((s) => s.showLineNumbers);
  const lineSpacing = useStore((s) => s.lineSpacing);
  const defaultEncoding = useStore((s) => s.defaultEncoding);
  const uiFontSize = useStore((s) => s.uiFontSize);
  const uiFontFamily = useStore((s) => s.uiFontFamily);
  const setPreferences = useStore((s) => s.setPreferences);
  const nextSearchMatch = useStore((s) => s.nextSearchMatch);
  const prevSearchMatch = useStore((s) => s.prevSearchMatch);
  const navigateFilterHit = useStore((s) => s.navigateFilterHit);
  const enableLiveStream = useStore((s) => s.enableLiveStream);
  const dbgviewPath = useStore((s) => s.dbgviewPath);
  const remoteHost = useStore((s) => s.remoteHost);
  const remotePort = useStore((s) => s.remotePort);
  const remoteUser = useStore((s) => s.remoteUser);
  const remoteDbgviewPath = useStore((s) => s.remoteDbgviewPath);
  const startFileTail = useStore((s) => s.startFileTail);
  const startDbgviewLocal = useStore((s) => s.startDbgviewLocal);
  const startDbgviewRemote = useStore((s) => s.startDbgviewRemote);
  const applyStreamDelta = useStore((s) => s.applyStreamDelta);

  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [activeMenu, setActiveMenu] = useState<string | null>(null);

  // Settings page overlays
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [activeSettingsTab, setActiveSettingsTab] = useState<'general' | 'logView' | 'appearance'>('general');

  // Help page overlays
  const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);
  const [isDocsOpen, setIsDocsOpen] = useState(false);
  const [isAboutOpen, setIsAboutOpen] = useState(false);

  // Paste-from-clipboard feedback
  const [pasteMsg, setPasteMsg] = useState<string | null>(null);

  // Remote DbgView connect dialog
  const [isRemoteOpen, setIsRemoteOpen] = useState(false);
  const [remotePassword, setRemotePassword] = useState('');
  const [remoteConnecting, setRemoteConnecting] = useState(false);
  const [remoteError, setRemoteError] = useState<string | null>(null);

  // Export notes helper
  const handleExportNotes = async () => {
    if (!activeFile) return;
    const fileNotes = notes[activeFile] || {};
    const sortedLines = Object.keys(fileNotes).map(Number).sort((a, b) => a - b);
    if (sortedLines.length === 0) {
      alert("No notes in this file to export!");
      return;
    }

    try {
      const path = await invoke<string | null>('save_file_dialog', {
        defaultName: 'notes.txt',
        extension: 'txt',
      });
      if (!path) return;

      const logLines = await invoke<string[]>('get_lines', {
        filepath: activeFile,
        indices: sortedLines,
      });

      let content = '';
      sortedLines.forEach((lineIdx, i) => {
        const noteText = fileNotes[lineIdx];
        const logLine = logLines[i].replace(/[\r\n]+$/, '');
        content += `Line ${lineIdx + 1}:\n[LOG]: ${logLine}\n[NOTE]: ${noteText}\n\n`;
      });

      await invoke('write_text_file', { path, content });
      alert("Notes exported successfully!");
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  // Keyboard Shortcuts Hook
  useEffect(() => {
    const handleGlobalKeys = async (e: KeyboardEvent) => {
      const activeEl = document.activeElement;
      const isInputFocused = activeEl && (activeEl.tagName === 'INPUT' || activeEl.tagName === 'TEXTAREA');

      // 1. Ctrl+C -> Copy Selection
      if (e.ctrlKey && e.key.toLowerCase() === 'c' && !isInputFocused) {
        e.preventDefault();
        await copySelection();
      }
      // 1.5. Ctrl+A -> Select all lines in the current view
      else if (e.ctrlKey && e.key.toLowerCase() === 'a' && !isInputFocused) {
        e.preventDefault();
        selectAll();
      }
      // 2. Ctrl+O -> Open File
      else if (e.ctrlKey && e.key.toLowerCase() === 'o') {
        e.preventDefault();
        try {
          const path = await invoke<string | null>('open_file_dialog');
          if (path) await loadLog(path);
        } catch (err) {
          console.error(err);
        }
      }
      // 2.5. Ctrl+S -> Save Notes
      else if (e.ctrlKey && e.key.toLowerCase() === 's') {
        e.preventDefault();
        try {
          await saveNotes();
        } catch (err) {
          console.error('Failed to save notes:', err);
        }
      }
      // 3. Ctrl+F -> Search
      else if (e.ctrlKey && e.key.toLowerCase() === 'f') {
        e.preventDefault();
        setIsSearchOpen((prev) => !prev);
      }
      // 4. Ctrl+H -> Toggle Filtered Mode
      else if (e.ctrlKey && e.key.toLowerCase() === 'h') {
        e.preventDefault();
        toggleShowFilteredOnly();
      }
      // 5. Ctrl+Shift+L -> Files Tab
      else if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'l') {
        e.preventDefault();
        setActiveTab('files');
        setIsSidebarOpen(true);
      }
      // 6. Ctrl+Shift+F -> Filters Tab
      else if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'f') {
        e.preventDefault();
        setActiveTab('filters');
        setIsSidebarOpen(true);
      }
      // 7. Ctrl+Shift+N -> Notes Tab
      else if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'n') {
        e.preventDefault();
        setActiveTab('notes');
        setIsSidebarOpen(true);
      }
      // 8. Ctrl+G -> Go to Line
      else if (e.ctrlKey && e.key.toLowerCase() === 'g') {
        e.preventDefault();
        const input = prompt(`Go to line (1 - ${lineCount}):`);
        if (input) {
          const line = parseInt(input);
          if (!isNaN(line) && line >= 1 && line <= lineCount) {
            setSelectedLine(line - 1);
          }
        }
      }
      // 9. C -> Add/Edit note
      else if (e.key.toLowerCase() === 'c' && !e.ctrlKey && !e.shiftKey && !e.altKey && !isInputFocused) {
        if (selectedLine !== null) {
          e.preventDefault();
          setNoteEditLine(selectedLine);
        }
      }
      // 10. Delete -> Remove note
      else if (e.key === 'Delete' && !isInputFocused) {
        if (selectedLine !== null && activeFile) {
          if (notes[activeFile]?.hasOwnProperty(selectedLine)) {
            e.preventDefault();
            deleteNote(activeFile, selectedLine);
          }
        }
      }
      // 11. F3 -> Next search match (or Shift+F3 for previous)
      else if (e.key === 'F3') {
        e.preventDefault();
        if (activeEl && activeEl.tagName === 'TEXTAREA') return;

        if (e.shiftKey) {
          prevSearchMatch();
        } else {
          nextSearchMatch();
        }
      }
      // 12. F2 -> Previous search match
      else if (e.key === 'F2') {
        e.preventDefault();
        if (activeEl && activeEl.tagName === 'TEXTAREA') return;

        prevSearchMatch();
      }
      // 13. Ctrl + ArrowLeft/ArrowRight -> Navigate filter hits
      else if (e.ctrlKey && !isInputFocused) {
        if (e.key === 'ArrowLeft') {
          e.preventDefault();
          navigateFilterHit(true);
        } else if (e.key === 'ArrowRight') {
          e.preventDefault();
          navigateFilterHit(false);
        }
      }
      // 14. H -> Open shortcuts dialog
      else if (e.key.toLowerCase() === 'h' && !e.ctrlKey && !e.shiftKey && !e.altKey && !isInputFocused) {
        e.preventDefault();
        setIsShortcutsOpen(true);
      }
    };

    window.addEventListener('keydown', handleGlobalKeys);
    return () => window.removeEventListener('keydown', handleGlobalKeys);
  }, [lineCount, loadLog, toggleShowFilteredOnly, setSelectedLine, selectedLine, selectedLines, copySelection, selectAll, activeFile, notes, nextSearchMatch, prevSearchMatch, navigateFilterHit, setIsShortcutsOpen, saveNotes]);

  // Handle active menu closures
  useEffect(() => {
    const closeMenu = () => setActiveMenu(null);
    window.addEventListener('click', closeMenu);
    return () => window.removeEventListener('click', closeMenu);
  }, []);

  // Listen to Tauri's native window drag and drop events
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    
    const setupDragDrop = async () => {
      unlisten = await listen<any>('tauri://drag-drop', async (event) => {
        const paths = event.payload?.paths;
        if (paths && paths.length > 0) {
          const filepath = paths[0];
          await loadLog(filepath);
        }
      });
    };

    setupDragDrop();
    return () => {
      if (unlisten) unlisten();
    };
  }, [loadLog]);

  // Listen to CLI file arguments: LogAnalyzer.exe [file1 file2 *.log ...] [-f filter.tat]
  useEffect(() => {
    let unlistenFiles: (() => void) | null = null;
    let unlistenFilter: (() => void) | null = null;

    const setupCliListeners = async () => {
      // Multiple log files (with glob expansion done by Rust)
      unlistenFiles = await listen<string[]>('cli-open-files', async (event) => {
        const paths = event.payload;
        if (paths && paths.length > 0) {
          for (const filepath of paths) {
            await loadLog(filepath);
          }
        }
      });

      // Optional .tat filter file
      unlistenFilter = await listen<string>('cli-open-filter', async (event) => {
        const filterPath = event.payload;
        if (filterPath) {
          await useStore.getState().loadFiltersFromPath(filterPath);
        }
      });
    };

    setupCliListeners();
    return () => {
      if (unlistenFiles) unlistenFiles();
      if (unlistenFilter) unlistenFilter();
    };
  }, [loadLog]);

  // Listen to live stream append deltas from the backend
  useEffect(() => {
    let unlisten: (() => void) | null = null;
    const setup = async () => {
      unlisten = await listen<StreamDelta>('stream-appended', (event) => {
        if (event.payload) applyStreamDelta(event.payload);
      });
    };
    setup();
    return () => {
      if (unlisten) unlisten();
    };
  }, [applyStreamDelta]);

  // Block native browser page zoom on Ctrl+Wheel
  useEffect(() => {
    const blockZoom = (e: WheelEvent) => {
      if (e.ctrlKey) {
        e.preventDefault();
      }
    };
    window.addEventListener('wheel', blockZoom, { passive: false });
    return () => window.removeEventListener('wheel', blockZoom);
  }, []);

  // Global paste handler: Ctrl+V on viewport pastes clipboard as a new log tab
  useEffect(() => {
    const handlePaste = async (e: ClipboardEvent) => {
      // Ignore paste inside input / textarea / contenteditable
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || (e.target as HTMLElement)?.isContentEditable) return;

      const text = e.clipboardData?.getData('text/plain') ?? '';
      if (!text.trim()) return;

      e.preventDefault();
      try {
        setPasteMsg('正在載入剪貼簿內容…');
        const tmpPath = await invoke<string>('create_temp_log', { content: text });
        await loadLog(tmpPath);
        const lineCount = text.split('\n').length;
        setPasteMsg(`✓ 已從剪貼簿載入 ${lineCount.toLocaleString()} 行`);
      } catch (err) {
        console.error('Paste failed:', err);
        setPasteMsg('✗ 載入失敗');
      } finally {
        setTimeout(() => setPasteMsg(null), 3000);
      }
    };
    window.addEventListener('paste', handlePaste);
    return () => window.removeEventListener('paste', handlePaste);
  }, [loadLog]);

  const renderReadmeMarkdown = (text: string) => {
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let inCodeBlock = false;
    let codeContent: string[] = [];

    const formatInline = (str: string): React.ReactNode[] => {
      const parts: React.ReactNode[] = [];
      let lastIdx = 0;
      const regex = /(\*\*.*?\*\*|`.*?`)/g;
      let match;
      let key = 0;

      while ((match = regex.exec(str)) !== null) {
        const matchStr = match[0];
        const matchIdx = match.index;

        if (matchIdx > lastIdx) {
          parts.push(str.substring(lastIdx, matchIdx));
        }

        if (matchStr.startsWith('**') && matchStr.endsWith('**')) {
          parts.push(<strong key={key++} className="font-bold text-accent dark:text-accent-hover">{matchStr.slice(2, -2)}</strong>);
        } else if (matchStr.startsWith('`') && matchStr.endsWith('`')) {
          parts.push(<code key={key++} className="bg-sidebar px-1 py-0.5 border border-border rounded font-mono ui-text-xs text-accent dark:text-accent font-semibold">{matchStr.slice(1, -1)}</code>);
        }

        lastIdx = regex.lastIndex;
      }

      if (lastIdx < str.length) {
        parts.push(str.substring(lastIdx));
      }

      return parts.length > 0 ? parts : [str];
    };

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];

      if (line.trim().startsWith('```')) {
        if (inCodeBlock) {
          elements.push(
            <pre key={`code-${i}`} className="bg-sidebar dark:bg-activity border border-border rounded-lg p-3 font-mono ui-text-xs my-2 select-text overflow-x-auto text-gray-750 dark:text-gray-300">
              <code>{codeContent.join('\n')}</code>
            </pre>
          );
          codeContent = [];
          inCodeBlock = false;
        } else {
          inCodeBlock = true;
        }
        continue;
      }

      if (inCodeBlock) {
        codeContent.push(line);
        continue;
      }

      if (line.startsWith('# ')) {
        elements.push(<h2 key={i} className="text-sm font-bold text-accent border-b border-border pb-1 mt-4 mb-2 select-text">{formatInline(line.slice(2))}</h2>);
        continue;
      }
      if (line.startsWith('## ')) {
        elements.push(<h3 key={i} className="text-xs font-bold text-accent mt-3 mb-1.5 select-text">{formatInline(line.slice(3))}</h3>);
        continue;
      }
      if (line.startsWith('### ')) {
        elements.push(<h4 key={i} className="text-xs font-bold text-foreground/80 mt-2 mb-1 select-text">{formatInline(line.slice(4))}</h4>);
        continue;
      }
      if (line.startsWith('* ') || line.startsWith('- ')) {
        elements.push(<li key={i} className="ml-4 list-disc text-gray-700 dark:text-gray-350 text-xs py-0.5 select-text">{formatInline(line.slice(2))}</li>);
        continue;
      }
      if (line.trim().startsWith('|')) {
        if (line.includes('---')) continue;
        const cols = line.split('|').map(c => c.trim()).filter(c => c !== '');
        elements.push(
          <div key={i} className="flex border-b border-border/30 py-1.5 ui-text-xs font-mono select-text">
            {cols.map((col, idx) => (
              <span key={idx} className="flex-1 truncate pr-2">{formatInline(col)}</span>
            ))}
          </div>
        );
        continue;
      }
      if (line.trim() === '---') {
        elements.push(<hr key={i} className="border-border/40 my-3" />);
        continue;
      }
      if (!line.trim()) {
        elements.push(<div key={i} className="h-1.5" />);
        continue;
      }
      elements.push(<p key={i} className="text-xs text-gray-600 dark:text-gray-400 my-1 leading-relaxed select-text">{formatInline(line)}</p>);
    }

    return elements;
  };
  const toggleTab = (tab: 'files' | 'filters' | 'notes') => {
    if (activeTab === tab && isSidebarOpen) {
      setIsSidebarOpen(false);
    } else {
      setActiveTab(tab);
      setIsSidebarOpen(true);
    }
  };

  const handleMenuClick = (e: React.MouseEvent, menu: string) => {
    e.stopPropagation();
    setActiveMenu(activeMenu === menu ? null : menu);
  };

  const handleMenuMouseEnter = (menu: string) => {
    // When a menu is already open, hovering another menu item switches to it
    if (activeMenu !== null) {
      setActiveMenu(menu);
    }
  };

  const activeFilename = activeFile ? activeFile.split(/[/\\]/).pop() : null;
  const isClipboardFile = activeFilename?.startsWith('loganalyzer_clipboard_') ?? false;
  const displayFilename = isClipboardFile ? '📋 Clipboard' : activeFilename;
  const enabledFiltersCount = filters.filter((f) => f.enabled).length;
  const notesCount = Object.keys(notes[activeFile || ''] || {}).length;

  return (
    <div className={`h-screen w-screen flex flex-col overflow-hidden select-none bg-background text-foreground ${theme}`} style={{ '--ui-font-size': `${uiFontSize}px` } as React.CSSProperties}>
      {/* 1. Custom Frameless Titlebar */}
      <div 
        data-tauri-drag-region
        className="h-10 border-b border-border flex items-center justify-between pl-3 select-none bg-sidebar dark:bg-activity z-50 shrink-0 cursor-default"
      >
        {/* Left: App Logo & Menus */}
        <div className="flex items-center gap-2 select-none">
          <img src={appLogo} className="w-4 h-4 mr-1 animate-pulse select-none" />
          
          {/* Custom Dropdown Menus */}
          <div className="flex items-center text-xs font-medium">
            {/* File Menu */}
            <div className="relative">
              <button
                onClick={(e) => handleMenuClick(e, 'file')}
                onMouseEnter={() => handleMenuMouseEnter('file')}
                className="px-2.5 py-1 rounded-md hover:bg-hover transition-colors cursor-default"
              >
                File
              </button>
              {activeMenu === 'file' && (
                <div className="absolute top-full left-0 mt-1 w-52 bg-card border border-border rounded-lg shadow-2xl py-1.5 z-55 text-xs font-normal">
                  <button
                    onClick={async () => {
                      const path = await invoke<string | null>('open_file_dialog');
                      if (path) await loadLog(path);
                      setActiveMenu(null);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                  >
                    <span>Open Log...</span>
                    <span className="ui-text-xs text-gray-400 font-mono">Ctrl+O</span>
                  </button>

                  {enableLiveStream && (
                    <button
                      onClick={async () => {
                        const path = await invoke<string | null>('open_file_dialog');
                        if (path) await startFileTail(path);
                        setActiveMenu(null);
                      }}
                      className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                    >
                      <span>Tail File (Live)...</span>
                      <span className="ui-text-xs text-accent font-mono">◉</span>
                    </button>
                  )}

                  {enableLiveStream && (
                    <button
                      onClick={async () => {
                        setActiveMenu(null);
                        if (!useStore.getState().dbgviewPath) {
                          alert('Please set the DbgView.exe path in Settings first.');
                          setIsSettingsOpen(true);
                          return;
                        }
                        try {
                          await startDbgviewLocal();
                        } catch (err) {
                          alert('Failed to start DbgView capture:\n' + err);
                        }
                      }}
                      className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                    >
                      <span>Capture DbgView (Kernel)...</span>
                      <span className="ui-text-xs text-red-500 font-mono">◉</span>
                    </button>
                  )}

                  {enableLiveStream && (
                    <button
                      onClick={() => {
                        setActiveMenu(null);
                        setRemoteError(null);
                        setRemotePassword('');
                        setIsRemoteOpen(true);
                      }}
                      className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                    >
                      <span>Capture DbgView (Remote)...</span>
                      <span className="ui-text-xs text-red-500 font-mono">◉</span>
                    </button>
                  )}

                  {/* Open Recent Submenu */}
                  <div className="relative group/recent">
                    <button
                      className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors cursor-default"
                    >
                      <span>Open Recent</span>
                      <span className="ui-text-xs text-gray-400">▶</span>
                    </button>
                    <div className="absolute top-0 left-full ml-0.5 w-64 bg-card border border-border rounded-lg shadow-2xl py-1.5 hidden group-hover/recent:block text-xs font-normal">
                      {recentFiles.length === 0 ? (
                        <div className="px-3 py-2 text-gray-400 italic">No recent logs</div>
                      ) : (
                        <>
                          {recentFiles.map((filepath) => (
                            <button
                              key={filepath}
                              onClick={async () => {
                                await loadLog(filepath);
                                setActiveMenu(null);
                              }}
                              className="w-full text-left px-3 py-2 hover:bg-hover truncate transition-colors ui-text-xs font-mono text-foreground"
                              title={filepath}
                            >
                              {filepath.split(/[\\/]/).pop()}
                              <span className="block ui-text-3xs text-gray-400 truncate mt-0.5">{filepath}</span>
                            </button>
                          ))}
                          <div className="h-[1px] bg-border my-1" />
                          <button
                            onClick={() => {
                              clearRecentFiles();
                              setActiveMenu(null);
                            }}
                            className="w-full text-left px-3 py-1.5 hover:bg-hover text-red-500 transition-colors"
                          >
                            Clear Recent Files
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                  {activeFile && (
                    <>
                      <div className="h-[1px] bg-border my-1" />
                      <button
                        onClick={async () => {
                          setActiveMenu(null);
                          await saveLog();
                        }}
                        className="w-full text-left px-3 py-2 hover:bg-hover transition-colors"
                      >
                        Save Log As...
                      </button>
                    </>
                  )}
                  <div className="h-[1px] bg-border my-1" />
                  <button
                    onClick={() => importFilters()}
                    className="w-full text-left px-3 py-2 hover:bg-hover transition-colors"
                  >
                    Import Filters...
                  </button>
                  <button
                    onClick={() => quickSaveFilters()}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                  >
                    <span>Save Filters</span>
                    {filtersModified && <span className="w-1.5 h-1.5 rounded-full bg-accent mr-1" />}
                  </button>
                  <button
                    onClick={() => saveFiltersAs()}
                    className="w-full text-left px-3 py-2 hover:bg-hover transition-colors"
                  >
                    Save Filters As...
                  </button>
                  {filters.length > 0 && (
                    <button
                      onClick={() => {
                        clearFilters();
                        setActiveMenu(null);
                      }}
                      className="w-full text-left px-3 py-2 hover:bg-red-500/10 text-red-500 transition-colors"
                    >
                      Clear All Filters
                    </button>
                  )}
                  <div className="h-[1px] bg-border my-1" />
                  <button
                    onClick={() => setIsSettingsOpen(true)}
                    className="w-full text-left px-3 py-2 hover:bg-hover transition-colors"
                  >
                    Preferences...
                  </button>
                  <div className="h-[1px] bg-border my-1" />
                  <button
                    onClick={() => appWindow.close()}
                    className="w-full text-left px-3 py-2 hover:bg-red-500/10 text-red-500 flex justify-between items-center transition-colors"
                  >
                    <span>Exit</span>
                    <span className="ui-text-xs text-red-500/60 font-mono">Ctrl+Q</span>
                  </button>
                </div>
              )}
            </div>

            {/* Edit Menu */}
            <div className="relative">
              <button
                onClick={(e) => handleMenuClick(e, 'edit')}
                onMouseEnter={() => handleMenuMouseEnter('edit')}
                className="px-2.5 py-1 rounded-md hover:bg-hover transition-colors cursor-default"
              >
                Edit
              </button>
              {activeMenu === 'edit' && (
                <div className="absolute top-full left-0 mt-1 w-52 bg-card border border-border rounded-lg shadow-2xl py-1.5 z-55 text-xs font-normal">
                  <button
                    onClick={() => copySelection()}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                  >
                    <span>Copy Selected Lines</span>
                    <span className="ui-text-xs text-gray-400 font-mono">Ctrl+C</span>
                  </button>
                  <button
                    onClick={() => {
                      selectAll();
                      setActiveMenu(null);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                  >
                    <span>Select All Lines</span>
                    <span className="ui-text-xs text-gray-400 font-mono">Ctrl+A</span>
                  </button>
                  <div className="h-[1px] bg-border my-1" />
                  <button
                    onClick={() => setIsSearchOpen(true)}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                  >
                    <span>Find...</span>
                    <span className="ui-text-xs text-gray-400 font-mono">Ctrl+F</span>
                  </button>
                  <button
                    onClick={() => {
                      const input = prompt(`Go to line (1 - ${lineCount}):`);
                      if (input) {
                        const line = parseInt(input);
                        if (!isNaN(line) && line >= 1 && line <= lineCount) {
                          setSelectedLine(line - 1);
                        }
                      }
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                  >
                    <span>Go to Line...</span>
                    <span className="ui-text-xs text-gray-400 font-mono">Ctrl+G</span>
                  </button>
                </div>
              )}
            </div>

            {/* View Menu */}
            <div className="relative">
              <button
                onClick={(e) => handleMenuClick(e, 'view')}
                onMouseEnter={() => handleMenuMouseEnter('view')}
                className="px-2.5 py-1 rounded-md hover:bg-hover transition-colors cursor-default"
              >
                View
              </button>
              {activeMenu === 'view' && (
                <div className="absolute top-full left-0 mt-1 w-52 bg-card border border-border rounded-lg shadow-2xl py-1.5 z-55 text-xs font-normal">
                  <button
                    onClick={() => {
                      setActiveTab('files');
                      setIsSidebarOpen(true);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                  >
                    <span>Log Files</span>
                    <span className="ui-text-xs text-gray-400 font-mono">Ctrl+Shift+L</span>
                  </button>
                  <button
                    onClick={() => {
                      setActiveTab('filters');
                      setIsSidebarOpen(true);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                  >
                    <span>Filters</span>
                    <span className="ui-text-xs text-gray-400 font-mono">Ctrl+Shift+F</span>
                  </button>
                  <button
                    onClick={() => {
                      setActiveTab('notes');
                      setIsSidebarOpen(true);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                  >
                    <span>Notes</span>
                    <span className="ui-text-xs text-gray-400 font-mono">Ctrl+Shift+N</span>
                  </button>
                  <div className="h-[1px] bg-border my-1" />
                  <button
                    onClick={() => toggleShowFilteredOnly()}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                  >
                    <span>Show Filtered Only</span>
                    <span className="flex items-center gap-1.5">
                      {showFilteredOnly && <Check size={12} className="text-accent" />}
                      <span className="ui-text-xs text-gray-400 font-mono">Ctrl+H</span>
                    </span>
                  </button>
                  <button
                    onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                  >
                    <span>Toggle Theme</span>
                    <span className="flex items-center gap-2">
                      {theme === 'dark' ? <Moon size={12} /> : <Sun size={12} />}
                    </span>
                  </button>
                </div>
              )}
            </div>

            {/* Notes Menu */}
            <div className="relative">
              <button
                onClick={(e) => handleMenuClick(e, 'notesMenu')}
                onMouseEnter={() => handleMenuMouseEnter('notesMenu')}
                className="px-2.5 py-1 rounded-md hover:bg-hover transition-colors cursor-default"
              >
                Notes
              </button>
              {activeMenu === 'notesMenu' && (
                <div className="absolute top-full left-0 mt-1 w-52 bg-card border border-border rounded-lg shadow-2xl py-1.5 z-55 text-xs font-normal">
                  <button
                    onClick={() => {
                      if (selectedLine !== null) {
                        setNoteEditLine(selectedLine);
                      } else {
                        alert('Please select a line first to add/edit a note.');
                      }
                      setActiveMenu(null);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                  >
                    <span>Add/Edit Note</span>
                    <span className="ui-text-xs text-gray-400 font-mono">C</span>
                  </button>
                  <button
                    onClick={() => {
                      if (selectedLine !== null && activeFile) {
                        deleteNote(activeFile, selectedLine);
                      } else {
                        alert('Please select a line with a note first.');
                      }
                      setActiveMenu(null);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors text-red-500"
                  >
                    <span>Remove Note</span>
                    <span className="ui-text-xs text-red-400 font-mono">Delete</span>
                  </button>
                  <div className="h-[1px] bg-border my-1" />
                  <button
                    onClick={async () => {
                      try {
                        await saveNotes();
                        alert('Notes saved successfully!');
                      } catch (err) {
                        alert('Failed to save notes: ' + err);
                      }
                      setActiveMenu(null);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                  >
                    <span>Save Notes</span>
                    <span className="ui-text-xs text-gray-400 font-mono">Ctrl+S</span>
                  </button>
                  <div className="h-[1px] bg-border my-1" />
                  <button
                    onClick={() => {
                      handleExportNotes();
                      setActiveMenu(null);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-hover transition-colors"
                  >
                    Export Notes to Text...
                  </button>
                </div>
              )}
            </div>

            {/* Help Menu */}
            <div className="relative">
              <button
                onClick={(e) => handleMenuClick(e, 'help')}
                onMouseEnter={() => handleMenuMouseEnter('help')}
                className="px-2.5 py-1 rounded-md hover:bg-hover transition-colors cursor-default"
              >
                Help
              </button>
              {activeMenu === 'help' && (
                <div className="absolute top-full left-0 mt-1 w-52 bg-card border border-border rounded-lg shadow-2xl py-1.5 z-55 text-xs font-normal">
                  <button
                    onClick={() => {
                      setIsShortcutsOpen(true);
                      setActiveMenu(null);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-hover flex justify-between items-center transition-colors"
                  >
                    <span>Keyboard Shortcuts</span>
                    <span className="ui-text-xs text-gray-400 font-mono">H</span>
                  </button>
                  <button
                    onClick={() => {
                      setIsDocsOpen(true);
                      setActiveMenu(null);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-hover transition-colors"
                  >
                    <span>Documentation</span>
                  </button>
                  <div className="h-[1px] bg-border my-1" />
                  <button
                    onClick={() => {
                      setIsAboutOpen(true);
                      setActiveMenu(null);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-hover transition-colors"
                  >
                    <span>About Log Analyzer</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Middle: Active Filename */}
        <div data-tauri-drag-region className="flex-1 text-center text-xs font-semibold text-gray-500 dark:text-gray-400 truncate px-4">
          {displayFilename ? `${displayFilename} - Log Analyzer` : 'Log Analyzer V3.0'}
        </div>

        {/* Right: Window Controls */}
        <div className="flex items-center h-full select-none shrink-0">
          <button
            onClick={() => appWindow.minimize()}
            className="h-full px-4 hover:bg-hover text-gray-500 flex items-center justify-center transition-colors"
            title="Minimize"
          >
            <Minus size={14} />
          </button>
          <button
            onClick={() => appWindow.toggleMaximize()}
            className="h-full px-4 hover:bg-hover text-gray-500 flex items-center justify-center transition-colors"
            title="Maximize"
          >
            <Square size={10} />
          </button>
          <button
            onClick={() => appWindow.close()}
            className="h-full px-4 hover:bg-red-500 hover:text-white text-gray-500 flex items-center justify-center transition-colors"
            title="Close"
          >
            <X size={14} />
          </button>
        </div>
      </div>

      {/* 2. Main Layout Workspace */}
      <div className="flex-1 flex flex-row overflow-hidden relative">
        
        {/* Left Side Activity Bar */}
        <div className="w-12 h-full border-r border-border bg-sidebar dark:bg-activity flex flex-col items-center justify-between py-3 select-none shrink-0 z-45">
          <div className="flex flex-col items-center gap-2 w-full">
            {/* Log Files Tab */}
            <div className="relative w-full flex justify-center py-1">
              <button
                onClick={() => toggleTab('files')}
                className={`p-2 rounded-lg transition-all ${
                  activeTab === 'files' && isSidebarOpen
                    ? 'text-accent'
                    : 'hover:bg-hover text-gray-400'
                }`}
                title="Log Files (Ctrl+Shift+L)"
              >
                <Folder size={18} />
              </button>
              {activeTab === 'files' && isSidebarOpen && (
                <div className="absolute left-0 top-1 bottom-1 w-[3px] bg-accent rounded-r-md" />
              )}
            </div>

            {/* Filters Tab */}
            <div className="relative w-full flex justify-center py-1">
              <button
                onClick={() => toggleTab('filters')}
                className={`relative p-2 rounded-lg transition-all ${
                  activeTab === 'filters' && isSidebarOpen
                    ? 'text-accent'
                    : 'hover:bg-hover text-gray-400'
                }`}
                title="Filters (Ctrl+Shift+F)"
              >
                <Filter size={18} />
                {enabledFiltersCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 min-w-[14px] h-[14px] px-0.5 rounded-full bg-accent text-[8px] font-bold text-white flex items-center justify-center shadow-sm">
                    {enabledFiltersCount}
                  </span>
                )}
              </button>
              {activeTab === 'filters' && isSidebarOpen && (
                <div className="absolute left-0 top-1 bottom-1 w-[3px] bg-accent rounded-r-md" />
              )}
            </div>

            {/* Notes Tab */}
            <div className="relative w-full flex justify-center py-1">
              <button
                onClick={() => toggleTab('notes')}
                className={`relative p-2 rounded-lg transition-all ${
                  activeTab === 'notes' && isSidebarOpen
                    ? 'text-accent'
                    : 'hover:bg-hover text-gray-400'
                }`}
                title="Notes (Ctrl+Shift+N)"
              >
                <BookOpen size={18} />
                {notesCount > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 min-w-[14px] h-[14px] px-0.5 rounded-full bg-amber-500 text-[8px] font-bold text-white flex items-center justify-center shadow-sm">
                    {notesCount}
                  </span>
                )}
              </button>
              {activeTab === 'notes' && isSidebarOpen && (
                <div className="absolute left-0 top-1 bottom-1 w-[3px] bg-accent rounded-r-md" />
              )}
            </div>
          </div>

          {/* Bottom actions */}
          <div className="flex flex-col items-center gap-2 w-full">
            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="p-2 rounded-lg hover:bg-hover text-gray-400 transition-colors cursor-pointer"
              title="Toggle Theme"
            >
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            <button
              onClick={() => setIsSettingsOpen(true)}
              className="p-2 rounded-lg hover:bg-hover text-gray-400 transition-colors cursor-pointer"
              title="Workspace Settings"
            >
              <Settings size={18} />
            </button>
          </div>
        </div>

        {/* Collapsible Sidebar */}
        {isSidebarOpen && <SidebarPanels activeTab={activeTab} />}

        {/* Central Log Viewport */}
        <div className="flex-1 flex flex-col overflow-hidden relative">
          <LogViewport />

          {/* Floating Search Overlay */}
          <SearchOverlay 
            isOpen={isSearchOpen} 
            onClose={() => setIsSearchOpen(false)} 
          />
        </div>
      </div>

      {/* 3. Interactive Status Bar */}
      <div className="h-6 border-t border-border bg-sidebar dark:bg-activity flex items-center justify-between px-4 ui-text-sm text-gray-500 select-none shrink-0 z-50">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1 text-accent font-semibold">
            <Info size={11} />
            <span>Ready</span>
          </span>
          {activeFile && (
            <span className="text-gray-400 truncate max-w-sm font-mono">
              {activeFile}
            </span>
          )}
        </div>

        <div className="flex items-center gap-4">
          <button
            onClick={() => toggleShowFilteredOnly()}
            className="hover:text-accent font-semibold flex items-center gap-1 cursor-pointer transition-colors bg-transparent border-0 p-0 ui-text-sm text-gray-500"
            title="Toggle Filter Mode (Ctrl+H)"
          >
            <span>Mode:</span>
            <span className="text-accent underline decoration-dotted underline-offset-2">
              {showFilteredOnly ? 'Filtered View' : 'Full Log'}
            </span>
          </button>

          <button
            onClick={() => {
              const input = prompt(`Go to line (1 - ${lineCount}):`);
              if (input) {
                const line = parseInt(input);
                if (!isNaN(line) && line >= 1 && line <= lineCount) {
                  setSelectedLine(line - 1);
                }
              }
            }}
            className="hover:text-accent font-semibold cursor-pointer transition-colors bg-transparent border-0 p-0 ui-text-sm text-gray-500"
            title="Go to Line (Ctrl+G)"
          >
            Total: {lineCount.toLocaleString()} lines
          </button>

          {selectedLine !== null && (
            <span className="font-mono font-semibold text-gray-600 dark:text-gray-300">
              Ln {selectedLine + 1}
            </span>
          )}

          <span className="font-semibold select-none uppercase">UTF-8 / UTF-16</span>
        </div>
      </div>

      {/* 4. Settings Dialog Modal */}
      {isSettingsOpen && (
        <div className="fixed inset-0 bg-black/55 backdrop-blur-[1.5px] flex items-center justify-center z-[100] select-none text-xs">
          <div className="bg-card border border-border shadow-2xl rounded-2xl w-[640px] h-[460px] flex flex-row overflow-hidden text-xs">
            {/* Left Tabs */}
            <div className="w-44 bg-sidebar border-r border-border flex flex-col py-4 select-none shrink-0">
              <span className="ui-text-2xs font-bold text-gray-400 uppercase tracking-wider px-4 mb-3">Preferences</span>
              <button
                onClick={() => setActiveSettingsTab('general')}
                className={`w-full text-left px-4 py-2.5 transition-colors font-medium cursor-pointer ${
                  activeSettingsTab === 'general' ? 'bg-hover text-accent font-semibold' : 'text-gray-500 hover:bg-hover/50'
                }`}
              >
                General Settings
              </button>
              <button
                onClick={() => setActiveSettingsTab('logView')}
                className={`w-full text-left px-4 py-2.5 transition-colors font-medium cursor-pointer ${
                  activeSettingsTab === 'logView' ? 'bg-hover text-accent font-semibold' : 'text-gray-500 hover:bg-hover/50'
                }`}
              >
                Log View Settings
              </button>
              <button
                onClick={() => setActiveSettingsTab('appearance')}
                className={`w-full text-left px-4 py-2.5 transition-colors font-medium cursor-pointer ${
                  activeSettingsTab === 'appearance' ? 'bg-hover text-accent font-semibold' : 'text-gray-500 hover:bg-hover/50'
                }`}
              >
                Appearance Settings
              </button>
            </div>

            {/* Right Config Content */}
            <div className="flex-1 flex flex-col justify-between p-6 overflow-y-auto bg-card">
              <div className="flex-1 overflow-y-auto pr-1">
                {/* General Page */}
                {activeSettingsTab === 'general' && (
                  <div className="flex flex-col gap-4">
                    <h2 className="text-sm font-bold text-gray-700 dark:text-zinc-300 border-b border-border pb-2">General Settings</h2>
                    <div className="flex flex-col gap-1.5">
                      <label className="font-semibold text-gray-600 dark:text-zinc-400">Default Encoding</label>
                      <span className="ui-text-xs text-gray-400">The character encoding used when opening log files.</span>
                      <select
                        value={defaultEncoding}
                        onChange={(e) => setPreferences({ defaultEncoding: e.target.value })}
                        className="w-full bg-sidebar border border-border rounded-lg p-2 focus:outline-none focus:border-accent"
                      >
                        <option value="UTF-8">UTF-8</option>
                        <option value="ASCII">ASCII</option>
                        <option value="ISO-8859-1">ISO-8859-1</option>
                        <option value="GBK">GBK</option>
                        <option value="Shift_JIS">Shift_JIS</option>
                      </select>
                    </div>

                    <div className="flex flex-col gap-1.5 border-t border-border pt-4">
                      <label className="flex items-center gap-2 cursor-pointer p-1.5 rounded hover:bg-hover">
                        <input
                          type="checkbox"
                          checked={enableLiveStream}
                          onChange={(e) => setPreferences({ enableLiveStream: e.target.checked })}
                          className="rounded text-accent border-border cursor-pointer"
                        />
                        <span className="font-semibold text-gray-600 dark:text-zinc-400">Enable Live Streaming</span>
                      </label>
                      <span className="ui-text-xs text-gray-400">
                        Tail a growing file in real time (foundation for live DbgView / kernel log capture).
                        Adds "Tail File (Live)" and "Capture DbgView (Kernel)" actions to the File menu.
                      </span>
                    </div>

                    {enableLiveStream && (
                      <div className="flex flex-col gap-1.5">
                        <label className="font-semibold text-gray-600 dark:text-zinc-400">DbgView.exe Path</label>
                        <span className="ui-text-xs text-gray-400">
                          Bring your own Sysinternals DebugView. Kernel capture launches it elevated (one UAC prompt).
                        </span>
                        <div className="flex items-center gap-2">
                          <input
                            type="text"
                            value={dbgviewPath}
                            onChange={(e) => setPreferences({ dbgviewPath: e.target.value })}
                            placeholder="C:\\Tools\\Dbgview.exe"
                            className="flex-1 bg-sidebar border border-border rounded-lg p-2 font-mono focus:outline-none focus:border-accent"
                          />
                          <button
                            onClick={async () => {
                              const path = await invoke<string | null>('open_exe_dialog');
                              if (path) setPreferences({ dbgviewPath: path });
                            }}
                            className="px-3 py-2 border border-border rounded-lg hover:bg-hover transition-colors cursor-pointer shrink-0 font-semibold"
                          >
                            Browse...
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Log View Page */}
                {activeSettingsTab === 'logView' && (
                  <div className="flex flex-col gap-4">
                    <h2 className="text-sm font-bold text-gray-700 dark:text-zinc-300 border-b border-border pb-2">Log View Settings</h2>
                    
                    {/* Font Family */}
                    <div className="flex flex-col gap-1.5">
                      <label className="font-semibold text-gray-600 dark:text-zinc-400">Font Family</label>
                      <span className="ui-text-xs text-gray-400">Choose the typeface for the log content.</span>
                      <select
                        value={editorFontFamily}
                        onChange={(e) => setPreferences({ editorFontFamily: e.target.value })}
                        className="w-full bg-sidebar border border-border rounded-lg p-2 focus:outline-none focus:border-accent"
                      >
                        <option value="Consolas">Consolas</option>
                        <option value="Courier New">Courier New</option>
                        <option value="Fira Code">Fira Code</option>
                        <option value="Source Code Pro">Source Code Pro</option>
                        <option value="monospace">System Monospace</option>
                      </select>
                    </div>

                    {/* Font Size */}
                    <div className="flex flex-col gap-1.5">
                      <label className="font-semibold text-gray-600 dark:text-zinc-400">Font Size (px)</label>
                      <input
                        type="number"
                        min={6}
                        max={72}
                        value={editorFontSize}
                        onChange={(e) => setPreferences({ editorFontSize: parseInt(e.target.value) || 12 })}
                        className="w-full bg-sidebar border border-border rounded-lg p-2 focus:outline-none focus:border-accent"
                      />
                    </div>

                    {/* Line Spacing */}
                    <div className="flex flex-col gap-1.5">
                      <label className="font-semibold text-gray-600 dark:text-zinc-400">Line Spacing (px)</label>
                      <input
                        type="number"
                        min={0}
                        max={50}
                        value={lineSpacing}
                        onChange={(e) => setPreferences({ lineSpacing: parseInt(e.target.value) || 0 })}
                        className="w-full bg-sidebar border border-border rounded-lg p-2 focus:outline-none focus:border-accent"
                      />
                    </div>

                    {/* Show Line Numbers */}
                    <label className="flex items-center gap-2 cursor-pointer p-1.5 rounded hover:bg-hover mt-1">
                      <input
                        type="checkbox"
                        checked={showLineNumbers}
                        onChange={(e) => setPreferences({ showLineNumbers: e.target.checked })}
                        className="rounded text-accent border-border cursor-pointer"
                      />
                      <span className="font-semibold text-gray-600 dark:text-zinc-400">Show Line Numbers</span>
                    </label>
                  </div>
                )}

                {/* Appearance Page */}
                {activeSettingsTab === 'appearance' && (
                  <div className="flex flex-col gap-4">
                    <h2 className="text-sm font-bold text-gray-700 dark:text-zinc-300 border-b border-border pb-2">Appearance Settings</h2>
                    
                    {/* Color Theme */}
                    <div className="flex flex-col gap-1.5">
                      <label className="font-semibold text-gray-600 dark:text-zinc-400">Color Theme</label>
                      <select
                        value={theme}
                        onChange={(e) => setTheme(e.target.value as 'dark' | 'light')}
                        className="w-full bg-sidebar border border-border rounded-lg p-2 focus:outline-none focus:border-accent"
                      >
                        <option value="light">Light Theme</option>
                        <option value="dark">Dark Theme</option>
                      </select>
                    </div>

                    {/* UI Font Family */}
                    <div className="flex flex-col gap-1.5">
                      <label className="font-semibold text-gray-600 dark:text-zinc-400">Interface Font Family</label>
                      <select
                        value={uiFontFamily}
                        onChange={(e) => setPreferences({ uiFontFamily: e.target.value })}
                        className="w-full bg-sidebar border border-border rounded-lg p-2 focus:outline-none focus:border-accent"
                      >
                        <option value="Inter">Inter</option>
                        <option value="Segoe UI">Segoe UI</option>
                        <option value="system-ui">System Default</option>
                      </select>
                    </div>

                    {/* UI Font Size */}
                    <div className="flex flex-col gap-1.5">
                      <label className="font-semibold text-gray-600 dark:text-zinc-400">Interface Font Size (px)</label>
                      <input
                        type="number"
                        min={8}
                        max={24}
                        value={uiFontSize}
                        onChange={(e) => setPreferences({ uiFontSize: parseInt(e.target.value) || 12 })}
                        className="w-full bg-sidebar border border-border rounded-lg p-2 focus:outline-none focus:border-accent"
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Close Button */}
              <div className="flex justify-end pt-4 select-none font-semibold shrink-0">
                <button
                  onClick={() => setIsSettingsOpen(false)}
                  className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors cursor-pointer"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 5. Keyboard Shortcuts Dialog Modal */}
      {isShortcutsOpen && (
        <div className="fixed inset-0 bg-black/55 backdrop-blur-[1.5px] flex items-center justify-center z-[100] select-none text-xs">
          <div className="bg-card border border-border shadow-2xl rounded-2xl w-[580px] max-h-[480px] flex flex-col p-5 overflow-hidden text-xs">
            <div className="flex items-center justify-between border-b border-border pb-3 mb-3 select-none">
              <span className="text-sm font-bold text-foreground">Keyboard Shortcuts</span>
              <button
                onClick={() => setIsShortcutsOpen(false)}
                className="text-gray-400 hover:text-foreground hover:bg-hover p-1 rounded-md transition-colors"
              >
                <X size={16} />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto pr-1">
              <div className="flex flex-col gap-4">
                <div>
                  <h4 className="font-bold text-accent mb-2 uppercase ui-text-xs tracking-wider">General</h4>
                  <table className="w-full text-left">
                    <tbody>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Open Log File</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">Ctrl + O</td></tr>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Go to Line...</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">Ctrl + G</td></tr>
                    </tbody>
                  </table>
                </div>

                <div>
                  <h4 className="font-bold text-accent mb-2 uppercase ui-text-xs tracking-wider">Search & Filters</h4>
                  <table className="w-full text-left">
                    <tbody>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Toggle Find Overlay</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">Ctrl + F</td></tr>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Toggle Show Filtered Only</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">Ctrl + H</td></tr>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Find Next Match</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">F3</td></tr>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Find Previous Match</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">F2</td></tr>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Navigate Filter Hit (Next / Prev)</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">Ctrl + Right / Left</td></tr>
                    </tbody>
                  </table>
                </div>

                <div>
                  <h4 className="font-bold text-accent mb-2 uppercase ui-text-xs tracking-wider">Sidebar Panels</h4>
                  <table className="w-full text-left">
                    <tbody>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Log Files Sidebar</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">Ctrl + Shift + L</td></tr>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Filters Sidebar</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">Ctrl + Shift + F</td></tr>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Notes Sidebar</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">Ctrl + Shift + N</td></tr>
                    </tbody>
                  </table>
                </div>

                <div>
                  <h4 className="font-bold text-accent mb-2 uppercase ui-text-xs tracking-wider">Log Editor & Notes</h4>
                  <table className="w-full text-left">
                    <tbody>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Add/Edit Note at Current Line</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">C</td></tr>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Remove Note at Current Line</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">Delete</td></tr>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Copy Selection</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">Ctrl + C</td></tr>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Select All Lines</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">Ctrl + A</td></tr>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Extend Selection (Range)</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">Shift + Click</td></tr>
                      <tr className="border-b border-border/40"><td className="py-1.5 text-gray-500 font-medium">Toggle Line in Selection</td><td className="py-1.5 text-right font-mono font-semibold text-gray-400">Ctrl + Click</td></tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
            
            <div className="flex justify-end pt-3 mt-1 border-t border-border/40 select-none">
              <button
                onClick={() => setIsShortcutsOpen(false)}
                className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors cursor-pointer font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 6. Documentation Dialog Modal */}
      {isDocsOpen && (
        <div className="fixed inset-0 bg-black/55 backdrop-blur-[1.5px] flex items-center justify-center z-[100] select-none text-xs">
          <div className="bg-card border border-border shadow-2xl rounded-2xl w-[600px] max-h-[500px] flex flex-col p-5 overflow-hidden text-xs">
            <div className="flex items-center justify-between border-b border-border pb-3 mb-3 select-none">
              <span className="text-sm font-bold text-foreground">Documentation</span>
              <button
                onClick={() => setIsDocsOpen(false)}
                className="text-gray-400 hover:text-foreground hover:bg-hover p-1 rounded-md transition-colors"
              >
                <X size={16} />
              </button>
            </div>
            
            <div className="flex-1 overflow-y-auto pr-1 select-text">
              <div className="flex flex-col gap-1 font-sans text-gray-700 dark:text-gray-300 leading-relaxed text-xs">
                {renderReadmeMarkdown(readmeContent)}
              </div>
            </div>
            
            <div className="flex justify-end pt-3 mt-3 border-t border-border/40 select-none">
              <button
                onClick={() => setIsDocsOpen(false)}
                className="px-4 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors cursor-pointer font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 7. About Dialog Modal */}
      {isAboutOpen && (
        <div className="fixed inset-0 bg-black/55 backdrop-blur-[1.5px] flex items-center justify-center z-[100] select-none text-xs">
          <div className="bg-card border border-border shadow-2xl rounded-2xl w-[380px] flex flex-col p-5 overflow-hidden text-xs text-center items-center">
            <img src={appLogo} className="w-12 h-12 mb-3 animate-pulse select-none" />
            <h3 className="text-sm font-bold text-foreground mb-1">Log Analyzer</h3>
            <span className="ui-text-xs text-accent font-semibold px-2 py-0.5 rounded-full bg-accent/10 mb-4">V3.0 (Tauri Release)</span>
            
            <div className="text-gray-500 dark:text-gray-400 font-sans leading-relaxed flex flex-col gap-2 mb-6">
              <p>An advanced diagnostic log viewer designed for high-performance inspection and pattern matching.</p>
              <p className="ui-text-xs text-gray-400">© 2026 LogAnalyzer Team. All rights reserved.</p>
            </div>
            
            <button
              onClick={() => setIsAboutOpen(false)}
              className="w-full py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors cursor-pointer font-semibold"
            >
              Close
            </button>
          </div>
        </div>
      )}

      {/* Remote DbgView Connect Dialog */}
      {isRemoteOpen && (
        <div className="fixed inset-0 bg-black/55 backdrop-blur-[1.5px] flex items-center justify-center z-[100] select-none text-xs">
          <div className="bg-card border border-border shadow-2xl rounded-2xl w-[420px] flex flex-col p-5 gap-3 text-xs">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <span className="text-sm font-bold text-foreground">Remote DbgView Capture (Kernel)</span>
              <button
                onClick={() => setIsRemoteOpen(false)}
                className="text-gray-400 hover:text-foreground hover:bg-hover p-1 rounded-md transition-colors"
              >
                <X size={16} />
              </button>
            </div>

            <span className="ui-text-xs text-gray-400">
              SSH to a target machine and run its DebugView elevated (scheduled task, kernel capture),
              streaming the log back. Host/user/path are saved; the password is not.
            </span>
            <span className="ui-text-xs text-gray-400">
              Target prep (run once, as admin on the target):{' '}
              <code className="font-mono text-accent">scripts\setup-remote-target.bat</code>{' '}
              — installs OpenSSH and enables admin network elevation. The SSH account must be a local admin.
            </span>

            <div className="flex gap-2">
              <div className="flex flex-col gap-1 flex-1">
                <label className="font-semibold text-gray-600 dark:text-zinc-400">Host / IP</label>
                <input
                  type="text"
                  value={remoteHost}
                  onChange={(e) => setPreferences({ remoteHost: e.target.value })}
                  placeholder="192.168.0.10"
                  className="bg-sidebar border border-border rounded-lg p-2 font-mono focus:outline-none focus:border-accent"
                />
              </div>
              <div className="flex flex-col gap-1 w-20">
                <label className="font-semibold text-gray-600 dark:text-zinc-400">Port</label>
                <input
                  type="number"
                  value={remotePort}
                  onChange={(e) => setPreferences({ remotePort: parseInt(e.target.value) || 22 })}
                  className="bg-sidebar border border-border rounded-lg p-2 font-mono focus:outline-none focus:border-accent"
                />
              </div>
            </div>

            <div className="flex flex-col gap-1">
              <label className="font-semibold text-gray-600 dark:text-zinc-400">Username</label>
              <input
                type="text"
                value={remoteUser}
                onChange={(e) => setPreferences({ remoteUser: e.target.value })}
                placeholder="Administrator"
                className="bg-sidebar border border-border rounded-lg p-2 font-mono focus:outline-none focus:border-accent"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="font-semibold text-gray-600 dark:text-zinc-400">Password</label>
              <input
                type="password"
                value={remotePassword}
                onChange={(e) => setRemotePassword(e.target.value)}
                placeholder="(not saved)"
                className="bg-sidebar border border-border rounded-lg p-2 font-mono focus:outline-none focus:border-accent"
              />
            </div>

            <div className="flex flex-col gap-1">
              <label className="font-semibold text-gray-600 dark:text-zinc-400">Target DbgView.exe Path</label>
              <input
                type="text"
                value={remoteDbgviewPath}
                onChange={(e) => setPreferences({ remoteDbgviewPath: e.target.value })}
                placeholder="C:\\Tools\\Dbgview.exe"
                className="bg-sidebar border border-border rounded-lg p-2 font-mono focus:outline-none focus:border-accent"
              />
            </div>

            {remoteError && (
              <div className="text-red-500 bg-red-500/10 border border-red-500/20 rounded-lg p-2 break-words">
                {remoteError}
              </div>
            )}

            <div className="flex justify-end gap-2 pt-1 font-semibold">
              <button
                onClick={() => setIsRemoteOpen(false)}
                className="px-3 py-2 border border-border rounded-lg hover:bg-hover transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                disabled={remoteConnecting}
                onClick={async () => {
                  setRemoteError(null);
                  setRemoteConnecting(true);
                  try {
                    await startDbgviewRemote(remotePassword);
                    setIsRemoteOpen(false);
                    setRemotePassword('');
                  } catch (err) {
                    setRemoteError(String(err));
                  } finally {
                    setRemoteConnecting(false);
                  }
                }}
                className="px-3 py-2 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {remoteConnecting ? 'Connecting…' : 'Connect'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Paste-from-clipboard status toast */}
      {pasteMsg && (
        <div className="fixed bottom-7 left-1/2 -translate-x-1/2 z-[200] pointer-events-none">
          <div className="bg-card border border-border shadow-2xl rounded-xl px-4 py-2.5 flex items-center gap-2.5 text-xs font-medium animate-in fade-in slide-in-from-bottom-2 duration-200">
            <span className="text-accent">📋</span>
            <span className="text-foreground">{pasteMsg}</span>
          </div>
        </div>
      )}
    </div>
  );
}
