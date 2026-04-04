/*
============================================================
SemantiCite.ai — API Service Layer
============================================================
PURPOSE:
    Centralizes all HTTP calls to the FastAPI backend.
    Every component imports from this single file instead
    of making raw axios calls, keeping things DRY and testable.

ENDPOINTS CONSUMED:
    POST /api/search        → Start a new topic search
    GET  /api/graph         → Retrieve the full citation graph
    GET  /api/paper/{id}    → Get details for a single paper
    GET  /api/status/{id}   → SSE stream for agent progress
    GET  /api/stats         → Graph-wide statistics
    GET  /api/health        → Backend health check
============================================================
*/

import axios from 'axios';

// Base URL for the FastAPI backend (matches FRONTEND_URL in .env)
const API_BASE = 'http://localhost:8000/api';

// Reusable axios instance with default config
const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,  // 30 second timeout
});


// =================================================================
// SEARCH — Kick off the agent to crawl a new topic
// =================================================================

/**
 * Starts a topic search. The backend spawns a background agent
 * and returns a task_id which we use to poll status via SSE.
 *
 * @param {string} query   - The research topic (e.g., "attention mechanism")
 * @param {number} depth   - How many citation layers deep to crawl (1-3)
 * @param {number} maxPapers - Max seed papers to discover
 * @returns {Promise<{task_id: string, message: string}>}
 */
export async function searchTopic(query, depth = 2, maxPapers = 10) {
  const response = await api.post('/search', {
    query,
    depth,
    max_papers: maxPapers,
  });
  return response.data;
}


// =================================================================
// GRAPH — Retrieve the full knowledge graph for visualization
// =================================================================

/**
 * Fetches all papers (nodes) and citations (edges) from Neo4j,
 * formatted for Cytoscape.js consumption.
 *
 * @param {string} [relationshipFilter] - Optional: filter by type (e.g., "supports")
 * @returns {Promise<{nodes: Array, edges: Array}>}
 */
export async function getGraph(relationshipFilter = null) {
  const params = {};
  if (relationshipFilter) {
    params.relationship_type = relationshipFilter;
  }
  const response = await api.get('/graph', { params });
  return response.data;
}


// =================================================================
// GRAPH MANAGEMENT — Reset the database
// =================================================================

/**
 * Deletes all nodes and relationships from the database.
 * 
 * @returns {Promise<{message: string}>}
 */
export async function clearGraph() {
  const response = await api.delete('/graph');
  return response.data;
}


// =================================================================
// PAPER DETAILS — Get full metadata for a single paper
// =================================================================

/**
 * Fetch detailed information about a single paper node.
 *
 * @param {string} paperId - The Semantic Scholar paper ID
 * @returns {Promise<Object>} Full paper metadata
 */
export async function getPaper(paperId) {
  const response = await api.get(`/paper/${paperId}`);
  return response.data;
}


// =================================================================
// AGENT STATUS — Server-Sent Events stream for real-time progress
// =================================================================

/**
 * Opens an SSE connection to stream real-time agent progress.
 * Returns an EventSource object the caller can listen to.
 *
 * Usage:
 *   const es = subscribeToStatus(taskId);
 *   es.onmessage = (event) => { ... };
 *   es.onerror = () => es.close();
 *
 * @param {string} taskId - The task_id returned by searchTopic()
 * @returns {EventSource}
 */
export function subscribeToStatus(taskId) {
  return new EventSource(`${API_BASE}/status/${taskId}`);
}


// =================================================================
// STATISTICS — Overview counts for the dashboard
// =================================================================

/**
 * Get aggregate statistics about the knowledge graph.
 *
 * @returns {Promise<{total_papers: number, total_edges: number, ...}>}
 */
export async function getStats() {
  const response = await api.get('/stats');
  return response.data;
}


// =================================================================
// HEALTH CHECK
// =================================================================

/**
 * Ping the backend to verify connectivity.
 *
 * @returns {Promise<{status: string, service: string, version: string}>}
 */
export async function healthCheck() {
  const response = await api.get('/health');
  return response.data;
}
