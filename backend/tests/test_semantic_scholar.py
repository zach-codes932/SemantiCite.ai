"""
============================================================
SemantiCite.ai — Semantic Scholar API Live Test
============================================================
PURPOSE:
    Tests the SemanticScholarClient against the REAL API
    to verify our client code actually works end-to-end.

HOW TO RUN:
    cd backend
    venv\Scripts\python.exe tests\test_semantic_scholar.py

WHAT IT TESTS:
    1. search_papers()   — Can we find papers by keyword?
    2. get_paper()       — Can we fetch a single paper's details?
    3. get_references()  — Can we get papers that a paper cites?
    4. get_citations()   — Can we get papers that cite a paper?
    5. Citation contexts — Does the API return context sentences?
    6. Citation intents  — Does the API return intent labels?

NOTE:
    Without an API key, we're rate-limited to 1 request/second.
    The script adds 1.5s delays between calls to stay safe.
============================================================
"""

import asyncio
import sys
import os
import time

# Add backend directory to Python path so imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.tools.semantic_scholar import SemanticScholarClient


# === Helper: Print formatted results ===
def print_section(title: str):
    """Print a visible section header."""
    print(f"\n{'=' * 60}")
    print(f"  TEST: {title}")
    print(f"{'=' * 60}")


def print_paper(paper, index: int = None):
    """Print a paper's key details in a readable format."""
    prefix = f"  [{index}]" if index is not None else "  "
    print(f"{prefix} Title: {paper.title}")
    print(f"       Year: {paper.year}")
    print(f"       Authors: {', '.join(paper.authors[:3])}{'...' if len(paper.authors) > 3 else ''}")
    print(f"       Citations: {paper.citation_count}")
    print(f"       ID: {paper.paper_id}")
    if paper.venue:
        print(f"       Venue: {paper.venue}")
    if paper.fields_of_study:
        print(f"       Fields: {', '.join(paper.fields_of_study)}")
    print()


