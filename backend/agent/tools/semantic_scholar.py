"""
============================================================
SemantiCite.ai — Semantic Scholar API Integration
============================================================
PURPOSE:
    Provides async functions to search for papers and retrieve
    citation data from the Semantic Scholar Academic Graph API.
    This is the "eyes" of our agent — how it discovers papers.

ARCHITECTURE ROLE:
    Agent Tool Layer — Called by the LangGraph agent during
    the "search" and "fetch citations" steps.
    
    ┌──────────────┐     ┌─────────────────┐     ┌──────────────┐
    │  LangGraph   │────>│  This Module    │────>│  Semantic    │
    │  Agent       │<────│  (API wrapper)  │<────│  Scholar API │
    └──────────────┘     └─────────────────┘     └──────────────┘

API DOCUMENTATION:
    https://api.semanticscholar.org/api-docs/graph

KEY ENDPOINTS USED:
    - /paper/search       → Find papers by keyword query
    - /paper/{id}         → Get paper details
    - /paper/{id}/citations    → Get papers that cite this paper
    - /paper/{id}/references   → Get papers this paper references

RATE LIMITS:
    - Without API key: 1 request per second
    - With API key:    100 requests per second
============================================================
"""

import httpx
import asyncio
from typing import Optional
from config import settings
from db.models import PaperNode, CitationContext


# === Constants ===
# Fields we request from the Semantic Scholar API for each paper
# These map directly to the properties in our PaperNode model
PAPER_FIELDS = [
    "paperId", "title", "authors", "year", "abstract",
    "citationCount", "url", "venue", "fieldsOfStudy"
]

# Fields we request for citation/reference relationships
# 'contexts' = the actual sentences where the citation appears
# 'intents' = Semantic Scholar's basic classification (Background, Method, Result)
# 'isInfluential' = whether this is a substantive (not just passing) citation
CITATION_FIELDS = [
    "paperId", "title", "authors", "year", "abstract",
    "citationCount", "url", "venue", "fieldsOfStudy",
    "contexts", "intents", "isInfluential"
]


