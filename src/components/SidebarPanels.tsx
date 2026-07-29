import React, { useState, useEffect, useRef } from 'react';
import { useStore, FilterItem, adjustColorForTheme } from '../store';
import { invoke } from '@tauri-apps/api/core';
import { Plus, X, Trash, Edit, Check, Settings, FileText, Filter, BookOpen, Clipboard, Download } from 'lucide-react';

interface SidebarPanelsProps {
  activeTab: 'files' | 'filters' | 'notes';
}

export const SidebarPanels: React.FC<SidebarPanelsProps> = ({ activeTab }) => {
  const {
    loadedFiles,
    activeFile,
    loadLog,
    closeLog,
    setActiveFile,
    filters,
    addFilter,
    updateFilter,
    removeFilter,
    moveFilter,
    notes,
    deleteNote,
    setSelectedLine,
    theme,
    currentFilterFile,
    clearFilters,

    // Lifted Filter Editor States
    isAddingFilter,
    editingFilterIdx,
    filterText,
    filterIsRegex,
    filterIsExclude,
    filterIsEvent,
    filterFgColor,
    filterBgColor,
    setFilterEditor,
    resetFilterEditor,
    selectedFilterIdx,
    setSelectedFilterIdx,
  } = useStore();

  const handleOpenFileDialog = async () => {
    try {
      const path = await invoke<string | null>('open_file_dialog');
      if (path) {
        await loadLog(path);
      }
    } catch (err) {
      console.error('Failed to open file dialog:', err);
    }
  };

  const handleAddFilterSubmit = () => {
    if (!filterText.trim()) return;
    addFilter({
      text: filterText,
      is_regex: filterIsRegex,
      is_exclude: filterIsExclude,
      is_event: filterIsEvent,
      fg_color: filterFgColor,
      bg_color: filterBgColor === 'transparent' ? '' : filterBgColor,
      enabled: true,
    });
    resetFilterEditor();
  };

  const handleEditFilterSubmit = (idx: number) => {
    if (!filterText.trim()) return;
    updateFilter(idx, {
      text: filterText,
      is_regex: filterIsRegex,
      is_exclude: filterIsExclude,
      is_event: filterIsEvent,
      fg_color: filterFgColor,
      bg_color: filterBgColor === 'transparent' ? '' : filterBgColor,
    });
    resetFilterEditor();
  };

  const startEditFilter = (idx: number, item: FilterItem) => {
    setFilterEditor({
      editingFilterIdx: idx,
      filterText: item.text,
      filterIsRegex: item.is_regex,
      filterIsExclude: item.is_exclude,
      filterIsEvent: item.is_event,
      filterFgColor: item.fg_color,
      filterBgColor: item.bg_color || 'transparent',
      isAddingFilter: false,
    });
  };

  // Filter Context Menu
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; idx: number; filter: FilterItem } | null>(null);

  useEffect(() => {
    const closeMenu = () => setContextMenu(null);
    window.addEventListener('click', closeMenu);
    return () => window.removeEventListener('click', closeMenu);
  }, []);

  // Drag & drop logic for reordering filters (custom MouseEvent implementation to bypass Tauri webview limitations)
  const [draggedIdx, setDraggedIdx] = useState<number | null>(null);
  const [dragOverIdx, setDragOverIdx] = useState<number | null>(null);

  const draggedRef = useRef<number | null>(null);
  const dragOverRef = useRef<number | null>(null);

  const setDragged = (idx: number | null) => {
    draggedRef.current = idx;
    setDraggedIdx(idx);
  };

  const setDragOver = (idx: number | null) => {
    dragOverRef.current = idx;
    setDragOverIdx(idx);
  };

  const handleCardMouseDown = (idx: number, e: React.MouseEvent) => {
    const target = e.target as HTMLElement;
    // Ignore right click or clicks on inputs/buttons/dropdowns
    if (e.button !== 0 || target.closest('button') || target.closest('input') || target.closest('select')) {
      return;
    }

    e.preventDefault();
    setDragged(idx);
    setDragOver(idx);
    document.body.style.cursor = 'grabbing';

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const element = document.elementFromPoint(moveEvent.clientX, moveEvent.clientY);
      if (!element) return;

      const cardEl = element.closest('[data-filter-idx]');
      if (cardEl) {
        const hoverIdx = parseInt(cardEl.getAttribute('data-filter-idx') || '-1');
        if (hoverIdx !== -1) {
          setDragOver(hoverIdx);
        }
      }
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';

      const from = draggedRef.current;
      const to = dragOverRef.current;
      if (from !== null && to !== null && from !== to) {
        moveFilter(from, to);
      }

      setDragged(null);
      setDragOver(null);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  const handleContextMenu = (e: React.MouseEvent, idx: number, filter: FilterItem) => {
    e.preventDefault();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      idx: idx,
      filter: filter,
    });
  };

  // Notes list sorting
  const activeFileNotes = notes[activeFile || ''] || {};
  const notesList = Object.entries(activeFileNotes)
    .map(([line, text]) => ({ line: parseInt(line), text }))
    .sort((a, b) => a.line - b.line);

  const isDark = theme === 'dark';

  return (
    <div className="w-80 h-full bg-sidebar border-r border-border flex flex-col overflow-hidden select-none">
      {/* Header */}
      <div className="h-10 border-b border-border flex items-center justify-between px-4 bg-sidebar dark:bg-activity">
        <span className="text-[10px] font-bold tracking-wider text-gray-500 dark:text-gray-400 uppercase select-none">
          {activeTab === 'files' && 'Log Files'}
          {activeTab === 'filters' && 'Filters'}
          {activeTab === 'notes' && 'Notes'}
        </span>

        {/* Actions */}
        {activeTab === 'files' && (
          <button
            onClick={handleOpenFileDialog}
            className="p-1 rounded-md hover:bg-hover text-accent cursor-pointer transition-colors"
            title="Open Log File"
          >
            <Plus size={16} />
          </button>
        )}

        {activeTab === 'filters' && !isAddingFilter && editingFilterIdx === null && (
          <div className="flex items-center gap-1">
            {filters.length > 0 && (
              <button
                onClick={() => clearFilters()}
                className="p-1 rounded-md hover:bg-red-500/10 text-gray-400 hover:text-red-500 cursor-pointer transition-colors"
                title="Clear All Filters"
              >
                <Trash size={15} />
              </button>
            )}
            <button
              onClick={() => setFilterEditor({ isAddingFilter: true })}
              className="p-1 rounded-md hover:bg-hover text-accent cursor-pointer transition-colors"
              title="Add Filter"
            >
              <Plus size={16} />
            </button>
          </div>
        )}
      </div>

      {/* Content Panels */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden p-2.5">
        {/* LOG FILES PANEL */}
        {activeTab === 'files' && (
          <div className="flex flex-col gap-1.5">
            {loadedFiles.length === 0 ? (
              <div className="text-center text-xs text-gray-400 mt-8 flex flex-col items-center gap-2">
                <FileText size={20} className="opacity-40" />
                <span>No files loaded</span>
              </div>
            ) : (
              loadedFiles.map((file) => {
                const isActive = activeFile === file;
                const filename = file.split(/[/\\]/).pop() || file;
                const pathDir = file.substring(0, file.length - filename.length);
                const isClipboard = filename.startsWith('loganalyzer_clipboard_');

                const handleClose = async (e: React.MouseEvent) => {
                  e.stopPropagation();
                  closeLog(file);
                  // Delete temp clipboard files on close
                  if (isClipboard) {
                    try { await invoke('delete_file', { path: file }); } catch {}
                  }
                };

                const handleSaveAs = async (e: React.MouseEvent) => {
                  e.stopPropagation();
                  try {
                    const savePath = await invoke<string | null>('save_file_dialog', {
                      defaultName: 'clipboard.log',
                      extension: 'log',
                    });
                    if (!savePath) return;
                    const content = await invoke<string>('read_text_file', { path: file });
                    await invoke('write_text_file', { path: savePath, content });
                  } catch (err) {
                    console.error('Save as failed:', err);
                  }
                };

                return (
                  <div
                    key={file}
                    onClick={() => setActiveFile(file)}
                    className={`group flex items-center justify-between p-2.5 rounded-lg cursor-pointer transition-all ${
                      isActive
                        ? 'bg-accent/10 border border-accent/30 text-accent dark:text-sky-400'
                        : 'border border-transparent hover:bg-hover text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    <div className="flex flex-col min-w-0 pr-2">
                      <div className="flex items-center gap-1.5">
                        {isClipboard && <Clipboard size={10} className="text-accent shrink-0" />}
                        <span className="text-xs font-semibold truncate font-mono" title={file}>
                          {isClipboard ? 'Clipboard' : filename}
                        </span>
                      </div>
                      <span className="text-[9px] text-gray-400 truncate select-none mt-0.5">
                        {isClipboard ? 'Unsaved — paste buffer' : pathDir}
                      </span>
                    </div>
                    <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                      {isClipboard && (
                        <button
                          onClick={handleSaveAs}
                          className="p-1 text-gray-400 hover:text-accent rounded hover:bg-hover transition-colors cursor-pointer"
                          title="Save As..."
                        >
                          <Download size={12} />
                        </button>
                      )}
                      <button
                        onClick={handleClose}
                        className="p-1 text-gray-400 hover:text-red-500 rounded hover:bg-hover transition-colors cursor-pointer"
                        title="Close File"
                      >
                        <X size={12} />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {/* FILTERS PANEL */}
        {activeTab === 'filters' && (
          <div className="flex flex-col gap-2.5">
            {/* Active Filter File Info */}
            {currentFilterFile && (
              <div className="px-2.5 py-1.5 bg-accent/5 border border-accent/20 rounded-xl text-[10px] font-mono text-gray-500 dark:text-gray-400 flex items-center justify-between truncate select-text mb-0.5">
                <span className="truncate" title={currentFilterFile}>
                  📂 {currentFilterFile.split(/[\\/]/).pop()}
                </span>
                <span className="text-[9px] opacity-65 pl-2 shrink-0 select-none">Active</span>
              </div>
            )}
            {/* Inline Filter Editor */}
            {(isAddingFilter || editingFilterIdx !== null) && (
              <div className="p-3 bg-card border border-border rounded-xl shadow-lg flex flex-col gap-3">
                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                  {isAddingFilter ? 'Create Filter' : 'Edit Filter'}
                </div>

                {/* Filter Text */}
                <input
                  type="text"
                  value={filterText}
                  onChange={(e) => setFilterEditor({ filterText: e.target.value })}
                  placeholder="Keyword or regex..."
                  className="w-full text-xs bg-gray-50 dark:bg-[#313244] border border-border rounded-lg p-2.5 focus:outline-none focus:border-accent"
                />

                {/* Checkboxes */}
                <div className="flex flex-col gap-1 text-xs text-gray-600 dark:text-gray-350">
                  <label className="flex items-center gap-2 cursor-pointer p-1.5 rounded-md hover:bg-hover">
                    <input
                      type="checkbox"
                      checked={filterIsRegex}
                      onChange={(e) => setFilterEditor({ filterIsRegex: e.target.checked })}
                      className="rounded text-accent border-border"
                    />
                    <span>Regular Expression (Regex)</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer p-1.5 rounded-md hover:bg-hover">
                    <input
                      type="checkbox"
                      checked={filterIsExclude}
                      onChange={(e) => setFilterEditor({ filterIsExclude: e.target.checked })}
                      className="rounded text-accent border-border"
                    />
                    <span>Exclude Match (Hide rows)</span>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer p-1.5 rounded-md hover:bg-hover">
                    <input
                      type="checkbox"
                      checked={filterIsEvent}
                      onChange={(e) => setFilterEditor({ filterIsEvent: e.target.checked })}
                      className="rounded text-accent border-border"
                    />
                    <span>Timeline Event</span>
                  </label>
                </div>

                {/* Premium Colors Swatch Grid */}
                <div className="flex flex-col gap-2">
                  <span className="text-[9px] text-gray-400 font-bold uppercase select-none">Color Swatches</span>
                  <div className="grid grid-cols-4 gap-1.5">
                    {[
                      { fg: '#ef4444', bg: 'rgba(239, 68, 68, 0.15)', name: 'Red' },
                      { fg: '#f97316', bg: 'rgba(249, 115, 22, 0.15)', name: 'Orange' },
                      { fg: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)', name: 'Amber' },
                      { fg: '#10b981', bg: 'rgba(16, 185, 129, 0.15)', name: 'Green' },
                      { fg: '#3b82f6', bg: 'rgba(59, 130, 246, 0.15)', name: 'Blue' },
                      { fg: '#8b5cf6', bg: 'rgba(139, 92, 246, 0.15)', name: 'Purple' },
                      { fg: '#ec4899', bg: 'rgba(236, 72, 153, 0.15)', name: 'Pink' },
                      { fg: '#9ca3af', bg: 'transparent', name: 'Grey' },
                    ].map((preset) => {
                      const isSelected = filterFgColor === preset.fg && filterBgColor === preset.bg;
                      return (
                        <button
                          key={preset.name}
                          type="button"
                          onClick={() => setFilterEditor({ filterFgColor: preset.fg, filterBgColor: preset.bg })}
                          style={{
                            backgroundColor: preset.bg || 'transparent',
                            color: preset.fg,
                            borderColor: isSelected ? preset.fg : 'var(--border)'
                          }}
                          className={`h-7 px-1 rounded-md border text-[10px] font-mono font-bold flex items-center justify-center transition-all cursor-pointer select-none hover:opacity-100 ${
                            isSelected ? 'ring-2 ring-accent/30 scale-105 opacity-100 font-black' : 'opacity-75'
                          }`}
                        >
                          Aa
                        </button>
                      );
                    })}
                  </div>

                  {/* Collapsible custom picker for advanced styles */}
                  <details className="text-[10px] text-gray-500 cursor-pointer select-none mt-1 outline-none">
                    <summary className="hover:text-accent font-medium outline-none">Custom colors picker...</summary>
                    <div className="flex items-center gap-3 mt-2 pl-2 border-l border-border">
                      <div className="flex flex-col gap-1 flex-1">
                        <span className="text-[8px] text-gray-400">Text color</span>
                        <input
                          type="color"
                          value={filterFgColor}
                          onChange={(e) => setFilterEditor({ filterFgColor: e.target.value })}
                          className="w-full h-7 border border-border rounded cursor-pointer p-0.5 bg-transparent"
                        />
                      </div>
                      <div className="flex flex-col gap-1 flex-1">
                        <span className="text-[8px] text-gray-400">Background</span>
                        <input
                          type="color"
                          value={filterBgColor.startsWith('rgba') ? '#ffffff' : filterBgColor}
                          onChange={(e) => setFilterEditor({ filterBgColor: e.target.value })}
                          className="w-full h-7 border border-border rounded cursor-pointer p-0.5 bg-transparent"
                        />
                      </div>
                    </div>
                  </details>
                </div>

                {/* Actions */}
                <div className="flex justify-end gap-2 text-xs font-semibold pt-1">
                  <button
                    onClick={resetFilterEditor}
                    className="px-3 py-1.5 border border-border rounded-md hover:bg-hover transition-colors cursor-pointer"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={() =>
                      isAddingFilter
                        ? handleAddFilterSubmit()
                        : handleEditFilterSubmit(editingFilterIdx!)
                    }
                    className="px-3 py-1.5 bg-accent hover:bg-accent-hover text-white rounded-md transition-colors cursor-pointer"
                  >
                    Save
                  </button>
                </div>
              </div>
            )}

            {/* Filters Checklist */}
            {filters.length === 0 ? (
              <div className="text-center text-xs text-gray-400 mt-8 flex flex-col items-center gap-2">
                <Filter size={20} className="opacity-40" />
                <span>No filters active</span>
              </div>
            ) : (
              <div className="flex flex-col gap-2.5">
                {filters.map((f, idx) => {
                  const adjustedBg = f.bg_color ? adjustColorForTheme(f.bg_color, true, isDark) : undefined;
                  const adjustedFg = f.fg_color ? adjustColorForTheme(f.fg_color, false, isDark) : undefined;

                  const isSelected = selectedFilterIdx === idx;
                  const isHoveredTarget = dragOverIdx === idx;

                  return (
                    <div
                      key={idx}
                      data-filter-idx={idx}
                      onMouseDown={(e) => handleCardMouseDown(idx, e)}
                      onContextMenu={(e) => handleContextMenu(e, idx, f)}
                      onClick={() => setSelectedFilterIdx(idx)}
                      style={{ backgroundColor: adjustedBg || undefined }}
                      className={`group flex items-center justify-between p-2.5 border rounded-xl shadow-sm cursor-grab transition-all ${
                        isHoveredTarget
                          ? 'border-dashed border-accent dark:border-accent bg-accent/5 scale-95'
                          : isSelected
                          ? 'border-accent dark:border-accent ring-2 ring-accent/20 scale-[1.01]'
                          : 'border-border hover:border-gray-300 dark:hover:border-zinc-700'
                      } ${adjustedBg ? '' : 'bg-card'} ${draggedIdx === idx ? 'opacity-30' : ''}`}
                    >
                      <div className={`flex items-center min-w-0 flex-1 gap-2 ${draggedIdx !== null ? 'pointer-events-none' : ''}`}>
                        <input
                          type="checkbox"
                          checked={f.enabled}
                          onChange={(e) => updateFilter(idx, { enabled: e.target.checked })}
                          className="rounded text-accent border-border cursor-pointer"
                        />

                        {/* Filter Text */}
                        <div
                          className="flex flex-col min-w-0 pr-1 cursor-pointer"
                          onClick={() => startEditFilter(idx, f)}
                        >
                          <span
                            className="text-xs font-mono font-semibold truncate"
                            style={{ color: adjustedFg }}
                          >
                            {f.text}
                          </span>
                          <span className="text-[9px] text-gray-400 uppercase select-none mt-0.5 font-sans font-medium">
                            {f.is_exclude ? 'exclude' : 'highlight'}
                            {f.is_regex ? ' • regex' : ''}
                            {f.is_event ? ' • timeline' : ''}
                          </span>
                        </div>
                      </div>

                      <div className={`flex items-center gap-1.5 select-none ${draggedIdx !== null ? 'pointer-events-none' : ''}`}>
                        {/* Hit counts */}
                        {f.enabled && (
                          <span className="text-[10px] font-bold font-mono px-1.5 py-0.5 rounded bg-gray-150/40 dark:bg-zinc-800/40 text-gray-500 dark:text-gray-400">
                            {f.hits.toLocaleString()}
                          </span>
                        )}

                        {/* Quick actions: Edit & Delete */}
                        <div className="flex items-center gap-1">
                          <button
                            onClick={() => startEditFilter(idx, f)}
                            className="p-1 opacity-0 group-hover:opacity-100 text-gray-400 hover:text-accent rounded hover:bg-hover transition-colors cursor-pointer"
                            title="Edit Filter"
                          >
                            <Edit size={12} />
                          </button>
                          <button
                            onClick={() => removeFilter(idx)}
                            className="p-1 opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 rounded hover:bg-hover transition-colors cursor-pointer"
                            title="Delete Filter"
                          >
                            <Trash size={12} />
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
                <button
                  onClick={() => clearFilters()}
                  className="w-full py-2 text-xs font-medium text-red-500/80 hover:text-red-500 hover:bg-red-500/10 border border-red-500/20 rounded-xl transition-colors cursor-pointer flex items-center justify-center gap-1.5 mt-1"
                >
                  <Trash size={12} />
                  <span>Clear All Filters ({filters.length})</span>
                </button>
              </div>
            )}
          </div>
        )}

        {/* NOTES PANEL */}
        {activeTab === 'notes' && (
          <div className="flex flex-col gap-2">
            {notesList.length === 0 ? (
              <div className="text-center text-xs text-gray-400 mt-8 flex flex-col items-center gap-2">
                <BookOpen size={20} className="opacity-40" />
                <span>No notes in this file</span>
              </div>
            ) : (
              notesList.map((n) => (
                <div
                  key={n.line}
                  onClick={() => setSelectedLine(n.line)}
                  className="p-2.5 border border-border bg-card hover:border-gray-300 dark:hover:border-zinc-700 rounded-lg cursor-pointer flex flex-col gap-1.5 select-text hover:shadow-sm transition-all"
                >
                  <div className="flex items-center justify-between border-b border-border pb-1.5 text-[9px] font-mono text-gray-400 select-none">
                    <span>Line {n.line + 1}</span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (activeFile) deleteNote(activeFile, n.line);
                      }}
                      className="hover:text-red-500 rounded p-0.5 hover:bg-hover transition-colors cursor-pointer"
                      title="Remove Note"
                    >
                      <Trash size={10} />
                    </button>
                  </div>
                  <div className="text-xs text-gray-750 dark:text-gray-300 break-words font-sans">
                    {n.text}
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* Floating Filter Context Menu */}
      {contextMenu !== null && (
        <div
          style={{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }}
          className="fixed z-50 bg-card border border-border shadow-2xl rounded-lg py-1.5 min-w-[150px] text-xs font-normal"
        >
          <button
            onClick={() => {
              startEditFilter(contextMenu.idx, contextMenu.filter);
            }}
            className="w-full text-left px-3 py-1.5 hover:bg-hover flex items-center gap-2 cursor-pointer transition-colors"
          >
            <Edit size={12} className="text-gray-400" />
            <span>Edit Filter</span>
          </button>
          <button
            onClick={() => {
              updateFilter(contextMenu.idx, { enabled: !contextMenu.filter.enabled });
            }}
            className="w-full text-left px-3 py-1.5 hover:bg-hover flex items-center gap-2 cursor-pointer transition-colors"
          >
            <Check size={12} className="text-gray-400" />
            <span>{contextMenu.filter.enabled ? 'Disable Filter' : 'Enable Filter'}</span>
          </button>
          <div className="h-[1px] bg-border my-1" />
          <button
            onClick={() => {
              if (contextMenu.idx > 0) {
                moveFilter(contextMenu.idx, contextMenu.idx - 1);
              }
            }}
            disabled={contextMenu.idx === 0}
            className="w-full text-left px-3 py-1.5 hover:bg-hover flex items-center gap-2 cursor-pointer transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span>Move Up</span>
          </button>
          <button
            onClick={() => {
              if (contextMenu.idx < filters.length - 1) {
                moveFilter(contextMenu.idx, contextMenu.idx + 1);
              }
            }}
            disabled={contextMenu.idx === filters.length - 1}
            className="w-full text-left px-3 py-1.5 hover:bg-hover flex items-center gap-2 cursor-pointer transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <span>Move Down</span>
          </button>
          <div className="h-[1px] bg-border my-1" />
          <button
            onClick={() => {
              removeFilter(contextMenu.idx);
            }}
            className="w-full text-left px-3 py-1.5 hover:bg-hover text-red-500 flex items-center gap-2 cursor-pointer transition-colors"
          >
            <Trash size={12} className="text-red-400" />
            <span>Delete</span>
          </button>
        </div>
      )}
    </div>
  );
};
