/*
============================================================
SemantiCite.ai — SearchBar Component
============================================================
PURPOSE:
    The main user input — a search box where the user types
    a research topic. On submit, it fires the agent pipeline
    and shows real-time progress via SSE.
============================================================
*/

import { useState } from 'react';
import { FiSearch, FiSliders } from 'react-icons/fi';
import './SearchBar.css';

/**
 * @param {Object} props
 * @param {function} props.onSearch  - Callback when user submits a query
 * @param {boolean}  props.isLoading - Whether the agent is currently running
 * @param {Object}   props.progress  - Current agent status object {step, message, progress}
 */
export default function SearchBar({ onSearch, isLoading, progress }) {
  const [query, setQuery] = useState('');
  const [depth, setDepth] = useState(2);
  const [showOptions, setShowOptions] = useState(false);

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    if (query.trim() && !isLoading) {
      onSearch(query.trim(), depth);
    }
  };

  return (
    <div className={`search-bar animate-fade-in ${isLoading ? 'search-bar--loading' : ''}`}>
      {/* === Search Form === */}
      <form className="search-bar__form" onSubmit={handleSubmit}>
        <div className="search-bar__input-wrapper">
          <FiSearch className="search-bar__icon" size={18} />
          <input
            id="search-input"
            type="text"
            className="search-bar__input"
            placeholder='Search a research topic (e.g., "Attention Mechanism") ...'
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isLoading}
            autoFocus
          />
          {/* Options toggle */}
          <button
            type="button"
            className="btn-ghost search-bar__options-btn"
            onClick={() => setShowOptions(!showOptions)}
            title="Search options"
          >
            <FiSliders size={16} />
          </button>
        </div>

        {/* === Submit Button === */}
        <button
          id="search-submit-btn"
          type="submit"
          className="btn-primary search-bar__submit"
          disabled={!query.trim() || isLoading}
        >
          {isLoading ? (
            <>
              <span className="loading-spinner" />
              Crawling...
            </>
          ) : (
            <>
              <FiSearch size={16} />
              Explore
            </>
          )}
        </button>
      </form>

      {/* === Advanced Options (collapsible) === */}
      {showOptions && (
        <div className="search-bar__options animate-fade-in">
          <label className="search-bar__option-label">
            Crawl Depth:
            <select
              className="search-bar__select"
              value={depth}
              onChange={(e) => setDepth(Number(e.target.value))}
            >
              <option value={1}>1 — Seed papers only</option>
              <option value={2}>2 — Seed + their citations (recommended)</option>
              <option value={3}>3 — Deep crawl (slower, richer graph)</option>
            </select>
          </label>
        </div>
      )}

      {/* === Agent Progress Bar (shown only while running) === */}
      {isLoading && progress && (
        <div className="search-bar__progress">
          <div className="search-bar__progress-bar">
            <div
              className="search-bar__progress-fill"
              style={{ width: `${progress.progress || 0}%` }}
            />
          </div>
          <p className="search-bar__progress-text">
            {progress.message || 'Starting agent...'}
          </p>
        </div>
      )}
    </div>
  );
}
