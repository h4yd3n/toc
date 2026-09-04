from typing import Optional
from pydantic import BaseModel, Field
from shared.models import SeverityTier


class ClassificationResult(BaseModel):
    severity: SeverityTier
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    model_version: str = "unknown"  # the model that actually answered — recorded on the ledger
    latency_ms: Optional[float] = None
    failed: bool = False  # classifier could not classify (parse failure, refusal, transport). Router fails closed on this.