class SemanticScholarClient:
    """
    Async client for the Semantic Scholar Academic Graph API.
    
    This client handles:
    - Paper search by keyword query
    - Fetching a paper's references (papers it cites)
    - Fetching a paper's citations (papers that cite it)
    - Rate limiting and error handling
    
    Usage:
        async with SemanticScholarClient() as client:
            papers = await client.search_papers("attention mechanism")
            refs = await client.get_references(papers[0].paper_id)
    """

    def __init__(self):
        """Initialize the HTTP client with appropriate headers."""
        # Build request headers
        headers = {"Accept": "application/json"}
        
        # Include API key if available (dramatically increases rate limit)
        if settings.SEMANTIC_SCHOLAR_API_KEY:
            headers["x-api-key"] = settings.SEMANTIC_SCHOLAR_API_KEY

        # httpx.AsyncClient is reusable and manages connection pooling
        self._client = httpx.AsyncClient(
            base_url=settings.SEMANTIC_SCHOLAR_BASE_URL,
            headers=headers,
            timeout=30.0,  # 30 second timeout for slow responses
        )

    async def close(self):
        """Close the HTTP client and release connections."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

    # =================================================================
    # PAPER SEARCH — Finding seed papers for a topic
    # =================================================================

    async def search_papers(
        self,
        query: str,
        limit: int = None,
    ) -> list[PaperNode]:
        """
        Search for papers matching a keyword query.
        
        This is the FIRST step in the agent pipeline:
        User enters "Attention Mechanism" → we find the top seed papers.
        
        Args:
            query: Search keywords (e.g., "transformer architecture NLP")
            limit: Maximum number of papers to return
                   (defaults to MAX_SEED_PAPERS from config)
        
        Returns:
            List of PaperNode objects with metadata from Semantic Scholar
        
        Example API call:
            GET /paper/search?query=attention+mechanism&fields=paperId,title,...&limit=10
        """
        if limit is None:
            limit = settings.MAX_SEED_PAPERS

        # Build the query parameters
        params = {
            "query": query,
            "limit": limit,
            "fields": ",".join(PAPER_FIELDS),
        }

        # Make the API request
        response = await self._client.get("/paper/search", params=params)
        response.raise_for_status()
        data = response.json()

        # Parse API response into PaperNode objects
        papers = []
        for item in data.get("data", []):
            paper = self._parse_paper(item)
            if paper:
                papers.append(paper)

        return papers

    # =================================================================
    # CITATION RETRIEVAL — Getting papers that cite a given paper
    # =================================================================

    async def get_citations(
        self,
        paper_id: str,
        limit: int = None,
    ) -> list[dict]:
        """
        Get papers that CITE the given paper (incoming citations).
        
        Direction: other_paper --cites--> this_paper
        
        This tells us: "Who referenced this work, and in what context?"
        
        Args:
            paper_id: Semantic Scholar paper ID to look up
            limit:    Max citations to return (defaults to config value)
        
        Returns:
            List of dicts with 'paper' (PaperNode) and 'contexts' (CitationContext list)
            
        Example API call:
            GET /paper/{paper_id}/citations?fields=contexts,intents,...&limit=20
        """
        if limit is None:
            limit = settings.MAX_CITATIONS_PER_PAPER

        params = {
            "limit": limit,
            "fields": ",".join(CITATION_FIELDS),
        }

        response = await self._client.get(
            f"/paper/{paper_id}/citations", params=params
        )
        response.raise_for_status()
        data = response.json()

        return self._parse_citation_response(data, cited_paper_id=paper_id)

    # =================================================================
    # REFERENCE RETRIEVAL — Getting papers that a given paper cites
    # =================================================================

    async def get_references(
        self,
        paper_id: str,
        limit: int = None,
    ) -> list[dict]:
        """
        Get papers that the given paper REFERENCES (outgoing citations).
        
        Direction: this_paper --cites--> other_paper
        
        This tells us: "What prior work did this paper build upon?"
        
        Args:
            paper_id: Semantic Scholar paper ID to look up
            limit:    Max references to return (defaults to config value)
        
        Returns:
            List of dicts with 'paper' (PaperNode) and 'contexts' (CitationContext list)
            
        Example API call:
            GET /paper/{paper_id}/references?fields=contexts,intents,...&limit=20
        """
        if limit is None:
            limit = settings.MAX_CITATIONS_PER_PAPER

        params = {
            "limit": limit,
            "fields": ",".join(CITATION_FIELDS),
        }

        response = await self._client.get(
            f"/paper/{paper_id}/references", params=params
        )
        response.raise_for_status()
        data = response.json()

        return self._parse_reference_response(data, citing_paper_id=paper_id)

    # =================================================================
    # SINGLE PAPER LOOKUP
    # =================================================================

    async def get_paper(self, paper_id: str) -> Optional[PaperNode]:
        """
        Fetch full details for a single paper by its ID.
        
        Useful when we have a paper_id from a citation but need
        its complete metadata (abstract, authors, etc.).
        
        Args:
            paper_id: Semantic Scholar paper ID
            
        Returns:
            PaperNode with full metadata, or None if not found
        """
        params = {"fields": ",".join(PAPER_FIELDS)}

        try:
            response = await self._client.get(
                f"/paper/{paper_id}", params=params
            )
            response.raise_for_status()
            return self._parse_paper(response.json())
        except httpx.HTTPStatusError:
            return None

    # =================================================================
    # INTERNAL HELPERS — Parsing API responses into our models
    # =================================================================

    def _parse_paper(self, data: dict) -> Optional[PaperNode]:
        """
        Convert a raw Semantic Scholar API response into a PaperNode.
        
        Handles missing/null fields gracefully — the API doesn't
        guarantee all fields are present for every paper.
        """
        paper_id = data.get("paperId")
        if not paper_id:
            return None

        # Extract author names from the nested author objects
        # API returns: [{"authorId": "123", "name": "John Doe"}, ...]
        authors = []
        for author in data.get("authors", []) or []:
            if isinstance(author, dict) and author.get("name"):
                authors.append(author["name"])

        return PaperNode(
            paper_id=paper_id,
            title=data.get("title", "Untitled"),
            authors=authors,
            year=data.get("year"),
            abstract=data.get("abstract"),
            citation_count=data.get("citationCount", 0) or 0,
            url=data.get("url"),
            venue=data.get("venue"),
            fields_of_study=data.get("fieldsOfStudy") or [],
        )

    def _parse_citation_response(
        self, data: dict, cited_paper_id: str
    ) -> list[dict]:
        """
        Parse the /citations endpoint response.
        
        For citations, the direction is:
        citingPaper --cites--> our paper (cited_paper_id)
        
        Returns list of dicts with 'paper' and 'contexts' keys.
        """
        results = []
        for item in data.get("data", []):
            citing_paper_data = item.get("citingPaper", {})
            paper = self._parse_paper(citing_paper_data)
            if not paper:
                continue

            # Extract citation contexts (the sentences where citation appears)
            contexts = []
            raw_contexts = item.get("contexts", []) or []
            raw_intents = item.get("intents", []) or []

            for ctx_text in raw_contexts:
                if ctx_text:  # Skip empty context strings
                    contexts.append(CitationContext(
                        citing_paper_id=paper.paper_id,
                        cited_paper_id=cited_paper_id,
                        context_text=ctx_text,
                        intents=raw_intents,
                    ))

            results.append({
                "paper": paper,
                "contexts": contexts,
                "is_influential": item.get("isInfluential", False),
            })

        return results

    def _parse_reference_response(
        self, data: dict, citing_paper_id: str
    ) -> list[dict]:
        """
        Parse the /references endpoint response.
        
        For references, the direction is:
        our paper (citing_paper_id) --cites--> citedPaper
        
        Returns list of dicts with 'paper' and 'contexts' keys.
        """
        results = []
        for item in data.get("data", []):
            cited_paper_data = item.get("citedPaper", {})
            paper = self._parse_paper(cited_paper_data)
            if not paper:
                continue

            # Extract citation contexts
            contexts = []
            raw_contexts = item.get("contexts", []) or []
            raw_intents = item.get("intents", []) or []

            for ctx_text in raw_contexts:
                if ctx_text:
                    contexts.append(CitationContext(
                        citing_paper_id=citing_paper_id,
                        cited_paper_id=paper.paper_id,
                        context_text=ctx_text,
                        intents=raw_intents,
                    ))

            results.append({
                "paper": paper,
                "contexts": contexts,
                "is_influential": item.get("isInfluential", False),
            })

        return results
