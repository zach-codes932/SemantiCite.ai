"""
============================================================
SemantiCite.ai — Citation Context Extractor
============================================================
PURPOSE:
    Extracts and normalizes citation windows (the sentences 
    surrounding a reference) from Semantic Scholar data.

ARCHITECTURE ROLE:
    Agent Tool Layer — Simplifies the raw context string provided
    by the API before it gets sent to the LLM.
============================================================
"""

from db.models import CitationContext


class CitationContextExtractor:
    """
    Cleans and processes raw citation contexts.
    
    While Semantic Scholar provides a 'contexts' array, the text
    is often messy, containing XML tags or being excessively long.
    This tool ensures the LLM receives clean, focused text.
    """

    @staticmethod
    def clean_context(context: CitationContext) -> str:
        """
        Clean the raw citation text.
        
        Args:
            context: Raw CitationContext model from the API
            
        Returns:
            Cleaned string ready for the LLM prompt.
        """
        text = context.context_text
        
        # 1. Remove common XML/HTML tags (sometimes present in raw text)
        text = text.replace("<cite>", "").replace("</cite>", "")
        text = text.replace("<b>", "").replace("</b>", "")
        text = text.replace("<i>", "").replace("</i>", "")
        
        # 2. Normalize whitespace
        text = " ".join(text.split())
        
        # 3. Truncate if excessively long (LLMs classify short windows better)
        # We limit to roughly 2-3 sentences.
        if len(text) > 800:
            text = text[:800] + "..."
            
        return text

    @staticmethod
    def get_best_context(contexts: list[CitationContext]) -> str | None:
        """
        Given multiple occurrences of a citation in a paper, 
        pick the one most likely to have strong semantic meaning.
        
        Args:
            contexts: List of occurrences where Paper A cites Paper B
            
        Returns:
            The single best context text, or None if empty.
        """
        if not contexts:
            return None

        # Sort contexts: Prioritize those with Semantic Scholar 'intents' attached
        # If it has a method/result intent attached, it's usually the most substantive mention
        sorted_contexts = sorted(
            contexts, 
            key=lambda c: len(c.intents) if c.intents else 0, 
            reverse=True
        )

        return CitationContextExtractor.clean_context(sorted_contexts[0])
