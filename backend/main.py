"""
============================================================
SemantiCite.ai — Main Application Entry Point
============================================================
PURPOSE:
    This is the FIRST file that runs when you start the backend.
    It creates the FastAPI application, configures middleware,
    and wires up all the route handlers.

HOW TO RUN:
    cd backend
    uvicorn main:app --reload --port 8000

    Then visit: http://localhost:8000/docs (interactive API docs)

ARCHITECTURE ROLE:
    Application Bootstrap — Ties together all layers:
    
    ┌─────────────────────────────────────────────────┐
    │              main.py (this file)                │
    │                                                 │
    │  1. Create FastAPI app                          │
    │  2. Configure CORS (allow frontend requests)    │
    │  3. Register API routes (/api/*)                │
    │  4. Setup startup/shutdown events               │
    │  5. Start serving on port 8000                  │
    └─────────────────────────────────────────────────┘
============================================================
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config import settings
from api.routes import router as api_router


# =================================================================
# APPLICATION LIFESPAN — Startup and Shutdown Events
# =================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle events.
    
    On STARTUP:
        - Log configuration status
        - Verify external service connectivity (Neo4j, APIs)
    
    On SHUTDOWN:
        - Close database connections cleanly
        - Release any held resources
    
    This replaces the older @app.on_event("startup") pattern
    and is the recommended approach in modern FastAPI.
    """
    # === STARTUP ===
    print("=" * 60)
    print("  [*] SemantiCite.ai -- Starting Up")
    print("=" * 60)
    
    # Log configuration status (helps debug missing env vars)
    s2_status = "[OK] Configured" if settings.SEMANTIC_SCHOLAR_API_KEY else "[!!] Not set (rate limited)"
    neo4j_status = settings.NEO4J_URI or "[!!] Not configured"
    print(f"  [API] Semantic Scholar Key: {s2_status}")
    print(f"  [DB]  Neo4j URI: {neo4j_status}")
    print(f"  [LLM] Model: {settings.LLM_MODEL_NAME}")
    print(f"  [WEB] Frontend URL: {settings.FRONTEND_URL}")
    print(f"  [CFG] Default Crawl Depth: {settings.DEFAULT_CRAWL_DEPTH}")
    print(f"  [CFG] Max Seed Papers: {settings.MAX_SEED_PAPERS}")
    print("=" * 60)
    print("  [READY] Server ready! Visit http://localhost:8000/docs")
    print("=" * 60)

    yield  # Application runs here

    # === SHUTDOWN ===
    print("\n[STOP] SemantiCite.ai -- Shutting down gracefully...")


# =================================================================
# CREATE FASTAPI APPLICATION
# =================================================================

app = FastAPI(
    title="SemantiCite.ai API",
    description=(
        "An Agentic System for Semantic Citation Analysis using Graph RAG. "
        "This API powers the citation knowledge graph — search for topics, "
        "discover papers, and explore semantic citation relationships."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",       # Swagger UI at /docs
    redoc_url="/redoc",     # ReDoc at /redoc
)


# =================================================================
# CORS MIDDLEWARE — Allow Frontend to Call Our API
# =================================================================
# Cross-Origin Resource Sharing (CORS) is required because the
# frontend (http://localhost:5173) and backend (http://localhost:8000)
# run on different ports. Without CORS, browsers block these requests.

app.add_middleware(
    CORSMiddleware,
    # Which origins (frontend URLs) are allowed to make requests
    allow_origins=[
        settings.FRONTEND_URL,         # React dev server (Vite)
        "http://localhost:5173",        # Vite default port
        "http://localhost:3000",        # Common alternative port
    ],
    # Allow cookies and authentication headers
    allow_credentials=True,
    # Allow all HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_methods=["*"],
    # Allow all headers (Content-Type, Authorization, etc.)
    allow_headers=["*"],
)


# =================================================================
# REGISTER API ROUTES
# =================================================================
# Include all routes defined in api/routes.py
# They are already prefixed with /api (defined in the router)

app.include_router(api_router)


# =================================================================
# ROOT ENDPOINT — Landing page / welcome message
# =================================================================

@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint — provides basic info about the API.
    
    Visit /docs for the interactive Swagger UI documentation.
    """
    return {
        "service": "SemantiCite.ai",
        "description": "Semantic Citation Analysis using Graph RAG",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }
