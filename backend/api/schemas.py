"""
============================================================
SemantiCite.ai — API Schemas (Request/Response Models)
============================================================
PURPOSE:
    Defines the exact shape of data going IN and OUT of our API.
    These Pydantic models provide:
    - Automatic request validation (reject malformed requests)
    - Response serialization (convert Python objects to JSON)
    - Auto-generated API documentation (Swagger / OpenAPI)

ARCHITECTURE ROLE:
    API Layer — Sits between the HTTP request and our business logic.
    
    Frontend ──HTTP──> Pydantic Schema ──validated──> Route Handler
    Frontend <──JSON── Pydantic Schema <──────────── Route Handler

WHY PYDANTIC:
    - Type-safe at runtime (not just for IDE hints)
    - Auto-generates OpenAPI docs at /docs
    - Clear error messages when requests are malformed
============================================================
"""

from pydantic import BaseModel, Field
from typing import Optional


# =================================================================
# REQUEST SCHEMAS — What the frontend sends to us
# =================================================================

class SearchRequest(BaseModel):
    """
    Request body for POST /api/search
    
    Sent when a user types a topic and hits "Search".
    The backend will trigger the agent to crawl papers for this topic.
    
    Example:
        {"query": "attention mechanism", "depth": 2, "max_papers": 10}
    """
    query: str = Field(
        ...,  # Required field
        description="Search topic or keywords (e.g., 'transformer architecture')",
        min_length=2,
        max_length=200,
        examples=["attention mechanism", "graph neural networks"],
    )
    depth: int = Field(
        default=2,
        description="How many citation levels deep to crawl (1-3)",
        ge=1,  # Minimum: 1 level
        le=3,  # Maximum: 3 levels (prevents runaway crawling)
    )
    max_papers: int = Field(
        default=10,
        description="Maximum number of seed papers to start from",
        ge=1,
        le=20,
    )


# =================================================================
# RESPONSE SCHEMAS — What we send back to the frontend
# =================================================================

class PaperResponse(BaseModel):
    """
    Response schema for a single paper's data.
    
    Used in:
    - GET /api/paper/{paper_id} — single paper detail view
    - As a nested model in GraphResponse (for each node)
    """
    paper_id: str = Field(description="Unique Semantic Scholar paper ID")
    title: str = Field(description="Full paper title")
    authors: list[str] = Field(default_factory=list, description="Author names")
    year: Optional[int] = Field(default=None, description="Publication year")
    abstract: Optional[str] = Field(default=None, description="Paper abstract")
    citation_count: int = Field(default=0, description="Total citation count")
    url: Optional[str] = Field(default=None, description="Semantic Scholar URL")
    venue: Optional[str] = Field(default=None, description="Journal/conference name")
    fields_of_study: list[str] = Field(default_factory=list, description="Research domains")


class EdgeResponse(BaseModel):
    """
    Response schema for a single citation edge.
    
    Represents: source --[relationship_type]--> target
    The frontend uses this to draw colored, labeled edges in the graph.
    """
    source: str = Field(description="Paper ID of the citing paper")
    target: str = Field(description="Paper ID of the cited paper")
    relationship_type: str = Field(
        description="Semantic label: supports, critiques, extends, uses_method, basis, background"
    )
    context_text: Optional[str] = Field(
        default=None,
        description="The sentence(s) where the citation appears"
    )
    confidence: float = Field(
        default=0.0,
        description="LLM's confidence in the classification (0.0 to 1.0)"
    )
    is_influential: bool = Field(
        default=False,
        description="Whether Semantic Scholar flags this as an influential citation"
    )


class GraphResponse(BaseModel):
    """
    Response schema for GET /api/graph
    
    Contains the full citation graph data needed to render
    the Cytoscape.js visualization on the frontend.
    
    Structure:
        {
            "nodes": [paper1, paper2, ...],
            "edges": [edge1, edge2, ...],
            "stats": {"total_papers": 42, "total_citations": 87}
        }
    """
    nodes: list[PaperResponse] = Field(
        default_factory=list, description="All papers in the graph"
    )
    edges: list[EdgeResponse] = Field(
        default_factory=list, description="All citation relationships"
    )
    stats: dict = Field(
        default_factory=dict, description="Graph statistics"
    )


class PaperDetailResponse(PaperResponse):
    """
    Extended paper response with citation relationship details.
    
    Used when the user clicks a node to see the full paper info
    plus all its incoming and outgoing citation relationships.
    """
    outgoing_citations: list[dict] = Field(
        default_factory=list,
        description="Papers this one cites (with relationship types)"
    )
    incoming_citations: list[dict] = Field(
        default_factory=list,
        description="Papers that cite this one (with relationship types)"
    )


class AgentStatusResponse(BaseModel):
    """
    Response schema for real-time agent status updates.
    
    Sent via Server-Sent Events (SSE) to let the frontend
    show a live progress indicator as the agent works.
    
    Example status messages:
        - "Searching for papers on 'attention mechanism'..."
        - "Found 10 seed papers. Fetching citations..."
        - "Classifying relationship: Paper A → Paper B"
        - "Complete! Discovered 47 papers and 83 relationships."
    """
    task_id: str = Field(description="Unique ID for this agent task")
    status: str = Field(
        description="Current status: pending, running, completed, failed"
    )
    step: str = Field(
        default="",
        description="Current agent step (e.g., 'searching', 'classifying')"
    )
    message: str = Field(
        default="",
        description="Human-readable progress message"
    )
    progress: float = Field(
        default=0.0,
        description="Progress percentage (0.0 to 100.0)"
    )
    papers_found: int = Field(default=0, description="Papers discovered so far")
    edges_created: int = Field(default=0, description="Citation edges created so far")


class StatsResponse(BaseModel):
    """
    Response schema for GET /api/graph/stats
    
    Summary statistics about the current knowledge graph.
    Displayed in the dashboard header or stats panel.
    """
    total_papers: int = Field(default=0, description="Total paper nodes in graph")
    total_citations: int = Field(default=0, description="Total citation edges")
