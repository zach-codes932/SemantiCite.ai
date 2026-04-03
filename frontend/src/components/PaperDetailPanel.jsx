/*
============================================================
SemantiCite.ai — PaperDetailPanel Component
============================================================
PURPOSE:
    A slide-in panel that shows detailed information about
    a paper when the user clicks on a node in the graph.

DISPLAYS:
    - Paper title, authors, year, venue
    - Abstract (truncated with "show more")
    - Citation count
    - Link to Semantic Scholar page
    - Incoming/outgoing relationship badges
============================================================
*/

import { FiX, FiExternalLink, FiBookOpen, FiUsers, FiCalendar, FiHash } from 'react-icons/fi';
import './PaperDetailPanel.css';

/**
 * @param {Object}   props
 * @param {Object}   props.paper   - Paper data from the graph node click
 * @param {function} props.onClose - Callback to dismiss the panel
 */
export default function PaperDetailPanel({ paper, onClose }) {
  if (!paper) return null;

  return (
    <div className="paper-panel glass-card animate-fade-in">
      {/* === Panel Header === */}
      <div className="paper-panel__header">
        <h2 className="paper-panel__title">{paper.fullTitle || paper.label}</h2>
        <button
          id="paper-panel-close"
          className="paper-panel__close"
          onClick={onClose}
          title="Close panel"
        >
          <FiX size={18} />
        </button>
      </div>

      {/* === Metadata Grid === */}
      <div className="paper-panel__meta">
        {/* Year */}
        {paper.year && (
          <div className="paper-panel__meta-item">
            <FiCalendar size={14} />
            <span>{paper.year}</span>
          </div>
        )}

        {/* Citation count */}
        <div className="paper-panel__meta-item">
          <FiHash size={14} />
          <span>{(paper.citations || 0).toLocaleString()} citations</span>
        </div>

        {/* Venue */}
        {paper.venue && (
          <div className="paper-panel__meta-item">
            <FiBookOpen size={14} />
            <span>{paper.venue}</span>
          </div>
        )}
      </div>

      {/* === Authors === */}
      {paper.authors && paper.authors.length > 0 && (
        <div className="paper-panel__section">
          <h3 className="paper-panel__section-title">
            <FiUsers size={14} /> Authors
          </h3>
          <p className="paper-panel__authors">
            {paper.authors.join(', ')}
          </p>
        </div>
      )}

      {/* === Abstract === */}
      {paper.abstract && (
        <div className="paper-panel__section">
          <h3 className="paper-panel__section-title">
            <FiBookOpen size={14} /> Abstract
          </h3>
          <p className="paper-panel__abstract">{paper.abstract}</p>
        </div>
      )}

      {/* === External Link === */}
      {paper.url && (
        <a
          href={paper.url}
          target="_blank"
          rel="noopener noreferrer"
          className="btn-primary paper-panel__link"
        >
          <FiExternalLink size={14} />
          View on Semantic Scholar
        </a>
      )}
    </div>
  );
}
