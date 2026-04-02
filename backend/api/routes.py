"""
============================================================
SemantiCite.ai — API Routes
============================================================
PURPOSE:
    Defines all HTTP endpoints that the frontend calls.
    This is the "front door" of our backend — every user action
    in the dashboard ultimately hits one of these routes.

ARCHITECTURE ROLE:
    API Layer — Receives HTTP requests, delegates to business logic,
    and returns structured responses.
    
    Frontend ──HTTP──> Routes ──> Agent / Neo4j Client ──> Response

ENDPOINTS OVERVIEW:
    POST /api/search           → Trigger the agent to crawl a topic
    GET  /api/graph            → Get the full citation graph
    GET  /api/paper/{id}       → Get details for a single paper
    GET  /api/status/{task_id} → SSE stream of agent progress
    GET  /api/stats            → Graph statistics (paper/edge counts)
    GET  /api/health           → Health check endpoint
============================================================
"""

import uuid
import asyncio
from fastapi import APIRouter, HTTPException, BackgroundTasks
from sse_starlette.sse import EventSourceResponse
from typing import AsyncGenerator

from api.schemas import (
    SearchRequest,
    GraphResponse,
    PaperDetailResponse,
    AgentStatusResponse,
    StatsResponse,
)
from db.neo4j_client import Neo4jClient

# === Router Setup ===
# APIRouter groups related endpoints together.
# Prefixed with /api so all routes are under /api/*
router = APIRouter(prefix="/api", tags=["SemantiCite API"])

# === In-Memory Task Store ===
# Tracks the status of running agent tasks.
# In production, this would be Redis or a database.
# For our MCA project, in-memory is perfectly fine.
agent_tasks: dict[str, AgentStatusResponse] = {}


# =================================================================
# SEARCH — Trigger the agent to crawl papers for a topic
# =================================================================

@router.post("/search", response_model=AgentStatusResponse)
async def search_topic(
    request: SearchRequest,
    background_tasks: BackgroundTasks,
):
    """
    Start a new citation analysis for the given topic.
    
    Flow:
    1. User submits a search query (e.g., "attention mechanism")
    2. This endpoint creates a task ID and returns it immediately
    3. The agent runs in the background, crawling papers
    4. Frontend polls /api/status/{task_id} for live updates
    
    This is ASYNC — we return instantly and process in the background
    so the frontend stays responsive.
    """
    # Generate a unique task ID for tracking this search
    task_id = str(uuid.uuid4())

    # Initialize task status (the frontend will poll this)
    agent_tasks[task_id] = AgentStatusResponse(
        task_id=task_id,
        status="pending",
        step="initializing",
        message=f"Starting search for '{request.query}'...",
        progress=0.0,
    )

    # Launch the agent in the background
    # BackgroundTasks runs after the response is sent
    background_tasks.add_task(
        run_agent_task,
        task_id=task_id,
        query=request.query,
        depth=request.depth,
        max_papers=request.max_papers,
    )

    return agent_tasks[task_id]


# =================================================================
# GRAPH — Retrieve the full citation knowledge graph
# =================================================================

@router.get("/graph", response_model=GraphResponse)
async def get_graph():
    """
    Retrieve all papers and citation relationships from Neo4j.
    
    This is the main data source for the Cytoscape.js visualization.
    Returns nodes (papers) and edges (citation relationships) in a
    format ready for direct consumption by the frontend.
    
    Called when:
    - The dashboard first loads
    - After an agent task completes (to refresh the graph)
    """
    try:
        async with Neo4jClient() as client:
            graph_data = await client.get_graph_for_topic("")
            stats = await client.get_graph_stats()

        return GraphResponse(
            nodes=graph_data.get("nodes", []),
            edges=graph_data.get("edges", []),
            stats=stats,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve graph: {str(e)}"
        )


# =================================================================
# PAPER DETAILS — Get full info for a single paper
# =================================================================

@router.get("/paper/{paper_id}", response_model=PaperDetailResponse)
async def get_paper(paper_id: str):
    """
    Retrieve detailed information for a specific paper.
    
    Called when the user clicks on a node in the graph visualization.
    Returns the paper's metadata plus all its incoming and outgoing
    citation relationships with context sentences.
    """
    try:
        async with Neo4jClient() as client:
            paper = await client.get_paper_by_id(paper_id)

        if not paper:
            raise HTTPException(
                status_code=404,
                detail=f"Paper with ID '{paper_id}' not found in the graph"
            )
        return PaperDetailResponse(**paper)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve paper: {str(e)}"
        )


