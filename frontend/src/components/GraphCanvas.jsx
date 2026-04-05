/*
============================================================
SemantiCite.ai — GraphCanvas Component
============================================================
PURPOSE:
    The centerpiece of the application. Renders the citation
    knowledge graph using Cytoscape.js with interactive
    pan/zoom, node click events, and color-coded edges.

ARCHITECTURE:
    DOM Ref → Cytoscape Instance → Live Data from Backend
    - Nodes = Papers (circles, sized by citation count)
    - Edges = Citation relationships (colored by type)

INTERACTIONS:
    - Click a node → Open PaperDetailPanel with paper info
    - Hover a node → Highlight its connections
    - Scroll → Zoom in/out
    - Drag → Pan the view
============================================================
*/

import { useRef, useEffect, useCallback } from 'react';
import cytoscape from 'cytoscape';
import './GraphCanvas.css';

const EDGE_COLORS = {
  supports:    '#10b981', /* Green */
  critiques:   '#f43f5e', /* Rose/Red */
  extends:     '#818cf8', /* Soft Indigo */
  uses_method: '#06b6d4', /* Cyan (changed from amber so it contrasts with nodes) */
  basis:       '#c084fc', /* Soft Violet */
  background:  '#52525b', /* Zinc (sleeker grey) */
};

/* ---------- Cytoscape stylesheet (visual rules) ---------- */
const cytoscapeStylesheet = [
  /* Node (Paper) styling */
  {
    selector: 'node',
    style: {
      'label': 'data(label)',
      'text-wrap': 'wrap',
      'text-max-width': '38px', /* Strict width before wrapping inside circle */
      'line-height': 1.1,
      'font-size': '8px',
      'font-family': 'Inter, sans-serif',
      'color': '#000000', /* High-contrast pure black text to match Neo4j */
      'text-valign': 'center', /* Vertically center inside the node */
      'text-halign': 'center', /* Horizontally center inside the node */
      'text-outline-width': 0, /* Remove outline so it looks flat inside */

      /* Circle appearance */
      'background-color': '#ff8a80', /* Neo4j-style pastel Coral/Salmon */
      'background-opacity': 1,
      'border-width': 0, /* Neo4j console usually shows flat borderless nodes */

      /* Size proportional to citation count (increased to fit text!) */
      'width': 'mapData(citations, 0, 50000, 45, 85)',
      'height': 'mapData(citations, 0, 50000, 45, 85)',

      /* Smooth transitions on state change */
      'transition-property': 'background-color, border-color, width, height',
      'transition-duration': '0.2s',
    },
  },

  /* Hovered node — enlarge and glow */
  {
    selector: 'node:active, node:selected',
    style: {
      'background-color': '#ffb0a8', /* Lighter coral */
      'border-color': '#ffccc7',
      'border-width': 2,
      'overlay-opacity': 0,
    },
  },

  /* Seed papers (larger, different color to distinguish origin) */
  {
    selector: 'node[?isSeed]',
    style: {
      'background-color': '#e53935', /* Deep red to make seeds pop against coral graph */
      'color': '#ffffff', /* White text for deep red background */
    },
  },

  /* Edge (Citation) styling */
  {
    selector: 'edge',
    style: {
      'width': 2.5, /* Thicker line for better color visibility */
      'line-color': 'data(color)',
      'target-arrow-color': 'data(color)',
      'target-arrow-shape': 'triangle',
      'arrow-scale': 1.2, /* Larger arrowheads */
      'curve-style': 'bezier',
      'opacity': 0.95, /* Higher opacity so colors pop */
      'transition-property': 'opacity, width',
      'transition-duration': '0.2s',
    },
  },

  /* Highlighted edges (when a node is hovered) */
  {
    selector: 'edge.highlighted',
    style: {
      'opacity': 1,
      'width': 3,
    },
  },

  /* Dimmed elements (non-highlighted when hovering a node) */
  {
    selector: '.dimmed',
    style: {
      'opacity': 0.15,
    },
  },
];


/**
 * @param {Object} props
 * @param {Object}   props.graphData      - {nodes: [...], edges: [...]} from the API
 * @param {function} props.onNodeClick    - Callback when a paper node is clicked
 * @param {string}   props.activeFilter   - Currently active relationship type filter
 */
