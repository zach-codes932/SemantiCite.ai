"""
============================================================
SemantiCite.ai — Data Models
============================================================
PURPOSE:
    Defines the core data structures used throughout the application.
    These models represent the "vocabulary" of our domain:
    - Papers (nodes in the knowledge graph)
    - Citation Relationships (edges in the knowledge graph)

ARCHITECTURE ROLE:
    Data Layer — These models are used by:
    - The Semantic Scholar tool (to structure API responses)
    - The Neo4j client (to read/write graph data)
    - The API schemas (to serialize data for the frontend)
    - The LLM classifier (to structure classification results)

KNOWLEDGE GRAPH STRUCTURE:
    ┌──────────┐   SUPPORTS    ┌──────────┐
    │ Paper A  │──────────────>│ Paper B  │
    │  (Node)  │   (Edge)      │  (Node)  │
    └──────────┘               └──────────┘
============================================================
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


# === Relationship Types ===
# These are the semantic labels we assign to citation edges.
# The LLM classifier categorizes each citation into one of these types.
# This goes BEYOND Semantic Scholar's basic intents (Background, Method, Result)
# by adding richer academic relationship semantics.

class RelationshipType(str, Enum):
    """
    Semantic classification of how Paper A relates to Paper B when citing it.
    
    Examples of each type:
    - SUPPORTS:    "Our findings confirm the results reported by [B]..."
    - CRITIQUES:   "However, [B] fails to account for..."
    - EXTENDS:     "Building upon the framework proposed by [B], we..."
    - USES_METHOD: "Following the approach described in [B], we applied..."
    - BASIS:       "This work is grounded in the seminal theory of [B]..."
    - BACKGROUND:  "[B] provides a comprehensive overview of the field..."
    """
    SUPPORTS = "supports"
    CRITIQUES = "critiques"
    EXTENDS = "extends"
    USES_METHOD = "uses_method"
    BASIS = "basis"
    BACKGROUND = "background"


# === Paper Node Model ===
# Represents a single research paper in our knowledge graph.
# Each paper becomes a NODE in Neo4j.

@dataclass
class PaperNode:
    """
    A research paper node in the knowledge graph.
    
    This is the primary entity we store. Each paper is uniquely
    identified by its Semantic Scholar paper_id.
    
    Attributes:
        paper_id:        Unique identifier from Semantic Scholar
        title:           Full title of the paper
        authors:         List of author names (e.g., ["Vaswani, A.", "Shazeer, N."])
        year:            Publication year (e.g., 2017)
        abstract:        Paper abstract text (may be None if unavailable)
        citation_count:  Total number of times this paper has been cited
        url:             Link to the paper on Semantic Scholar
        venue:           Publication venue/journal (e.g., "NeurIPS", "Nature")
        fields_of_study: Research domains (e.g., ["Computer Science", "AI"])
    """
    paper_id: str
    title: str
    authors: list[str] = field(default_factory=list)
    year: Optional[int] = None
    abstract: Optional[str] = None
    citation_count: int = 0
    url: Optional[str] = None
    venue: Optional[str] = None
    fields_of_study: list[str] = field(default_factory=list)


# === Citation Edge Model ===
# Represents a semantic relationship between two papers.
# Each citation becomes a DIRECTED EDGE in Neo4j: source --[type]--> target

@dataclass
class CitationEdge:
    """
    A semantic citation relationship (edge) in the knowledge graph.
    
    Direction: source_paper_id ---[relationship_type]---> target_paper_id
    Meaning:   "The source paper cites the target paper with this intent"
    
    Example:
        source = "Attention Is All You Need" (Vaswani et al.)
        target = "Sequence to Sequence Learning" (Sutskever et al.)
        type   = EXTENDS
        context = "Building upon the encoder-decoder framework of [Sutskever et al.]..."
    
    Attributes:
        source_paper_id:   The paper that CONTAINS the citation (the citer)
        target_paper_id:   The paper being CITED (the citee)
        relationship_type: Semantic classification of the citation 
        context_text:      The 1-2 sentences surrounding the citation
        confidence:        LLM's confidence in the classification (0.0 to 1.0)
        is_influential:    Whether Semantic Scholar flags this as influential
    """
    source_paper_id: str
    target_paper_id: str
    relationship_type: RelationshipType
    context_text: Optional[str] = None
    confidence: float = 0.0
    is_influential: bool = False


# === Citation Context Model ===
# Intermediate structure used during the extraction phase,
# before the LLM classifies the relationship type.

@dataclass
class CitationContext:
    """
    Raw citation context extracted from a paper, BEFORE classification.
    
    This is the input to the LLM classifier. The agent extracts these
    from Semantic Scholar's 'contexts' field, then sends them to the
    LLM to determine the relationship type.
    
    Attributes:
        citing_paper_id: The paper that contains the citation
        cited_paper_id:  The paper being referenced
        context_text:    The sentence(s) where the citation appears
        intents:         Semantic Scholar's basic intent labels (if available)
    """
    citing_paper_id: str
    cited_paper_id: str
    context_text: str
    intents: list[str] = field(default_factory=list)
