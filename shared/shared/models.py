from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class VisibilityState(str, Enum):
    VISIBLE = "visible"          # Fully public / recommended in feed
    LIMITED = "limited"          # Downranked / excluded from recommendation algorithm
    HELD = "held"                # Quarantined / invisible pending review
    REMOVED = "removed"          # Deleted / hard takedown


class SeverityTier(str, Enum):
    NONE = "none"
    TIER_3_BORDERLINE = "tier_3_borderline"
    TIER_2_MODERATE = "tier_2_moderate"
    TIER_1_SEVERE = "tier_1_severe"


class EnforcementAction(str, Enum):
    ALLOW = "allow"
    DOWNRANK = "downrank"
    RESTRICT_VISIBILITY = "restrict_visibility"
    REMOVE_CONTENT = "remove_content"
    REMOVE_AND_STRIKE = "remove_and_strike"
    ROUTE_TO_LEGAL_HASH_CHECK = "route_to_legal_hash_check"


class ContentItem(BaseModel):
    content_id: str
    author_id: str
    text: str
    view_count: int = 0
    current_visibility: VisibilityState = VisibilityState.VISIBLE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModerationDecision(BaseModel):
    decision_id: str
    content_id: str
    policy_id: str
    policy_version: str
    severity: SeverityTier
    confidence: float = Field(ge=0.0, le=1.0)
    action: EnforcementAction
    new_visibility: VisibilityState
    rationale: str
    actor: str = "ai_classifier"  # model_version or moderator_id
    decided_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class LedgerEvent(BaseModel):
    event_id: str
    content_id: str
    event_type: str  # e.g. "detection_fired", "visibility_transition", "reach_gate_tripped", "human_review"
    actor_type: str  # "ai_model", "human_moderator", "reach_gate", "report_aggregator"
    actor_id: str
    policy_version: Optional[str] = None
    old_state: Optional[str] = None
    new_state: Optional[str] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    prev_hash: Optional[str] = None


# STIX 2.1 Threat Objects for Sigtoc
class STIXThreatObject(BaseModel):
    id: str
    type: str  # "threat-actor", "indicator", "attack-pattern", "campaign"
    spec_version: str = "2.1"
    name: str
    description: Optional[str] = None
    aliases: List[str] = Field(default_factory=list)
    confidence: int = Field(ge=0, le=100, default=75)
    indicators: List[str] = Field(default_factory=list)
    labels: List[str] = Field(default_factory=list)
    created: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    modified: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ThreatReport(BaseModel):
    report_id: str
    source: str  # "darknet_crawler", "telegram_monitor", "commercial_feed"
    title: str
    summary: str
    severity_score: float = Field(ge=0.0, le=10.0)
    credibility_score: float = Field(ge=0.0, le=1.0)
    relevance_score: float = Field(ge=0.0, le=1.0)
    threat_actors: List[str] = Field(default_factory=list)
    evasion_tactics: List[str] = Field(default_factory=list)
    recommended_policy_action: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