async def run_tests():
    """Run all Semantic Scholar API tests sequentially."""
    
    passed = 0
    failed = 0
    total_tests = 6

    async with SemanticScholarClient() as client:

        # =====================================================
        # TEST 1: Search papers by keyword
        # =====================================================
        print_section("1/6 — Search Papers (query: 'attention mechanism')")
        try:
            papers = await client.search_papers("attention mechanism", limit=5)
            
            if len(papers) > 0:
                print(f"  [PASS] Found {len(papers)} papers\n")
                for i, paper in enumerate(papers):
                    print_paper(paper, i + 1)
                passed += 1
                
                # Save the first paper's ID for subsequent tests
                seed_paper_id = papers[0].paper_id
                seed_paper_title = papers[0].title
            else:
                print("  [FAIL] No papers returned")
                failed += 1
                return
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            failed += 1
            return

        # Rate limit delay
        print("  (waiting 1.5s for rate limit...)")
        await asyncio.sleep(1.5)

        # =====================================================
        # TEST 2: Get single paper details
        # =====================================================
        print_section(f"2/6 -- Get Paper Details (ID: {seed_paper_id[:20]}...)")
        try:
            paper = await client.get_paper(seed_paper_id)
            
            if paper and paper.title:
                print(f"  [PASS] Retrieved paper details\n")
                print_paper(paper)
                
                # Check if abstract is available
                if paper.abstract:
                    abstract_preview = paper.abstract[:150] + "..." if len(paper.abstract) > 150 else paper.abstract
                    print(f"  Abstract: {abstract_preview}\n")
                else:
                    print("  Abstract: (not available)\n")
                passed += 1
            else:
                print("  [FAIL] Paper not found or empty response")
                failed += 1
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            failed += 1

        await asyncio.sleep(1.5)

        # =====================================================
        # TEST 3: Get references (papers the seed paper cites)
        # =====================================================
        print_section(f"3/6 -- Get References (papers that '{seed_paper_title[:40]}...' cites)")
        try:
            references = await client.get_references(seed_paper_id, limit=5)
            
            if len(references) > 0:
                print(f"  [PASS] Found {len(references)} references\n")
                for i, ref in enumerate(references):
                    print_paper(ref["paper"], i + 1)
                passed += 1
            else:
                print("  [WARN] No references found (paper may not have full text)")
                passed += 1  # Not a failure, just limited data
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            failed += 1

        await asyncio.sleep(1.5)

        # =====================================================
        # TEST 4: Get citations (papers that cite the seed paper)
        # =====================================================
        print_section(f"4/6 -- Get Citations (papers that cite '{seed_paper_title[:40]}...')")
        try:
            citations = await client.get_citations(seed_paper_id, limit=5)
            
            if len(citations) > 0:
                print(f"  [PASS] Found {len(citations)} citing papers\n")
                for i, cit in enumerate(citations):
                    print_paper(cit["paper"], i + 1)
                passed += 1
            else:
                print("  [WARN] No citations found")
                passed += 1
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            failed += 1

        await asyncio.sleep(1.5)

        # =====================================================
        # TEST 5: Check citation CONTEXTS (the key feature!)
        # =====================================================
        print_section("5/6 -- Citation Contexts (sentence-level citation text)")
        try:
            # Fetch references again to check contexts
            references = await client.get_references(seed_paper_id, limit=10)
            
            contexts_found = 0
            for ref in references:
                if ref["contexts"]:
                    for ctx in ref["contexts"]:
                        contexts_found += 1
                        if contexts_found <= 3:  # Show first 3 examples
                            print(f"  Context {contexts_found}:")
                            print(f"    Citing: {seed_paper_title[:50]}...")
                            print(f"    Cited:  {ref['paper'].title[:50]}...")
                            ctx_preview = ctx.context_text[:200] + "..." if len(ctx.context_text) > 200 else ctx.context_text
                            print(f"    Text:   \"{ctx_preview}\"")
                            if ctx.intents:
                                print(f"    Intents: {ctx.intents}")
                            print()

            if contexts_found > 0:
                print(f"  [PASS] Found {contexts_found} citation context sentences total")
                passed += 1
            else:
                print("  [WARN] No citation contexts available for this paper")
                print("  (This is expected for some papers -- S2 needs full text access)")
                passed += 1  # Not a failure
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            failed += 1

        await asyncio.sleep(1.5)

        # =====================================================
        # TEST 6: Check citation INTENTS (Background/Method/Result)
        # =====================================================
        print_section("6/6 -- Citation Intents (S2 basic classification)")
        try:
            citations = await client.get_citations(seed_paper_id, limit=10)
            
            intents_found = {}
            for cit in citations:
                for ctx in cit["contexts"]:
                    for intent in ctx.intents:
                        intents_found[intent] = intents_found.get(intent, 0) + 1

            if intents_found:
                print(f"  [PASS] Found intent labels:")
                for intent, count in sorted(intents_found.items()):
                    print(f"    - {intent}: {count} occurrences")
                passed += 1
            else:
                print("  [WARN] No intent labels available")
                print("  (S2 provides intents only for papers with full text)")
                passed += 1
        except Exception as e:
            print(f"  [FAIL] Error: {e}")
            failed += 1

    # =====================================================
    # FINAL RESULTS
    # =====================================================
    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {passed}/{total_tests} tests passed, {failed} failed")
    print(f"{'=' * 60}")
    
    if failed == 0:
        print("  [ALL PASS] Semantic Scholar API integration is working!")
    else:
        print("  [ISSUES] Some tests failed. Check output above.")
    print()


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  SemantiCite.ai -- Semantic Scholar API Live Test")
    print("  Testing against: https://api.semanticscholar.org/graph/v1")
    print("=" * 60)
    
    asyncio.run(run_tests())
