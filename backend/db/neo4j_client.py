"""
============================================================
SemantiCite.ai — Neo4j Graph Database Client
============================================================
PURPOSE:
    Manages all interactions with the Neo4j graph database.
    This is the ONLY module that speaks to Neo4j directly.
    All other modules use this client to read/write graph data.

ARCHITECTURE ROLE:
    Data Layer — Sits between the Agent/API and the database.
    
    ┌──────────────┐     ┌───────────────┐     ┌─────────┐
    │ Agent Tools / │────>│ Neo4j Client  │────>│  Neo4j  │
    │ API Routes   │<────│ (this file)   │<────│  AuraDB │
    └──────────────┘     └───────────────┘     └─────────┘

GRAPH SCHEMA:
    Nodes:  (:Paper {paper_id, title, authors, year, abstract, ...})
    Edges:  (:Paper)-[:CITES {type, context, confidence}]->(:Paper)

KEY DESIGN DECISIONS:
    - Uses MERGE instead of CREATE to prevent duplicate nodes/edges
    - Async-compatible using Neo4j's async driver
    - Singleton pattern ensures one connection pool per application
============================================================
"""

from neo4j import AsyncGraphDatabase, AsyncDriver
from typing import Optional
import asyncio
from config import settings
from db.models import PaperNode, CitationEdge, RelationshipType


