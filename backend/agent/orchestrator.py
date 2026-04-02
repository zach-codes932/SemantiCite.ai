"""
============================================================
SemantiCite.ai — Agent Orchestrator (LangGraph)
============================================================
PURPOSE:
    Defines the state machine that controls the AI agent's
    workflow. This is the "manager" that coordinates all the
    different tools to achieve the goal of building the graph.

ARCHITECTURE ROLE:
    Agent Layer — Uses LangGraph to orchestrate:
    1. Search papers (SemanticScholarClient)
    2. Fetch citations (SemanticScholarClient)
    3. Extract context (CitationContextExtractor)
    4. Classify (LLMClassifier)
    5. Save to database (GraphWriter)
    
GRAPH WORKFLOW:
    [START] → Search Top Papers → For Each Paper: 
                → Fetch Citations 
                → Extract & Classify 
                → Save to Graph 
                → [END] (if max depth reached)
============================================================
"""

from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END

from config import settings
from db.models import PaperNode
from agent.tools.semantic_scholar import SemanticScholarClient
from agent.tools.citation_extractor import CitationContextExtractor
from agent.tools.llm_classifier import LLMClassifier
from agent.tools.graph_writer import GraphWriter

# =================================================================
# AGENT STATE
# =================================================================
# This dictionary represents the "memory" of the agent during a run.
# It gets passed from step to step.

class AgentState(TypedDict):
    topic: str                 # The original search query
    max_depth: int             # How deep to crawl
    current_depth: int         # Current crawl depth
    task_id: str               # ID to report status back to the API
    
    # Tracking progress
    papers_to_process: List[PaperNode] # Papers waiting to have their citations fetched
    processed_paper_ids: set   # Papers we've already fetched (prevents infinite loops)
    
    # Final stats
    total_papers_found: int
    total_edges_created: int


# =================================================================
# AGENT NODES (Steps in the workflow)
# =================================================================

async def search_seed_papers(state: AgentState) -> dict:
    """Find the initial prominent papers for the topic."""
    
    # In a real system, we'd update the API status here using a callback.
    # For now, we update the internal state numbers.
    print(f"\n[Agent] Searching for '{state['topic']}'...")
    
    async with SemanticScholarClient() as client:
        papers = await client.search_papers(state["topic"])
        
    writer = GraphWriter()
    
    # Save seed papers to the graph immediately
    for p in papers:
        await writer.save_paper(p)
        
    print(f"[Agent] Found {len(papers)} seed papers.")
        
    return {
        "papers_to_process": papers,
        "total_papers_found": len(papers),
        "total_edges_created": 0,
        "processed_paper_ids": set()
    }


async def process_citations(state: AgentState) -> dict:
    """
    For each paper in the queue, fetch its citations, classify them,
    and save them to the graph.
    """
    papers = state["papers_to_process"]
    processed = state["processed_paper_ids"]
    current_depth = state["current_depth"]
    
    print(f"\n[Agent] Processing depth {current_depth}. Papers in queue: {len(papers)}")
    
    next_layer_papers = []
    new_paper_count = 0
    new_edge_count = 0
    
    # Initialize our tools
    classifier = LLMClassifier()
    writer = GraphWriter()
    
    async with SemanticScholarClient() as client:
        # We only process a few to avoid taking too long in a demo
        for paper in papers[:settings.MAX_SEED_PAPERS]:
            if paper.paper_id in processed:
                continue
                
            processed.add(paper.paper_id)
            print(f"  -> Fetching citations for: {paper.title[:40]}...")
            
            # Fetch incoming citations
            citations_data = await client.get_citations(paper.paper_id)
            
            for cit in citations_data:
                citing_paper = cit["paper"]
                contexts = cit["contexts"]
                is_influential = cit["is_influential"]
                
                # We save the citing paper to the graph
                await writer.save_paper(citing_paper)
                new_paper_count += 1
                
                # Pick the best context sentence
                best_context = CitationContextExtractor.get_best_context(contexts)
                
                if best_context:
                    # Classify the relationship
                    classification = await classifier.classify_citation(
                        citing_title=citing_paper.title,
                        cited_title=paper.title,
                        context_text=best_context
                    )
                    
                    # Store the actual sentence as reasoning so it displays in the UI
                    classification["reasoning"] = best_context
                else:
                    # Default if no text available
                    classification = {
                        "relationship_type": "background",
                        "confidence": 0.0,
                        "reasoning": "No citation context available"
                    }
                
                # Save the edge: citing_paper -> this_paper
                await writer.save_citation(
                    source_id=citing_paper.paper_id,
                    target_id=paper.paper_id,
                    classification=classification,
                    is_influential=is_influential
                )
                new_edge_count += 1
                
                # Add to queue for the next depth layer
                next_layer_papers.append(citing_paper)
                
    return {
        "papers_to_process": next_layer_papers,
        "processed_paper_ids": processed,
        "current_depth": current_depth + 1,
        "total_papers_found": state["total_papers_found"] + new_paper_count,
        "total_edges_created": state["total_edges_created"] + new_edge_count
    }


def should_continue(state: AgentState) -> str:
    """Conditional routing edge: do we go deeper or stop?"""
    if state["current_depth"] >= state["max_depth"] or not state["papers_to_process"]:
        print(f"\n[Agent] Max depth reached or no more papers. Stopping.")
        return "stop"
    return "continue"


# =================================================================
# BUILD THE GRAPH
# =================================================================

def build_agent_graph():
    """Compiles the LangGraph state machine."""
    workflow = StateGraph(AgentState)
    
    # Add our nodes (functions)
    workflow.add_node("search", search_seed_papers)
    workflow.add_node("process", process_citations)
    
    # Define the flow
    workflow.add_edge(START, "search")
    workflow.add_edge("search", "process")
    
    # Conditional logic
    workflow.add_conditional_edges(
        "process",
        should_continue,
        {
            "continue": "process",  # Loop back
            "stop": END             # Finish
        }
    )
    
    return workflow.compile()

# The compiled graph ready to be invoked
agent_graph = build_agent_graph()
