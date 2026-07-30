import React, { useEffect, useRef, useState } from 'react';
import { useStore } from '../store';
import { X, ArrowDown, ArrowUp, CaseSensitive, Type } from 'lucide-react';

interface SearchOverlayProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SearchOverlay: React.FC<SearchOverlayProps> = ({ isOpen, onClose }) => {
  const searchQuery = useStore((s) => s.searchQuery);
  const isRegexSearch = useStore((s) => s.isRegexSearch);
  const isCaseSensitiveSearch = useStore((s) => s.isCaseSensitiveSearch);
  const activeSearchResults = useStore((s) => s.activeSearchResults);
  const searchIndex = useStore((s) => s.searchIndex);
  const isSearching = useStore((s) => s.isSearching);
  const setSearchQuery = useStore((s) => s.setSearchQuery);
  const runSearch = useStore((s) => s.runSearch);
  const nextSearchMatch = useStore((s) => s.nextSearchMatch);
  const prevSearchMatch = useStore((s) => s.prevSearchMatch);
  const clearSearch = useStore((s) => s.clearSearch);

  const inputRef = useRef<HTMLInputElement>(null);
  const [history, setHistory] = useState<string[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return;
    const delay = setTimeout(() => {
      runSearch();
    }, 200);

    return () => clearTimeout(delay);
  }, [searchQuery, isRegexSearch, isCaseSensitiveSearch, isOpen]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (e.shiftKey) {
        prevSearchMatch();
      } else {
        if (searchQuery.trim() && !history.includes(searchQuery)) {
          setHistory((h) => [searchQuery, ...h.slice(0, 9)]);
        }
        nextSearchMatch();
      }
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleClose();
    }
  };

  const handleClose = () => {
    clearSearch();
    onClose();
  };

  if (!isOpen) return null;

  const matchCount = activeSearchResults.length;
  const currentMatch = matchCount > 0 && searchIndex !== -1 ? searchIndex + 1 : 0;

  return (
    <div className="absolute top-4 right-10 z-35 w-[420px] bg-card border border-border rounded-xl shadow-2xl p-2 select-none backdrop-blur-[2px]">
      <div className="flex items-center gap-1.5 relative">
        <div className="flex-1 relative">
          <input
            ref={inputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value, isRegexSearch, isCaseSensitiveSearch)}
            onKeyDown={handleKeyDown}
            onFocus={() => setShowHistory(true)}
            onBlur={() => setTimeout(() => setShowHistory(false), 200)}
            placeholder="Find (Enter to search, Esc to close)..."
            className="w-full text-xs bg-gray-50 dark:bg-[#313244] border border-border rounded-lg p-2.5 focus:outline-none focus:border-accent"
          />

          {/* Autocomplete Dropdown */}
          {showHistory && history.length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-1 bg-card border border-border rounded-lg shadow-xl max-h-40 overflow-y-auto z-50 text-xs py-1">
              {history.map((h, i) => (
                <div
                  key={i}
                  onMouseDown={() => {
                    setSearchQuery(h, isRegexSearch, isCaseSensitiveSearch);
                    inputRef.current?.focus();
                  }}
                  className="px-3 py-2 hover:bg-hover cursor-pointer truncate transition-colors"
                >
                  {h}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Toggles */}
        <button
          onClick={() => setSearchQuery(searchQuery, isRegexSearch, !isCaseSensitiveSearch)}
          className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
            isCaseSensitiveSearch
              ? 'bg-accent/15 text-accent font-semibold'
              : 'hover:bg-hover text-gray-400'
          }`}
          title="Match Case"
        >
          <CaseSensitive size={16} />
        </button>

        <button
          onClick={() => setSearchQuery(searchQuery, !isRegexSearch, isCaseSensitiveSearch)}
          className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
            isRegexSearch
              ? 'bg-accent/15 text-accent font-semibold'
              : 'hover:bg-hover text-gray-400'
          }`}
          title="Use Regular Expression"
        >
          <Type size={16} />
        </button>

        {/* Counter */}
        <div className="ui-text-xs text-gray-400 min-w-[55px] text-center font-bold select-none font-mono">
          {isSearching ? (
            <span className="animate-pulse">Searching...</span>
          ) : matchCount > 0 ? (
            <span>{currentMatch}/{matchCount}</span>
          ) : searchQuery ? (
            <span className="text-red-500 font-semibold">0 matches</span>
          ) : null}
        </div>

        {/* Navigations */}
        <button
          onClick={prevSearchMatch}
          disabled={matchCount === 0}
          className="p-1 rounded-md hover:bg-hover text-gray-400 disabled:opacity-30 disabled:pointer-events-none transition-colors cursor-pointer"
          title="Previous Match (Shift+Enter)"
        >
          <ArrowUp size={16} />
        </button>

        <button
          onClick={nextSearchMatch}
          disabled={matchCount === 0}
          className="p-1 rounded-md hover:bg-hover text-gray-400 disabled:opacity-30 disabled:pointer-events-none transition-colors cursor-pointer"
          title="Next Match (Enter)"
        >
          <ArrowDown size={16} />
        </button>

        {/* Divider */}
        <div className="w-[1px] h-6 bg-border mx-0.5" />

        <button
          onClick={handleClose}
          className="p-1 rounded-md hover:bg-hover text-gray-400 hover:text-red-500 transition-colors cursor-pointer"
          title="Close Search Overlay (Esc)"
        >
          <X size={16} />
        </button>
      </div>
    </div>
  );
};
