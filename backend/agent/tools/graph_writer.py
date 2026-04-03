"""
============================================================
SemantiCite.ai — Graph Writer Tool
============================================================
PURPOSE:
    Provides a high-level tool for the agent to save its
    discoveries directly into the Neo4j Knowledge Graph.

ARCHITECTURE ROLE:
    Agent Tool Layer — Wraps the low-level Neo4j client.
============================================================
"""

from db.neo4j_client import Neo4jClient
from db.models import PaperNode, CitationEdge, RelationshipType


class GraphWriter:
    """
    Takes classified papers and relationships and writes them
    to Neo4j, abstracting away the connection management.
    """

    def __init__(self):
        # We reuse the same singleton connection logic
        pass

    async def save_paper(self, paper: PaperNode):
        """Save a single paper node to the graph."""
        async with Neo4jClient() as client:
            await client.create_paper(paper)

    async def save_citation(
        self, 
        source_id: str, 
        target_id: str, 
        classification: dict,
        is_influential: bool = False
    ):
        """
        Save a semantic edge between two papers.
        """
        raw_rt = classification.get("relationship_type", RelationshipType.BACKGROUND)
        if isinstance(raw_rt, str):
            try:
                rt_enum = RelationshipType(raw_rt.lower())
            except ValueError:
                rt_enum = RelationshipType.BACKGROUND
        else:
            rt_enum = raw_rt

        edge = CitationEdge(
            source_paper_id=source_id,
            target_paper_id=target_id,
            relationship_type=rt_enum,
            context_text=classification.get("reasoning", ""), 
            confidence=classification.get("confidence", 0.0),
            is_influential=is_influential
        )
        
        async with Neo4jClient() as client:
            await client.create_citation_edge(edge)
