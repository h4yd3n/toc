import os
import uuid
import json
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field
from anthropic import Anthropic

from shared.models import (
    Assessment,
    AssessmentStatus,
    DimensionScore,
    Evidence,
    Trip,
    AnalyticConfidence
)
from shared.constants import ICD203_TERMS

class DraftedAssessment(BaseModel):
    assessment: Assessment
    bluf: str
    key_judgments: List[str]
    framework_sections: dict
    mitigations_and_residual_risk: str
    collection_gaps_statement: str

class AssessmentDrafter:
    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def draft_assessment(
        self,
        trip: Trip,
        dimension_scores: List[DimensionScore],
        evidence: List[Evidence],
        inherent_score: float,
        residual_score: float,
        band: str,
        recommendation: str,
        collection_gaps: List[str],
        framework: str = 'mett-tc'
    ) -> DraftedAssessment:
        
        assessment = Assessment(
            assessment_id=str(uuid.uuid4()),
            subject_type="trip",
            subject_id=trip.trip_id,
            framework=framework,
            dimension_scores=dimension_scores,
            inherent_score=inherent_score,
            residual_score=residual_score,
            analytic_confidence=AnalyticConfidence.MODERATE,
            status=AssessmentStatus.DRAFT,
            author="ai",
            collection_gaps=collection_gaps
        )
        
        if self.client:
            return self._draft_with_claude(assessment, trip, evidence, band, recommendation)
        else:
            return self._draft_with_heuristics(assessment, trip, evidence, band, recommendation)
            
    def _draft_with_claude(self, assessment: Assessment, trip: Trip, evidence: List[Evidence], band: str, recommendation: str) -> DraftedAssessment:
        icd_terms_str = ", ".join([t[0] for t in ICD203_TERMS])
        prompt = f"""
        Draft an intelligence assessment for the trip {trip.trip_id}.
        Inherent Score: {assessment.inherent_score}, Residual Score: {assessment.residual_score}, Band: {band}
        Recommendation: {recommendation}
        Collection Gaps: {assessment.collection_gaps}
        Evidence count: {len(evidence)}
        Framework: {assessment.framework}
        
        Provide a JSON object with:
        - bluf (string, 1-3 sentences with bottom line score, band, recommendation)
        - key_judgments (list of strings, 3-5 numbered statements using strict ICD 203 terms: {icd_terms_str})
        - framework_sections (object with string keys/values for framework sections, e.g., Mission, Enemy, etc.)
        - mitigations_and_residual_risk (string)
        - collection_gaps_statement (string)
        """
        
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            tools=[{
                "name": "draft_report",
                "description": "Draft an intelligence report",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "bluf": {"type": "string"},
                        "key_judgments": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "framework_sections": {
                            "type": "object",
                            "additionalProperties": {"type": "string"}
                        },
                        "mitigations_and_residual_risk": {"type": "string"},
                        "collection_gaps_statement": {"type": "string"}
                    },
                    "required": ["bluf", "key_judgments", "framework_sections", "mitigations_and_residual_risk", "collection_gaps_statement"]
                }
            }],
            tool_choice={"type": "tool", "name": "draft_report"},
            messages=[{"role": "user", "content": prompt}]
        )
        
        for content in response.content:
            if content.type == "tool_use" and content.name == "draft_report":
                data = content.input
                return DraftedAssessment(
                    assessment=assessment,
                    bluf=data.get("bluf", ""),
                    key_judgments=data.get("key_judgments", []),
                    framework_sections=data.get("framework_sections", {}),
                    mitigations_and_residual_risk=data.get("mitigations_and_residual_risk", ""),
                    collection_gaps_statement=data.get("collection_gaps_statement", "")
                )
        
        return self._draft_with_heuristics(assessment, trip, evidence, band, recommendation)

    def _draft_with_heuristics(self, assessment: Assessment, trip: Trip, evidence: List[Evidence], band: str, recommendation: str) -> DraftedAssessment:
        return DraftedAssessment(
            assessment=assessment,
            bluf=f"BLUF: The trip is assessed at {assessment.residual_score} (Band: {band}). Recommendation: {recommendation}.",
            key_judgments=[
                "1. We assess it is likely that risks are moderate.",
                "2. It is highly unlikely that major disruptions will occur."
            ],
            framework_sections={
                "Mission": f"Trip purpose: {trip.purpose}",
                "Enemy": "No specific threats identified.",
                "Terrain": "Standard urban environment.",
                "Troops": "Standard security posture.",
                "Time": "Short duration.",
                "Civil Considerations": "Normal patterns of life."
            },
            mitigations_and_residual_risk="Standard mitigations apply. Residual risk is manageable.",
            collection_gaps_statement=f"We have identified the following collection gaps: {', '.join(assessment.collection_gaps)}."
        )
