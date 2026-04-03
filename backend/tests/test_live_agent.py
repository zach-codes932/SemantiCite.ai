"""
============================================================
SemantiCite.ai — Live Agent Flow Test
============================================================
Tests the LangGraph agent against the live endpoints:
- Semantic Scholar (Search & Citations)
- Google Gemini Flash (Classification)
- Neo4j AuraDB (Graph Save)
============================================================
"""

import asyncio
import sys
import os

# Set up path so we can import backend packages
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.orchestrator import agent_graph
from db.neo4j_client import Neo4jClient
from config import settings

async def main():
    print(f"\n============================================================")
    print(f"  TESTING LIVE AGENT PIPELINE")
    print(f"============================================================")
    print(f"  - Mock Data Mode: {settings.USE_MOCK_API}")
    print(f"  - Semantic Scholar Key: {'Yes' if settings.SEMANTIC_SCHOLAR_API_KEY else 'No'}")
    print(f"  - Google Gemini Key:    {'Yes' if settings.GOOGLE_API_KEY else 'No'}")
    print(f"  - Neo4j Database URI:   {settings.NEO4J_URI}")
    print(f"============================================================\n")

    initial_state = {
        "topic": "transformer attention", # Keep topic narrow for speed
        "max_depth": 1,                   # Depth 1 = Seed papers + 1 layer of citations
        "current_depth": 0,
        "task_id": "test_run_01",
        "papers_to_process": [],
        "processed_paper_ids": set(),
        "total_papers_found": 0,
        "total_edges_created": 0
    }

    try:
        # Run the agent
        print("[*] Starting LangGraph Agent...")
        final_state = await agent_graph.ainvoke(initial_state)

        print("\n============================================================")
        print("  AGENT EXECUTION COMPLETE")
        print("============================================================")
        print(f"  - Total Papers Found: {final_state.get('total_papers_found')}")
        print(f"  - Total Edges Saved:  {final_state.get('total_edges_created')}")
        
        # Verify Neo4j insertion
        print("\n[*] Verifying Neo4j Database contents...")
        async with Neo4jClient() as client:
            # Query just to get a count to ensure DB connection is working
            query = "MATCH (n:Paper) RETURN count(n) as paper_count"
            result = await client.driver.execute_query(query)
            count = result.records[0]["paper_count"]
            print(f"  -> Total Papers currently in AuraDB: {count}")
            
    except Exception as e:
        print(f"\n[!] Pipeline Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