export default function GraphCanvas({ graphData, onNodeClick, activeFilter }) {
  const containerRef = useRef(null);
  const cyRef = useRef(null);

  /**
   * Transform our backend data into Cytoscape-compatible elements.
   * Backend returns papers and edges; we map them to cy nodes/edges.
   */
  const buildElements = useCallback(() => {
    if (!graphData) return [];

    const elements = [];

    /* --- Nodes (Papers) --- */
    (graphData.nodes || []).forEach((paper) => {
      elements.push({
        data: {
          id: paper.paper_id || paper.id,
          // Shorter label so it wraps cleanly inside 45px bubbles
          label: paper.title ? paper.title.substring(0, 18) + (paper.title.length > 18 ? '...' : '') : 'Untitled',
          fullTitle: paper.title,
          year: paper.year,
          citations: paper.citation_count || 0,
          authors: paper.authors || [],
          venue: paper.venue || '',
          isSeed: paper.is_seed || false,
        },
      });
    });

    /* --- Edges (Citations) --- */
    (graphData.edges || []).forEach((edge) => {
      const relType = edge.relationship_type || 'background';
      // Optionally filter by active relationship
      if (activeFilter && relType !== activeFilter) return;

      elements.push({
        data: {
          id: `${edge.source}-${edge.target}-${relType}`,
          source: edge.source,
          target: edge.target,
          relType: relType,
          color: EDGE_COLORS[relType] || EDGE_COLORS.background,
          confidence: edge.confidence || 0,
        },
      });
    });

    return elements;
  }, [graphData, activeFilter]);


  /* --- Initialize Cytoscape instance on mount --- */
  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      elements: buildElements(),
      style: cytoscapeStylesheet,
      layout: {
        name: 'cose',              // Force-directed layout
        animate: true,
        animationDuration: 800,
        nodeRepulsion: () => 8000,  // How far nodes push each other apart
        idealEdgeLength: () => 120, // Preferred edge length
        padding: 40,
      },
      // Interaction settings
      minZoom: 0.3,
      maxZoom: 3,
      wheelSensitivity: 0.3,
    });

    /* --- Event: Click a node → show paper details --- */
    cy.on('tap', 'node', (event) => {
      const nodeData = event.target.data();
      if (onNodeClick) {
        onNodeClick(nodeData);
      }
    });

    /* --- Event: Hover a node → highlight its edges --- */
    cy.on('mouseover', 'node', (event) => {
      const node = event.target;
      const neighborhood = node.neighborhood().add(node);
      // Dim everything
      cy.elements().addClass('dimmed');
      // Un-dim the hovered node and its connections
      neighborhood.removeClass('dimmed');
      neighborhood.edges().addClass('highlighted');
    });

    /* --- Event: Mouse out → restore all elements --- */
    cy.on('mouseout', 'node', () => {
      cy.elements().removeClass('dimmed').removeClass('highlighted');
    });

    cyRef.current = cy;

    // Cleanup on unmount
    return () => {
      cy.destroy();
    };
  }, []); // Only run once on mount


  /* --- Update elements when graphData or filter changes --- */
  useEffect(() => {
    if (!cyRef.current) return;

    const cy = cyRef.current;
    const newElements = buildElements();

    // Replace all elements and re-layout
    cy.elements().remove();
    cy.add(newElements);

    // Re-run the layout to animate new nodes into place
    cy.layout({
      name: 'cose',
      animate: true,
      animationDuration: 600,
      nodeRepulsion: () => 8000,
      idealEdgeLength: () => 120,
      padding: 40,
    }).run();

  }, [graphData, activeFilter, buildElements]);


  return (
    <div className="graph-canvas">
      {/* The Cytoscape.js div — it needs an explicit height */}
      <div ref={containerRef} className="graph-canvas__container" />

      {/* Empty state — shown when no graph data exists */}
      {(!graphData || !graphData.nodes || graphData.nodes.length === 0) && (
        <div className="graph-canvas__empty">
          <div className="graph-canvas__empty-icon">
            <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <circle cx="12" cy="12" r="3" />
              <circle cx="4" cy="6" r="2" />
              <circle cx="20" cy="6" r="2" />
              <circle cx="4" cy="18" r="2" />
              <circle cx="20" cy="18" r="2" />
              <line x1="9.5" y1="10.5" x2="5.5" y2="7.5" />
              <line x1="14.5" y1="10.5" x2="18.5" y2="7.5" />
              <line x1="9.5" y1="13.5" x2="5.5" y2="16.5" />
              <line x1="14.5" y1="13.5" x2="18.5" y2="16.5" />
            </svg>
          </div>
          <h3>No Graph Data Yet</h3>
          <p>Search for a research topic above to build the citation knowledge graph.</p>
        </div>
      )}
    </div>
  );
}
