from typing import Optional
from pydantic import BaseModel, Field
from shared.models import SeverityTier


class ClassificationResult(BaseModel):
    severity: SeverityTier
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    model_version: str = "claude-3-5-sonnet"
    latency_ms: Optional[float] = None
