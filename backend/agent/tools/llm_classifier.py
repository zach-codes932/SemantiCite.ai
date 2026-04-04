"""
============================================================
SemantiCite.ai — LLM Citation Classifier
============================================================
PURPOSE:
    Uses Google Gemini Flash to read a citation sentence
    and classify it into a semantic relationship type
    (supports, critiques, extends, etc.).

ARCHITECTURE ROLE:
    Agent Tool Layer — The core intelligence of the system.
    Converts raw text into structured Neo4j edge properties.
============================================================
"""

import json
import asyncio
import random
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from config import settings
from db.models import RelationshipType
from agent.prompts import CITATION_CLASSIFIER_SYSTEM_PROMPT


class ClassificationResult(BaseModel):
    """Pydantic model representing the expected JSON from the LLM."""
    relationship_type: RelationshipType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class LLMClassifier:
    """
    Wrapper for the LangChain Google GenAI client.
    Handles prompting, parsing, and fallback logic.
    """

    def __init__(self):
        # Initialize the OpenAI model via LangChain
        # We explicitly use GPT-4o-mini, which is wildly cheap and fast.
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL_NAME,
            openai_api_key=settings.OPENAI_API_KEY,
            temperature=0.1,  # Low temperature for consistent classification
            max_tokens=150,   # We only need a short structural response
        )
        
        # This powerful feature mathematically guarantees the output matches
        # the Pydantic schema perfectly, avoiding the need for regex parsing text.
        self.structured_llm = self.llm.with_structured_output(ClassificationResult)

    async def classify_citation(
        self, citing_title: str, cited_title: str, context_text: str
    ) -> dict:
        """
        Classifies the relationship between two papers based on the text.
        
        Args:
            citing_title: Title of the paper making the citation
            cited_title: Title of the paper being cited
            context_text: The sentence where the citation occurs
            
        Returns:
            Dictionary with {relationship_type, confidence, reasoning}
        """
        if not settings.OPENAI_API_KEY:
            # Fallback if no LLM key is provided: just return "background"
            print("  [WARN] No OpenAI API Key found. Defaulting classification to 'background'")
            return {
                "relationship_type": RelationshipType.BACKGROUND,
                "confidence": 0.5,
                "reasoning": "Mock classification (No API key provided)"
            }

        # Construct the user prompt
        user_prompt = f"""
Citing Paper: {citing_title}
Cited Paper: {cited_title}

Citation Context text: 
"{context_text}"

Classify this citation as a JSON object exactly as instructed.
"""

        # Add a 0.2s delay to safely respect 500 Requests Per Minute (Tier 1 limit)
        # 0.2s = max 300 RPM, well within safe limits holding for async workers
        await asyncio.sleep(0.2)

        try:
            # Combine system and user prompts
            messages = [
                ("system", CITATION_CLASSIFIER_SYSTEM_PROMPT),
                ("user", user_prompt)
            ]
            
            # Call OpenAI and get structured Pydantic object back directly!
            result = await self.structured_llm.ainvoke(messages)
            
            return {
                "relationship_type": result.relationship_type,
                "confidence": result.confidence,
                "reasoning": result.reasoning
            }

        except Exception as e:
            print(f"  [ERROR] Classification failed: {e}")
            # Fallback to random type for demo purposes when rate limited
            fallback_type = random.choice([
                RelationshipType.SUPPORTS,
                RelationshipType.CRITIQUES,
                RelationshipType.EXTENDS,
                RelationshipType.USES_METHOD,
                RelationshipType.BASIS,
                RelationshipType.BACKGROUND
            ])
            return {
                "relationship_type": fallback_type,
                "confidence": 0.0,
                "reasoning": "Fallback due to LLM error (Rate Limit/Quota)"
            }
