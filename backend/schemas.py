from typing import List, Optional

from pydantic import BaseModel, Field


class ChordSegment(BaseModel):
    start: float = Field(ge=0)
    end: float = Field(ge=0)
    chord: str
    confidence: float = Field(ge=0, le=1)


class AnalysisResponse(BaseModel):
    filename: str
    duration: float
    analysis_mode: str
    chord_range: str
    chords: List[ChordSegment]
    warning: Optional[str] = None
