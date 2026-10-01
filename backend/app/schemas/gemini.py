"""Strict structured output schema for Gemini observations."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class GeminiObservation(BaseModel):
    category: Literal["visual", "temporal", "audio", "text", "other"] = "other"
    timestamp: Optional[float] = None
    observation: str = Field(min_length=1, max_length=1000)
    strength: Literal["weak", "moderate", "strong"] = "weak"
    uncertainty: Literal["low", "medium", "high"] = "medium"
    signal: Literal["concern", "consistent", "neutral"] = "neutral"


class GeminiObservations(BaseModel):
    observations: List[GeminiObservation] = Field(default_factory=list, max_length=30)
    limitations: List[str] = Field(default_factory=list, max_length=20)
