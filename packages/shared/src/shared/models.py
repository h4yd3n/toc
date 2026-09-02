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

class IntelDiscipline(str, Enum):
    OSINT = "OSINT"
    CYBINT = "CYBINT"
    GEOINT = "GEOINT"
    HUMINT = "HUMINT"
    SIGINT = "SIGINT"

class AdmiraltyReliability(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"

class AdmiraltyCredibility(int, Enum):
    CONFIRMED = 1
    PROBABLY_TRUE = 2
    POSSIBLY_TRUE = 3
    DOUBTFUL = 4
    IMPROBABLE = 5
    CANNOT_JUDGE = 6

class AnalyticConfidence(str, Enum):
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"

class RequirementStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ANSWERED = "ANSWERED"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"

class AssessmentStatus(str, Enum):
    DRAFT = "DRAFT"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    SUPERSEDED = "SUPERSEDED"

class TaskingStatus(str, Enum):
    CURRENT = "CURRENT"
    DUE = "DUE"
    OVERDUE = "OVERDUE"
    GAP = "GAP"

class RiskBand(str, Enum):
    LOW = "LOW"
    GUARDED = "GUARDED"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    SEVERE = "SEVERE"

class AssetType(str, Enum):
    OFFICE = "OFFICE"
    DATA_CENTER = "DATA_CENTER"
    VENDOR = "VENDOR"
    WAREHOUSE = "WAREHOUSE"

class RequirementKind(str, Enum):
    PIR = "PIR"
    FFIR = "FFIR"

class Source(BaseModel):
    source_id: str
    name: str
    discipline: IntelDiscipline
    reliability: AdmiraltyReliability
    connector_class: str
    enabled: bool = True

class GeoPoint(BaseModel):
    lat: float
    lon: float
    label: Optional[str] = None

class Signal(BaseModel):
    signal_id: str
    source_id: str
    credibility: AdmiraltyCredibility
    raw_text: str
    url: Optional[str] = None
    published_at: Optional[datetime] = None
    collected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    geo: Optional[GeoPoint] = None
    content_hash: str
    origin_key: Optional[str] = None

class Event(BaseModel):
    event_id: str
    signal_ids: List[str]
    event_type: str
    severity: float = Field(ge=0.0, le=1.0)
    geo: Optional[GeoPoint] = None
    occurred_at: Optional[datetime] = None
    entity_ids: List[str] = Field(default_factory=list)

class Asset(BaseModel):
    asset_id: str
    type: AssetType
    geo: GeoPoint
    criticality: float = Field(ge=0.0, le=1.0)
    posture: str = 'normal'

class Person(BaseModel):
    person_id: str
    role: str
    sensitivity_tier: int = 1
    public_profile: bool = False

class ItineraryLeg(BaseModel):
    leg_id: str
    geo: GeoPoint
    arrive_at: datetime
    depart_at: datetime

class Trip(BaseModel):
    trip_id: str
    person_id: str
    purpose: str
    mission_profile: str = 'general'
    legs: List[ItineraryLeg] = Field(default_factory=list)

class Requirement(BaseModel):
    req_id: str
    kind: RequirementKind
    question: str
    owner_id: str
    priority: int = 1
    geo_scope: Optional[GeoPoint] = None
    expires_at: Optional[datetime] = None
    status: RequirementStatus = RequirementStatus.ACTIVE

class SIR(BaseModel):
    sir_id: str
    req_id: str
    question: str
    dimensions: List[str] = Field(default_factory=list)
    status: str = 'active'

class Indicator(BaseModel):
    indicator_id: str
    sir_id: str
    description: str
    observable_pattern: str
    volatility: str = 'medium'

class CollectionTasking(BaseModel):
    tasking_id: str
    indicator_id: str
    source_id: str
    frequency: str = 'daily'
    last_collected_at: Optional[datetime] = None
    status: TaskingStatus = TaskingStatus.DUE

class DimensionScore(BaseModel):
    assessment_id: str
    dimension: str
    base: float
    delta: float
    value: float
    analytic_confidence: AnalyticConfidence
    weight: float = 1.0

class Evidence(BaseModel):
    dimension_score_id: str
    event_id: str
    contribution: float
    quote: str
    retrieved_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Assessment(BaseModel):
    assessment_id: str
    subject_type: str
    subject_id: str
    framework: str = 'mett-tc'
    dimension_scores: List[DimensionScore] = Field(default_factory=list)
    inherent_score: Optional[float] = None
    residual_score: Optional[float] = None
    analytic_confidence: Optional[AnalyticConfidence] = None
    status: AssessmentStatus = AssessmentStatus.DRAFT
    author: str = 'ai'
    reviewer_id: Optional[str] = None
    approved_at: Optional[datetime] = None
    collection_gaps: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
