/*
============================================================
SemantiCite.ai — Main Application Component (App.jsx)
============================================================
PURPOSE:
    The central point that ties everything together.
    Manages the application state (Graph Data, Agent Progress,
    Selected Node, Filter) and renders the layout.
============================================================
*/

import { useState, useEffect } from 'react';
import Header from './components/Header';
import SearchBar from './components/SearchBar';
import GraphCanvas from './components/GraphCanvas';
import PaperDetailPanel from './components/PaperDetailPanel';
import FilterPanel from './components/FilterPanel';
import { searchTopic, getGraph, getStats, subscribeToStatus, clearGraph } from './services/api';

export default function App() {
  // Application State
  const [graphData, setGraphData] = useState(null);
  const [stats, setStats] = useState(null);
  const [activePaper, setActivePaper] = useState(null);
  const [activeFilter, setActiveFilter] = useState(null);
  
  // Agent / Background Task State
  const [isAgentRunning, setIsAgentRunning] = useState(false);
  const [agentProgress, setAgentProgress] = useState(null);

  // Load initial graph data on mount
  useEffect(() => {
    fetchGraphAndStats();
  }, [activeFilter]); // Re-fetch graph if the user changes the filter

  const fetchGraphAndStats = async () => {
    try {
      const gData = await getGraph(activeFilter);
      setGraphData(gData);
      
      const st = await getStats();
      setStats(st);
    } catch (err) {
      console.error("Error fetching graph data:", err);
    }
  };

  /**
   * Triggers the backend LLM agent to crawl a new topic
   */
  const handleSearch = async (query, depth) => {
    try {
      setIsAgentRunning(true);
      setAgentProgress({ message: 'Initializing...', progress: 5 });
      setActivePaper(null); // Close panel if open

      // 1. Send the POST request to start the background agent
      const response = await searchTopic(query, depth);
      const taskId = response.task_id;

      // 2. Open an SSE stream to listen for progress updates
      const sse = subscribeToStatus(taskId);
      
      sse.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log("Agent update:", data);
        
        setAgentProgress(data);
        
        // When completed, close the stream and refresh the graph
        if (data.status === 'completed' || data.status === 'failed') {
          sse.close();
          setIsAgentRunning(false);
          // Wait a short moment then pull the newly generated graph data
          setTimeout(() => {
            fetchGraphAndStats();
            setAgentProgress(null);
          }, 1500);
        }
      };

      sse.onerror = () => {
        sse.close();
        setIsAgentRunning(false);
        setAgentProgress(null);
      };

    } catch (err) {
      console.error("Failed to start search:", err);
      setIsAgentRunning(false);
    }
  };

  /**
   * Resets the entire knowledge graph database
   */
  const handleClearGraph = async () => {
    try {
      await clearGraph();
      // Reset local state for immediate feedback
      setGraphData({ nodes: [], edges: [] });
      setStats({ total_papers: 0, total_citations: 0 });
      setActivePaper(null);
      console.log("Graph cleared successfully.");
    } catch (err) {
      console.error("Failed to clear graph:", err);
      alert("Error: Could not clear the graph. Check backend logs.");
    }
  };

  return (
    <div className="layout">
      <Header />
      
      <main className="layout__main">
        {/* Top Control Bar */}
        <section className="layout__controls">
          <SearchBar 
            onSearch={handleSearch} 
            isLoading={isAgentRunning} 
            progress={agentProgress} 
          />
        </section>

        {/* Dashboard Area */}
        <section className="layout__dashboard">
          <GraphCanvas 
            graphData={graphData} 
            onNodeClick={setActivePaper}
            activeFilter={activeFilter}
          />
          
          <FilterPanel 
            activeFilter={activeFilter} 
            onChange={setActiveFilter} 
            onClear={handleClearGraph}
          />
          
          <PaperDetailPanel 
            paper={activePaper} 
            onClose={() => setActivePaper(null)} 
          />

          {/* Inline Statistics Overlay at bottom right */}
          {stats && !activePaper && (
            <div className="layout__stats glass-card animate-fade-in">
              <div className="layout__stat-item">
                <span className="layout__stat-val">{stats.total_papers || 0}</span>
                <span className="layout__stat-lbl">Papers</span>
              </div>
              <div className="layout__stat-item">
                <span className="layout__stat-val">{stats.total_citations || 0}</span>
                <span className="layout__stat-lbl">Citations</span>
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