# =================================================================
# STATUS — Real-time agent progress via Server-Sent Events (SSE)
# =================================================================

@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Stream real-time agent progress updates via SSE.
    
    The frontend connects to this endpoint after starting a search
    and receives live updates as the agent discovers papers:
    
    Event stream example:
        data: {"status": "running", "message": "Found 5 seed papers..."}
        data: {"status": "running", "message": "Classifying Paper A → Paper B..."}
        data: {"status": "completed", "message": "Done! 47 papers, 83 edges"}
    
    SSE (Server-Sent Events) is simpler than WebSockets for one-way
    server-to-client communication, which is all we need here.
    """
    if task_id not in agent_tasks:
        raise HTTPException(
            status_code=404,
            detail=f"Task '{task_id}' not found"
        )

    async def event_generator() -> AsyncGenerator:
        """Yield status updates until the task completes or fails."""
        while True:
            if task_id in agent_tasks:
                task = agent_tasks[task_id]
                yield {
                    "event": "status",
                    "data": task.model_dump_json(),
                }
                # Stop streaming if the task is done
                if task.status in ("completed", "failed"):
                    break
            await asyncio.sleep(1)  # Poll every second

    return EventSourceResponse(event_generator())


# =================================================================
# STATISTICS — Graph summary metrics
# =================================================================

@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """
    Get summary statistics about the knowledge graph.
    
    Returns total paper count and citation count.
    Displayed in the dashboard header for quick overview.
    """
    try:
        async with Neo4jClient() as client:
            stats = await client.get_graph_stats()
        return StatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve stats: {str(e)}"
        )


# =================================================================
# HEALTH CHECK — Verify the backend is running
# =================================================================

@router.get("/health")
async def health_check():
    """
    Simple health check endpoint.
    
    Used by:
    - Frontend to verify backend connectivity
    - Deployment monitoring tools
    - Quick manual testing: curl http://localhost:8000/api/health
    """
    return {
        "status": "healthy",
        "service": "SemantiCite.ai Backend",
        "version": "1.0.0",
    }


# =================================================================
# BACKGROUND TASK — Agent execution (placeholder for Phase 2)
# =================================================================

from agent.orchestrator import agent_graph

async def run_agent_task(
    task_id: str,
    query: str,
    depth: int,
    max_papers: int,
):
    """
    Execute the LangGraph agent pipeline in the background.
    """
    try:
        # --- Step 1: Update status to "running" ---
        agent_tasks[task_id].status = "running"
        agent_tasks[task_id].step = "initializing"
        agent_tasks[task_id].message = f"Initializing agent for '{query}'..."
        agent_tasks[task_id].progress = 5.0

        # Define the initial state for LangGraph
        initial_state = {
            "topic": query,
            "max_depth": depth,
            "current_depth": 0,
            "task_id": task_id,
            "papers_to_process": [],
            "processed_paper_ids": set(),
            "total_papers_found": 0,
            "total_edges_created": 0
        }

        agent_tasks[task_id].step = "processing"
        agent_tasks[task_id].message = "Agent is traversing the citation graph..."
        agent_tasks[task_id].progress = 20.0

        # Run the agent synchronously inside an async wrapper
        # LangGraph exposes ainvoke for async execution
        final_state = await agent_graph.ainvoke(initial_state)

        # --- Finalizing task ---
        agent_tasks[task_id].status = "completed"
        agent_tasks[task_id].step = "done"
        
        papers = final_state.get('total_papers_found', 0)
        edges = final_state.get('total_edges_created', 0)
        agent_tasks[task_id].message = f"Done! Discovered {papers} papers and {edges} semantic relationships."
        agent_tasks[task_id].progress = 100.0
        agent_tasks[task_id].papers_found = papers
        agent_tasks[task_id].edges_created = edges

    except Exception as e:
        # --- Error handling: mark task as failed ---
        import traceback
        traceback.print_exc()
        agent_tasks[task_id].status = "failed"
        agent_tasks[task_id].message = f"Error: {str(e)}"
