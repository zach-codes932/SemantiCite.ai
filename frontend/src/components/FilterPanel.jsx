/*
============================================================
SemantiCite.ai — FilterPanel Component
============================================================
PURPOSE:
    A floating panel that allows users to filter the graph
    edges by semantic relationship type (e.g., only show
    "supports" or "critiques").
============================================================
*/

import './FilterPanel.css';
import { FiFilter } from 'react-icons/fi';

const FILTER_OPTIONS = [
  { value: null, label: 'All Relationships' },
  { value: 'supports', label: 'Supports' },
  { value: 'critiques', label: 'Critiques' },
  { value: 'extends', label: 'Extends / Builds Upon' },
  { value: 'uses_method', label: 'Uses Method' },
  { value: 'basis', label: 'Theoretical Basis' },
  { value: 'background', label: 'Background Content' },
];

/**
 * @param {Object}   props
 * @param {string}   props.activeFilter - The currently selected filter key
 * @param {function} props.onChange     - Callback when filter changes
 */
export default function FilterPanel({ activeFilter, onChange }) {
  return (
    <div className="filter-panel glass-card">
      <div className="filter-panel__header">
        <FiFilter size={14} />
        <span>Filter Graph</span>
      </div>
      
      <div className="filter-panel__options">
        {FILTER_OPTIONS.map((option) => (
          <button
            key={option.value || 'all'}
            className={`filter-btn ${activeFilter === option.value ? 'active' : ''}`}
            onClick={() => onChange(option.value)}
          >
            <span
              className="filter-btn__indicator"
              data-type={option.value || 'all'}
            />
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
