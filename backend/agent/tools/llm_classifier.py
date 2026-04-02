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
from langchain_google_genai import ChatGoogleGenerativeAI
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
        # Initialize the Gemini model via LangChain
        # We enforce JSON output using response_format if supported,
        # but Gemini handles JSON well when prompted.
        self.llm = ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL_NAME,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=0.1,  # Low temperature for consistent classification
            max_output_tokens=150, # We only need a short JSON response
        )

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
        if not settings.GOOGLE_API_KEY:
            # Fallback if no LLM key is provided: just return "background"
            print("  [WARN] No Google API Key. Defaulting classification to 'background'")
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

        try:
            # Combine system and user prompts
            messages = [
                ("system", CITATION_CLASSIFIER_SYSTEM_PROMPT),
                ("user", user_prompt)
            ]
            
            # Call Gemini
            response = await self.llm.ainvoke(messages)
            
            # Extract JSON from the markdown codeblocks Gemini usually returns
            response_text = response.content.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            elif response_text.startswith("```"):
                response_text = response_text[3:-3].strip()
                
            data = json.loads(response_text)
            
            # Validate output matches our schema
            result = ClassificationResult(**data)
            
            return {
                "relationship_type": result.relationship_type,
                "confidence": result.confidence,
                "reasoning": result.reasoning
            }

        except Exception as e:
            print(f"  [ERROR] Classification failed: {e}")
            # Safe fallback if LLM hallucinates or quota exceeded
            return {
                "relationship_type": RelationshipType.BACKGROUND,
                "confidence": 0.0,
                "reasoning": "Fallback due to LLM error"
            }
