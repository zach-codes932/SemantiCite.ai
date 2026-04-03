/*
============================================================
SemantiCite.ai — Header Component
============================================================
PURPOSE:
    Top navigation bar with the app logo, tagline, and
    a real-time backend status indicator (green/red dot).
============================================================
*/

import { useState, useEffect } from 'react';
import { healthCheck } from '../services/api';
import { FiActivity, FiGlobe } from 'react-icons/fi';
import './Header.css';

export default function Header() {
  // Track whether the backend API is reachable
  const [backendOnline, setBackendOnline] = useState(false);

  // Ping the backend on mount to show connectivity status
  useEffect(() => {
    healthCheck()
      .then(() => setBackendOnline(true))
      .catch(() => setBackendOnline(false));
  }, []);

  return (
    <header className="header">
      <div className="header__inner">
        {/* === Logo & Brand === */}
        <div className="header__brand">
          <div className="header__logo-icon">
            <FiGlobe size={22} />
          </div>
          <div>
            <h1 className="header__title">
              Semanti<span className="gradient-text">Cite</span>.ai
            </h1>
            <p className="header__tagline">
              Agentic Citation Analysis with Graph RAG
            </p>
          </div>
        </div>

        {/* === Status Indicator === */}
        <div className="header__status">
          <span
            className={`header__status-dot ${backendOnline ? 'online' : 'offline'}`}
          />
          <span className="header__status-text">
            {backendOnline ? 'Backend Online' : 'Backend Offline'}
          </span>
          <FiActivity size={14} className="header__status-icon" />
        </div>
      </div>
    </header>
  );
}
