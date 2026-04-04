"""
============================================================
SemantiCite.ai — Configuration Management
============================================================
PURPOSE:
    Centralized configuration for the entire backend application.
    Loads sensitive values (API keys, database credentials) from
    environment variables, keeping them out of source code.

ARCHITECTURE ROLE:
    This is the FIRST module loaded by the application.
    All other modules import settings from here instead of
    reading environment variables directly.

USAGE:
    from config import settings
    print(settings.NEO4J_URI)

SETUP:
    1. Copy .env.example to .env
    2. Fill in your API keys and credentials
    3. The application loads .env automatically on startup
============================================================
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# === Load Environment Variables ===
# Look for .env file in the backend directory (where this file lives)
# This file contains secrets like API keys and is NOT committed to git
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    """
    Application settings loaded from environment variables.
    
    Each setting has a sensible default for development,
    but MUST be configured properly for production use.
    """

    # --- Semantic Scholar API ---
    # Free API: 1 req/sec without key, 100 req/sec with key
    # Get your key at: https://www.semanticscholar.org/product/api
    SEMANTIC_SCHOLAR_API_KEY: str = os.getenv("SEMANTIC_SCHOLAR_API_KEY", "")
    SEMANTIC_SCHOLAR_BASE_URL: str = "https://api.semanticscholar.org/graph/v1"
    
    # Toggle to bypass API rate limits during development
    # Change to False once the API key is approved
    USE_MOCK_API: bool = os.getenv("USE_MOCK_API", "False").lower() in ("true", "1", "yes")

    # --- Neo4j Graph Database ---
    # For AuraDB Free: URI looks like "neo4j+s://xxxxx.databases.neo4j.io"
    # For Local Docker: URI is typically "bolt://localhost:7687"
    NEO4J_URI: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")

    # --- OpenAI LLM ---
    # We use gpt-4o-mini for fast, strictly-structured citation classification
    # with high rate limits (~500 RPM on Tier 1).
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")

    # --- Application Settings ---
    # CORS: Which frontend origins are allowed to call our API
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    # Default crawl depth: how many citation levels deep the agent goes
    # Depth 1 = seed papers only, Depth 2 = seed + their references (recommended)
    DEFAULT_CRAWL_DEPTH: int = int(os.getenv("DEFAULT_CRAWL_DEPTH", "2"))
    
    # Maximum number of seed papers to fetch per search query
    MAX_SEED_PAPERS: int = int(os.getenv("MAX_SEED_PAPERS", "5"))
    
    # Maximum citations to process per paper (prevents runaway crawling)
    MAX_CITATIONS_PER_PAPER: int = int(os.getenv("MAX_CITATIONS_PER_PAPER", "10"))


# === Singleton Settings Instance ===
# Import this in other modules: from config import settings
settings = Settings()
