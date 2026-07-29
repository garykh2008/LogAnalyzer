import React, { useRef, useEffect, useState, UIEvent } from 'react';
import { useStore, adjustColorForTheme } from '../store';
import { invoke } from '@tauri-apps/api/core';
import { FileText, Edit, Trash, Copy } from 'lucide-react';

const ROW_HEIGHT = 20;
const MAX_DOM_HEIGHT = 4000000;

export const LogViewport: React.FC = () => {
  const {
    activeFile,
    lineCount,
    loading,
    selectedLine,
    selectedLines,
    setSelectedLine,
    searchQuery,
    activeSearchResults,
    tagCodes,
    filteredIndices,
    filterPalette,
    notes,
    addNote,
    deleteNote,
    editorFontSize,
    editorFontFamily,
    showLineNumbers,
    lineSpacing,
    showFilteredOnly,
    loadLog,
    copySelection,
    theme,
    setPreferences,

    // Lifted states
    openAddFilter,
    setActiveTab,
    setIsSidebarOpen,
    noteEditLine,
    setNoteEditLine,
  } = useStore();

  const containerRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const heatmapRef = useRef<HTMLCanvasElement>(null);

  const [visibleLines, setVisibleLines] = useState<string[]>([]);
  const [startIndex, setStartIndex] = useState(0);
  const [visibleCount, setVisibleCount] = useState(30);
  const [containerHeight, setContainerHeight] = useState(600);
  const [isDropActive, setIsDropActive] = useState(false);
  
  // Note dialog input text
  const [noteText, setNoteText] = useState('');

  // Context Menu State
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; line: number } | null>(null);

  // Position preservation state
  const [pendingAnchor, setPendingAnchor] = useState<{ raw: number; offset: number } | null>(null);

  // Track if selection changes are manual clicks (to prevent scroll jumps)
  const [isManualSelection, setIsManualSelection] = useState(false);

  const totalDisplayLines = filteredIndices ? filteredIndices.length : lineCount;
  const fitCount = Math.max(1, Math.floor(containerHeight / ROW_HEIGHT));

  // Calculate container dimensions
  useEffect(() => {
    if (!containerRef.current) return;
    const updateDimensions = () => {
      const h = containerRef.current?.clientHeight || 600;
      setContainerHeight(h);
      const count = Math.ceil(h / ROW_HEIGHT) + 4;
      setVisibleCount(count);
    };

    updateDimensions();
    const observer = new ResizeObserver(updateDimensions);
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Fetch visible log lines
  useEffect(() => {
    if (!activeFile || totalDisplayLines === 0) {
      setVisibleLines([]);
      return;
    }

    const fetchLines = async () => {
      const fetchIndices: number[] = [];
      const end = Math.min(startIndex + visibleCount, totalDisplayLines);

      for (let i = startIndex; i < end; i++) {
        const rawIdx = filteredIndices ? filteredIndices[i] : i;
        fetchIndices.push(rawIdx);
      }

      if (fetchIndices.length === 0) return;

      try {
        const lines = await invoke<string[]>('get_lines', {
          filepath: activeFile,
          indices: fetchIndices,
        });
        setVisibleLines(lines);
      } catch (err) {
        console.error('Failed to fetch lines:', err);
      }
    };

    fetchLines();
  }, [activeFile, startIndex, visibleCount, totalDisplayLines, filteredIndices]);

  // Handle scrolling
  const handleScroll = (e: UIEvent<HTMLDivElement>) => {
    const target = e.currentTarget;
    const maxScroll = target.scrollHeight - target.clientHeight;
    if (maxScroll <= 0) return;

    const pct = target.scrollTop / maxScroll;
    const start = Math.floor(pct * Math.max(0, totalDisplayLines - fitCount));
    setStartIndex(start);
  };

  // Redirect wheel scroll on content to virtual scrollbar
  const handleWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    if (e.ctrlKey) {
      e.preventDefault();
      const zoomDir = e.deltaY < 0 ? 1 : -1;
      const nextFontSize = Math.max(6, Math.min(72, editorFontSize + zoomDir));
      setPreferences({ editorFontSize: nextFontSize });
      return;
    }

    if (!scrollRef.current) return;
    scrollRef.current.scrollTop += e.deltaY;
  };

  // Close context menu on global click
  useEffect(() => {
    const closeMenu = () => setContextMenu(null);
    window.addEventListener('click', closeMenu);
    return () => window.removeEventListener('click', closeMenu);
  }, []);

  // Selection click handler (prevents jump)
  const handleLineClick = (rawIdx: number, e: React.MouseEvent) => {
    setIsManualSelection(true);
    setSelectedLine(rawIdx, e.ctrlKey || e.shiftKey);
  };

  // Sync scrollbar position (only for search results jumps or non-manual anchors)
  useEffect(() => {
    if (selectedLine === null || totalDisplayLines === 0 || !scrollRef.current) return;

    if (isManualSelection) {
      // Consume manual selection flag
      setIsManualSelection(false);
      return;
    }

    let displayIdx = selectedLine;
    if (filteredIndices) {
      displayIdx = filteredIndices.indexOf(selectedLine);
      if (displayIdx === -1) return;
    }

    const pct = displayIdx / (totalDisplayLines - 1);
    const maxScroll = scrollRef.current.scrollHeight - scrollRef.current.clientHeight;
    
    scrollRef.current.scrollTop = pct * maxScroll;
    setStartIndex(Math.max(0, Math.min(displayIdx - 2, totalDisplayLines - fitCount)));
  }, [selectedLine, totalDisplayLines, filteredIndices]);

  // Preservation recording
  const recordAnchor = () => {
    const topIdx = startIndex;
    const rawTopIdx = filteredIndices ? filteredIndices[topIdx] : topIdx;
    
    let visibleSelected = false;
    let selectedDisplayIdx = -1;
    if (selectedLine !== null) {
      selectedDisplayIdx = filteredIndices ? filteredIndices.indexOf(selectedLine) : selectedLine;
      if (selectedDisplayIdx >= startIndex && selectedDisplayIdx < startIndex + visibleCount) {
        visibleSelected = true;
      }
    }
    
    if (visibleSelected) {
      setPendingAnchor({
        raw: selectedLine!,
        offset: selectedDisplayIdx - startIndex
      });
    } else {
      setPendingAnchor({
        raw: rawTopIdx,
        offset: 0
      });
    }
  };

  useEffect(() => {
    recordAnchor();
  }, [showFilteredOnly]);

  // Restoration
  useEffect(() => {
    if (!pendingAnchor || totalDisplayLines === 0 || !scrollRef.current) return;
    
    let targetDisplayIdx = 0;
    if (filteredIndices) {
      const newIdx = filteredIndices.indexOf(pendingAnchor.raw);
      if (newIdx !== -1) {
        targetDisplayIdx = Math.max(0, newIdx - pendingAnchor.offset);
      } else {
        let low = 0;
        let high = filteredIndices.length - 1;
        let closest = 0;
        while (low <= high) {
          const mid = Math.floor((low + high) / 2);
          if (filteredIndices[mid] === pendingAnchor.raw) {
            closest = mid;
            break;
          } else if (filteredIndices[mid] < pendingAnchor.raw) {
            closest = mid;
            low = mid + 1;
          } else {
            high = mid - 1;
          }
        }
        targetDisplayIdx = Math.max(0, closest - pendingAnchor.offset);
      }
    } else {
      targetDisplayIdx = Math.max(0, pendingAnchor.raw - pendingAnchor.offset);
    }
    
    const maxScroll = scrollRef.current.scrollHeight - scrollRef.current.clientHeight;
    const pct = targetDisplayIdx / Math.max(1, totalDisplayLines - fitCount);
    
    scrollRef.current.scrollTop = pct * maxScroll;
    setStartIndex(Math.max(0, Math.min(targetDisplayIdx, totalDisplayLines - fitCount)));
    setPendingAnchor(null);
  }, [filteredIndices, totalDisplayLines]);

  // Heatmap draw
  useEffect(() => {
    const canvas = heatmapRef.current;
    if (!canvas || totalDisplayLines === 0) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    if (activeSearchResults.length > 0) {
      ctx.fillStyle = 'rgba(249, 115, 22, 0.85)';
      activeSearchResults.forEach((rawIdx) => {
        let displayIdx = rawIdx;
        if (filteredIndices) {
          displayIdx = filteredIndices.indexOf(rawIdx);
          if (displayIdx === -1) return;
        }
        const y = (displayIdx / totalDisplayLines) * canvas.height;
        ctx.fillRect(0, y, canvas.width, 2.5);
      });
    }

    const viewY = (startIndex / totalDisplayLines) * canvas.height;
    const viewH = (visibleCount / totalDisplayLines) * canvas.height;
    ctx.fillStyle = 'rgba(0, 122, 204, 0.25)';
    ctx.fillRect(0, viewY, canvas.width, Math.max(4, viewH));
  }, [activeSearchResults, totalDisplayLines, filteredIndices, startIndex, visibleCount]);

  // Highlighting matches
  const renderLineContent = (text: string, query: string) => {
    if (!query) return <span>{text}</span>;
    try {
      const escapedQuery = query.replace(/[/\-\\^$*+?.()|[\]{}]/g, '\\$&');
      const regex = new RegExp(`(${escapedQuery})`, 'gi');
      const parts = text.split(regex);
      
      return (
        <span>
          {parts.map((part, i) =>
            regex.test(part) ? (
              <mark key={i} className="bg-amber-500/30 dark:bg-amber-500/50 text-foreground rounded-[2px] px-0.5 font-semibold">{part}</mark>
            ) : (
              part
            )
          )}
        </span>
      );
    } catch {
      return <span>{text}</span>;
    }
  };

  // Drag and drop
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDropActive(true);
  };

  const handleDragLeave = () => {
    setIsDropActive(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setIsDropActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      const filepath = (file as any).path || file.name;
      if (filepath) {
        await loadLog(filepath);
      }
    }
  };

  const handleContextMenu = (e: React.MouseEvent, line: number) => {
    e.preventDefault();
    setSelectedLine(line, e.ctrlKey || e.shiftKey);
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      line: line
    });
  };

  const handleDoubleClickLine = (lineText: string) => {
    openAddFilter(lineText.trim());
    setActiveTab('filters');
    setIsSidebarOpen(true);
  };

  const handleOpenNoteDialog = (line: number) => {
    const existing = notes[activeFile || '']?.[line] || '';
    setNoteText(existing);
    setNoteEditLine(line);
  };

  const handleSaveNote = () => {
    if (noteEditLine !== null && activeFile) {
      if (noteText.trim()) {
        addNote(activeFile, noteEditLine, noteText);
      } else {
        deleteNote(activeFile, noteEditLine);
      }
    }
    setNoteEditLine(null);
  };

  const realScrollHeight = totalDisplayLines * ROW_HEIGHT;
  const domScrollHeight = Math.min(realScrollHeight, MAX_DOM_HEIGHT);

  // Keep note text synced if editing note changes from shortcut
  useEffect(() => {
    if (noteEditLine !== null && activeFile) {
      const existing = notes[activeFile]?.[noteEditLine] || '';
      setNoteText(existing);
    }
  }, [noteEditLine, activeFile, notes]);

  const isDark = theme === 'dark';

  return (
    <div
      ref={containerRef}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`relative flex-1 flex flex-row overflow-hidden bg-background select-text outline-none ${
        isDropActive ? 'border-2 border-dashed border-accent' : ''
      }`}
    >
      {/* Drop overlay */}
      {isDropActive && (
        <div className="absolute inset-0 bg-accent/5 pointer-events-none flex items-center justify-center z-50">
          <div className="bg-card border border-border p-8 rounded-2xl shadow-2xl flex flex-col items-center gap-4 max-w-sm">
            <FileText size={48} className="text-accent animate-bounce" />
            <p className="text-sm font-semibold text-center">Drop Log File Here to Analyze</p>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {loading && (
        <div className="absolute inset-0 bg-black/45 backdrop-blur-[1px] flex items-center justify-center z-45">
          <div className="bg-card border border-border px-6 py-4 rounded-xl shadow-2xl flex flex-col items-center gap-3">
            <div className="w-6 h-6 border-3 border-accent border-t-transparent rounded-full animate-spin"></div>
            <p className="text-xs font-medium text-gray-400">Processing Log File...</p>
          </div>
        </div>
      )}

      {/* Welcome Screen */}
      {!activeFile ? (
        <div className="flex-1 flex flex-col items-center justify-center text-gray-400 gap-4 bg-gray-50 dark:bg-[#1a1a1a]">
          <div className="bg-white dark:bg-card border border-border p-8 rounded-2xl shadow-xl flex flex-col items-center gap-4 text-center max-w-sm select-none">
            <FileText size={48} className="text-gray-300 dark:text-zinc-700 animate-pulse" />
            <div>
              <h3 className="text-sm font-bold text-gray-700 dark:text-zinc-300">No Log File Open</h3>
              <p className="text-xs text-gray-500 mt-1.5 leading-relaxed">Drag and drop a log file here, or use File &gt; Open Log to start analyzing.</p>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* Main Log Lines View */}
          <div 
            className="flex-1 overflow-hidden relative select-text"
            onWheel={handleWheel}
          >
            <div
              className="absolute inset-0 select-text"
              style={{
                fontFamily: editorFontFamily,
                fontSize: `${editorFontSize}px`,
                lineHeight: `${ROW_HEIGHT}px`,
              }}
            >
              {visibleLines.map((lineText, index) => {
                const itemIndex = startIndex + index;
                const rawIdx = filteredIndices ? filteredIndices[itemIndex] : itemIndex;
                const code = tagCodes[rawIdx];
                const palette = filterPalette[code];
                const hasNote = notes[activeFile]?.hasOwnProperty(rawIdx);
                const isLineSelected = selectedLines.includes(rawIdx);

                // Resolve smart color adjustments for theme contrast
                const adjustedBg = palette?.bg ? adjustColorForTheme(palette.bg, true, isDark) : undefined;
                const adjustedFg = palette?.fg ? adjustColorForTheme(palette.fg, false, isDark) : undefined;

                const rowBg = isLineSelected
                  ? 'bg-[#add6ff]/40 dark:bg-[#264f78]/60'
                  : hasNote
                  ? 'bg-amber-100/30 dark:bg-[#3a3d41]/50'
                  : adjustedBg
                  ? 'style-bg'
                  : 'hover:bg-gray-100/50 dark:hover:bg-white/5';

                const inlineStyle = adjustedBg && !isLineSelected ? { backgroundColor: adjustedBg } : {};

                return (
                  <div
                    key={itemIndex}
                    onClick={(e) => handleLineClick(rawIdx, e)}
                    onDoubleClick={() => handleDoubleClickLine(lineText)}
                    onContextMenu={(e) => handleContextMenu(e, rawIdx)}
                    style={{
                      height: `${ROW_HEIGHT}px`,
                      paddingTop: `${lineSpacing / 2}px`,
                      paddingBottom: `${lineSpacing / 2}px`,
                      ...inlineStyle,
                    }}
                    className={`flex flex-row items-center border-b border-gray-100 dark:border-[#303031]/10 cursor-pointer ${rowBg}`}
                  >
                    {/* Line numbers gutter */}
                    {showLineNumbers && (
                      <div
                        style={{ width: `${Math.max(55, String(lineCount).length * 8 + 20)}px` }}
                        className="flex-shrink-0 h-full flex items-center justify-end pr-3.5 border-r border-border text-gutter-fg bg-gutter dark:bg-[#1a1a1a] select-none text-[10px] font-mono"
                      >
                        {hasNote && (
                          <span className="w-1.5 h-1.5 rounded-full bg-amber-500 mr-1.5"></span>
                        )}
                        {rawIdx + 1}
                      </div>
                    )}

                    {/* Log text content */}
                    <div
                      style={{ color: adjustedFg || undefined }}
                      className="flex-1 px-4 truncate select-text whitespace-pre text-foreground"
                    >
                      {renderLineContent(lineText, searchQuery)}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Virtual Scrollbar & Heatmap Gutter */}
          <div className="w-6 relative bg-gray-50/20 dark:bg-[#181818]/20 border-l border-border flex flex-row select-none">
            {/* Heatmap Canvas on the left */}
            <canvas
              ref={heatmapRef}
              width={10}
              height={containerHeight}
              className="w-2.5 h-full opacity-80"
            />

            {/* Standard scrollbar on the right */}
            <div
              ref={scrollRef}
              onScroll={handleScroll}
              className="flex-1 h-full overflow-y-auto overflow-x-hidden"
            >
              <div style={{ height: `${domScrollHeight}px`, width: '1px' }}></div>
            </div>
          </div>
        </>
      )}

      {/* Floating Context Menu */}
      {contextMenu !== null && (
        <div
          style={{ top: `${contextMenu.y}px`, left: `${contextMenu.x}px` }}
          className="fixed z-50 bg-card border border-border shadow-2xl rounded-lg py-1.5 min-w-[150px] text-xs font-normal"
        >
          <button
            onClick={() => copySelection()}
            className="w-full text-left px-3 py-1.5 hover:bg-hover flex items-center gap-2 cursor-pointer transition-colors"
          >
            <Copy size={12} className="text-gray-400" />
            <span>Copy</span>
          </button>
          <div className="h-[1px] bg-border my-1" />
          <button
            onClick={() => handleOpenNoteDialog(contextMenu.line)}
            className="w-full text-left px-3 py-1.5 hover:bg-hover flex items-center gap-2 cursor-pointer transition-colors"
          >
            <Edit size={12} className="text-gray-400" />
            <span>Add/Edit Note</span>
          </button>
        </div>
      )}

      {/* Note Editing Modal */}
      {noteEditLine !== null && (
        <div className="absolute inset-0 bg-black/45 backdrop-blur-[1.5px] flex items-center justify-center z-50">
          <div className="bg-card border border-border p-6 rounded-xl shadow-2xl w-[360px] flex flex-col gap-4">
            <div className="flex flex-col gap-1 select-none">
              <span className="text-xs font-bold text-gray-400 uppercase tracking-wider">Line Note</span>
              <span className="text-xs text-gray-500 font-mono font-medium">Editing line {noteEditLine + 1}</span>
            </div>
            <textarea
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Type your notes or annotations here..."
              rows={3}
              className="w-full bg-gray-50 dark:bg-[#3c3c3c] border border-border rounded-lg p-2.5 text-xs focus:outline-none focus:border-accent resize-none"
            />
            <div className="flex flex-row justify-end gap-2 text-xs font-semibold pt-1 select-none">
              <button
                onClick={() => setNoteEditLine(null)}
                className="px-3 py-1.5 border border-border rounded-md hover:bg-hover transition-colors cursor-pointer"
              >
                Cancel
              </button>
              {notes[activeFile || '']?.hasOwnProperty(noteEditLine) && (
                <button
                  onClick={() => {
                    if (activeFile) deleteNote(activeFile, noteEditLine);
                    setNoteEditLine(null);
                  }}
                  className="px-3 py-1.5 border border-red-500/30 text-red-500 rounded-md hover:bg-red-500/10 transition-colors cursor-pointer"
                >
                  Delete
                </button>
              )}
              <button
                onClick={handleSaveNote}
                className="px-3 py-1.5 bg-accent hover:bg-accent-hover text-white rounded-md transition-colors cursor-pointer"
              >
                Save
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