class Neo4jClient:
    """
    Async client for Neo4j graph database operations.
    
    Usage:
        client = Neo4jClient()
        await client.connect()
        await client.create_paper(paper_node)
        await client.close()
    
    Or as an async context manager:
        async with Neo4jClient() as client:
            await client.create_paper(paper_node)
    """

    def __init__(self):
        """Initialize the client. Call connect() to establish the connection."""
        self._driver: Optional[AsyncDriver] = None

    # =================================================================
    # CONNECTION MANAGEMENT
    # =================================================================

    async def connect(self):
        """
        Establish connection to Neo4j database.
        
        Uses the credentials from config.py (loaded from .env).
        The driver manages a connection pool internally,
        so we only need one instance for the entire application.
        """
        self._driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            connection_timeout=15.0, # 15 second timeout for initial connection
            max_connection_lifetime=600, # 10 minutes max connection age
        )
        # Verify the connection is working
        try:
            await asyncio.wait_for(self._driver.verify_connectivity(), timeout=20.0)
        except asyncio.TimeoutError:
            print("  [ERROR] Neo4j connection timed out during verification.")
            raise Exception("Neo4j connection timed out.")

    async def close(self):
        """Close the database connection and release all resources."""
        if self._driver:
            await self._driver.close()
            self._driver = None

    async def __aenter__(self):
        """Support 'async with Neo4jClient() as client:' syntax."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Auto-close connection when exiting 'async with' block."""
        await self.close()

    # =================================================================
    # WRITE OPERATIONS — Creating Nodes and Edges
    # =================================================================

    async def create_paper(self, paper: PaperNode) -> None:
        """
        Create or update a Paper node in the graph.
        
        Uses MERGE to prevent duplicates: if a paper with the same
        paper_id already exists, it updates the properties instead
        of creating a duplicate.
        
        Args:
            paper: PaperNode dataclass with paper metadata
        """
        # Cypher query explanation:
        # MERGE = "find or create" — idempotent operation
        # ON CREATE SET = only set these properties when creating a new node
        # ON MATCH SET  = update these properties if node already exists
        query = """
        MERGE (p:Paper {paper_id: $paper_id})
        ON CREATE SET
            p.title = $title,
            p.authors = $authors,
            p.year = $year,
            p.abstract = $abstract,
            p.citation_count = $citation_count,
            p.url = $url,
            p.venue = $venue,
            p.fields_of_study = $fields_of_study
        ON MATCH SET
            p.title = $title,
            p.citation_count = $citation_count,
            p.abstract = COALESCE($abstract, p.abstract)
        """
        async with self._driver.session() as session:
            await session.run(
                query,
                paper_id=paper.paper_id,
                title=paper.title,
                authors=paper.authors,
                year=paper.year,
                abstract=paper.abstract,
                citation_count=paper.citation_count,
                url=paper.url,
                venue=paper.venue,
                fields_of_study=paper.fields_of_study,
            )

    async def create_citation_edge(self, edge: CitationEdge) -> None:
        """
        Create a semantic citation relationship between two papers.
        
        This creates a directed edge:
            (source_paper) --[CITES {type, context}]--> (target_paper)
        
        Both paper nodes must exist before calling this.
        Uses MERGE to prevent duplicate edges between the same papers.
        
        Args:
            edge: CitationEdge dataclass with relationship metadata
        """
        # Cypher query explanation:
        # MATCH both source and target papers first
        # MERGE the CITES relationship between them (prevents duplicates)
        # SET the semantic properties on the edge
        query = """
        MATCH (source:Paper {paper_id: $source_id})
        MATCH (target:Paper {paper_id: $target_id})
        MERGE (source)-[r:CITES]->(target)
        SET r.relationship_type = $rel_type,
            r.context_text = $context,
            r.confidence = $confidence,
            r.is_influential = $is_influential
        """
        async with self._driver.session() as session:
            await session.run(
                query,
                source_id=edge.source_paper_id,
                target_id=edge.target_paper_id,
                rel_type=edge.relationship_type.value,
                context=edge.context_text,
                confidence=edge.confidence,
                is_influential=edge.is_influential,
            )

    # =================================================================
    # READ OPERATIONS — Querying the Graph
    # =================================================================

    async def get_graph_for_topic(self, topic: str) -> dict:
        """
        Retrieve the full citation graph related to a search topic.
        
        Returns all papers and their citation relationships that were
        discovered during an agent crawl for the given topic.
        
        This is the primary query used by the frontend to render
        the interactive visualization.
        
        Args:
            topic: The search topic used to discover these papers
            
        Returns:
            Dictionary with 'nodes' (papers) and 'edges' (citations)
            formatted for direct use by Cytoscape.js on the frontend
        """
        # Query: Find all Paper nodes and their CITES relationships
        # Returns both node properties and edge properties
        query = """
        MATCH (p:Paper)
        OPTIONAL MATCH (p)-[r:CITES]->(cited:Paper)
        RETURN p, r, cited
        """
        nodes = {}   # paper_id -> paper properties (deduplicated)
        edges = []   # list of citation relationships

        async with self._driver.session() as session:
            result = await session.run(query)
            async for record in result:
                # --- Process Paper Nodes ---
                paper = record["p"]
                paper_id = paper["paper_id"]
                if paper_id not in nodes:
                    nodes[paper_id] = {
                        "paper_id": paper_id,
                        "title": paper.get("title", ""),
                        "authors": paper.get("authors", []),
                        "year": paper.get("year"),
                        "abstract": paper.get("abstract"),
                        "citation_count": paper.get("citation_count", 0),
                        "url": paper.get("url"),
                        "venue": paper.get("venue"),
                        "fields_of_study": paper.get("fields_of_study", []),
                    }

                # --- Process Citation Edges ---
                rel = record["r"]
                cited = record["cited"]
                if rel and cited:
                    cited_id = cited["paper_id"]
                    # Also add the cited paper to nodes if not already there
                    if cited_id not in nodes:
                        nodes[cited_id] = {
                            "paper_id": cited_id,
                            "title": cited.get("title", ""),
                            "authors": cited.get("authors", []),
                            "year": cited.get("year"),
                            "abstract": cited.get("abstract"),
                            "citation_count": cited.get("citation_count", 0),
                            "url": cited.get("url"),
                            "venue": cited.get("venue"),
                            "fields_of_study": cited.get("fields_of_study", []),
                        }
                    edges.append({
                        "source": paper_id,
                        "target": cited_id,
                        "relationship_type": rel.get("relationship_type", "background"),
                        "context_text": rel.get("context_text"),
                        "confidence": rel.get("confidence", 0.0),
                        "is_influential": rel.get("is_influential", False),
                    })

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
        }

    async def get_paper_by_id(self, paper_id: str) -> Optional[dict]:
        """
        Retrieve a single paper's full details and its relationships.
        
        Used when a user clicks on a node in the graph to see
        the paper's metadata and all its citation connections.
        
        Args:
            paper_id: Semantic Scholar paper ID
            
        Returns:
            Paper details with lists of incoming/outgoing citations,
            or None if the paper is not in our graph
        """
        query = """
        MATCH (p:Paper {paper_id: $paper_id})
        OPTIONAL MATCH (p)-[out_r:CITES]->(out_paper:Paper)
        OPTIONAL MATCH (in_paper:Paper)-[in_r:CITES]->(p)
        RETURN p,
               collect(DISTINCT {rel: out_r, paper: out_paper}) as outgoing,
               collect(DISTINCT {rel: in_r, paper: in_paper}) as incoming
        """
        async with self._driver.session() as session:
            result = await session.run(query, paper_id=paper_id)
            record = await result.single()

            if not record:
                return None

            paper = record["p"]
            
            # Build lists of outgoing citations (papers this one cites)
            outgoing_citations = []
            for item in record["outgoing"]:
                if item["rel"] and item["paper"]:
                    outgoing_citations.append({
                        "paper_id": item["paper"]["paper_id"],
                        "title": item["paper"].get("title", ""),
                        "relationship_type": item["rel"].get("relationship_type", "background"),
                        "context_text": item["rel"].get("context_text"),
                    })

            # Build lists of incoming citations (papers that cite this one)
            incoming_citations = []
            for item in record["incoming"]:
                if item["rel"] and item["paper"]:
                    incoming_citations.append({
                        "paper_id": item["paper"]["paper_id"],
                        "title": item["paper"].get("title", ""),
                        "relationship_type": item["rel"].get("relationship_type", "background"),
                        "context_text": item["rel"].get("context_text"),
                    })

            return {
                "paper_id": paper["paper_id"],
                "title": paper.get("title", ""),
                "authors": paper.get("authors", []),
                "year": paper.get("year"),
                "abstract": paper.get("abstract"),
                "citation_count": paper.get("citation_count", 0),
                "url": paper.get("url"),
                "venue": paper.get("venue"),
                "fields_of_study": paper.get("fields_of_study", []),
                "outgoing_citations": outgoing_citations,
                "incoming_citations": incoming_citations,
            }

    async def get_graph_stats(self) -> dict:
        """
        Get summary statistics about the current knowledge graph.
        
        Useful for the dashboard to show metrics like total papers,
        total relationships, and most cited papers.
        
        Returns:
            Dictionary with graph statistics
        """
        query = """
        MATCH (p:Paper)
        OPTIONAL MATCH ()-[r:CITES]->()
        RETURN count(DISTINCT p) as paper_count,
               count(DISTINCT r) as edge_count
        """
        async with self._driver.session() as session:
            result = await session.run(query)
            record = await result.single()
            return {
                "total_papers": record["paper_count"],
                "total_citations": record["edge_count"],
            }

    # =================================================================
    # MAINTENANCE OPERATIONS
    # =================================================================

    async def clear_database(self) -> None:
        """
        Delete ALL nodes and relationships from the database.
        
        WARNING: This is destructive! Only use for testing or resetting.
        """
        query = "MATCH (n) DETACH DELETE n"
        async with self._driver.session() as session:
            await session.run(query)
