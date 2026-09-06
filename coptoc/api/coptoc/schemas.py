from datetime import datetime
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field

Posture = Literal["normal", "guarded", "elevated", "high", "critical"]
GraphicConfidence = Literal["confirmed", "probable", "possible", "template"]

class TripCreate(BaseModel):
    person_id: str
    origin_location_id: str
    dest_location_id: Optional[str] = None
    dest_name: Optional[str] = None
    dest_lat: Optional[float] = None
    dest_lon: Optional[float] = None
    depart_at: datetime
    return_at: datetime
    purpose: str = ""

class TripUpdate(BaseModel):
    dest_location_id: Optional[str] = None
    dest_name: Optional[str] = None
    dest_lat: Optional[float] = None
    dest_lon: Optional[float] = None
    depart_at: Optional[datetime] = None
    return_at: Optional[datetime] = None
    purpose: Optional[str] = None

SupplyCategory = Literal["fuel", "water", "rations", "medical", "ammunition", "parts", "equipment", "other"]
SystemCategory = Literal["comms", "network", "application", "power", "sensor", "other"]
PaceRole = Literal["primary", "alternate", "contingency", "emergency"]

class SupplyCreate(BaseModel):
    location_id: Optional[str] = None
    category: SupplyCategory = "other"
    item: str
    on_hand: float = Field(ge=0)
    required: float = Field(ge=0)
    unit: str = "ea"
    note: str = ""

class SupplyUpdate(BaseModel):
    on_hand: Optional[float] = Field(default=None, ge=0)
    required: Optional[float] = Field(default=None, ge=0)
    unit: Optional[str] = None
    note: Optional[str] = None

class ShipmentCreate(BaseModel):
    description: str
    category: SupplyCategory = "other"
    quantity: str = ""
    from_name: str = ""
    to_location_id: Optional[str] = None
    to_name: str = ""
    eta: datetime
    status: Literal["planned", "in_transit", "delayed", "arrived", "cancelled"] = "planned"
    priority: Literal["routine", "priority", "urgent"] = "routine"
    carrier: str = ""
    ref: Optional[str] = None
    note: str = ""

class ShipmentUpdate(BaseModel):
    status: Optional[Literal["planned", "in_transit", "delayed", "arrived", "cancelled"]] = None
    eta: Optional[datetime] = None
    priority: Optional[Literal["routine", "priority", "urgent"]] = None
    note: Optional[str] = None

class SystemCreate(BaseModel):
    name: str
    category: SystemCategory = "comms"
    location_id: Optional[str] = None
    pace: Optional[PaceRole] = None
    status: Literal["up", "degraded", "down"] = "up"
    note: str = ""

class SystemUpdate(BaseModel):
    status: Optional[Literal["up", "degraded", "down"]] = None
    pace: Optional[PaceRole] = None
    note: Optional[str] = None

class TaskingCreate(BaseModel):
    kind: Literal["collection", "comms", "supply", "movement", "coverage", "other"] = "other"
    title: str
    from_section: Literal["S1", "S2", "S3", "S4", "S6"]
    to_section: Literal["S1", "S2", "S3", "S4", "S6"]
    subject_type: Optional[Literal["operation", "event", "requirement", "location", "trip"]] = None
    subject_id: Optional[str] = None
    subject_name: str = ""
    asset: str = ""
    window_from: Optional[datetime] = None
    window_to: Optional[datetime] = None
    priority: Literal["routine", "priority", "urgent"] = "routine"
    notes: str = ""

class AreaRatingIn(BaseModel):
    indicator: str
    rating: Literal["green", "amber", "red", "unknown"] = "unknown"
    note: str = ""

class AreaCreate(BaseModel):
    place: Optional[str] = None            # required unless location_id names a site
    location_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    ratings: List[AreaRatingIn] = []
    summary: str = ""

class GraphicCreate(BaseModel):
    type: str
    kind: Literal["point", "line", "polygon"]
    name: str
    geometry: Any                     # point: [lon, lat]; line / polygon: [[lon, lat], …]
    window_from: Optional[datetime] = None
    window_to: Optional[datetime] = None
    status: Literal["planned", "active"] = "active"
    note: str = ""
    confidence: GraphicConfidence = "confirmed"
    basis: str = ""
    subject_type: Optional[Literal["event", "location", "operation", "trip", "case", "report", "actor", "threat", "nai"]] = None
    subject_id: Optional[str] = None

class GraphicUpdate(BaseModel):
    name: Optional[str] = None
    geometry: Optional[Any] = None
    window_from: Optional[datetime] = None
    window_to: Optional[datetime] = None
    status: Optional[Literal["planned", "active", "retired"]] = None
    note: Optional[str] = None
    confidence: Optional[GraphicConfidence] = None
    basis: Optional[str] = None

class AreaUpdate(BaseModel):
    ratings: Optional[List[AreaRatingIn]] = None
    summary: Optional[str] = None

class TaskingUpdate(BaseModel):
    status: Optional[Literal["requested", "accepted", "scheduled", "complete", "declined"]] = None
    result: Optional[str] = None
    notes: Optional[str] = None
    asset: Optional[str] = None
    window_from: Optional[datetime] = None
    window_to: Optional[datetime] = None
    priority: Optional[Literal["routine", "priority", "urgent"]] = None

class LegCreate(BaseModel):
    kind: Literal["flight", "ground", "lodging"]
    label: str = ""
    ref: Optional[str] = None
    from_name: Optional[str] = None
    from_lat: Optional[float] = None
    from_lon: Optional[float] = None
    to_name: str
    to_lat: float
    to_lon: float
    start_at: datetime
    end_at: datetime
    note: str = ""

class EventCreate(BaseModel):
    name: str
    event_type: str = "conference"
    venue_location_id: Optional[str] = None
    venue_name: Optional[str] = None
    venue_lat: Optional[float] = None
    venue_lon: Optional[float] = None
    start_at: datetime
    end_at: datetime
    description: str = ""
    security_plan: Optional[str] = None
    attendee_ids: List[str] = Field(default_factory=list)
    generate_trips: bool = True

class EventUpdate(BaseModel):
    name: Optional[str] = None
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    description: Optional[str] = None
    security_plan: Optional[str] = None
    required_security: Optional[int] = Field(None, ge=0)

class CoverageAssign(BaseModel):
    person_id: str
    role: Literal["lead", "agent", "advance", "driver"] = "agent"

class AttendeesAdd(BaseModel):
    person_ids: List[str]
    generate_trips: bool = True

class CheckIn(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    note: Optional[str] = None
    at: Optional[datetime] = None

class LocationCreate(BaseModel):
    name: str
    type: str = "office"
    lat: float
    lon: float
    city: str = ""
    country: str = ""
    posture: str = "normal"
    sensitivity: str = "standard"
    is_toc: bool = False


class LocationUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    city: Optional[str] = None
    country: Optional[str] = None
    sensitivity: Optional[str] = None


class PostureUpdate(BaseModel):
    posture: Posture
    reason: str = ""

class ShiftUpdate(BaseModel):
    on_shift: bool
    shift_role: Optional[str] = None

class ThreatLinkCreate(BaseModel):
    target_type: Literal["location", "person"]
    target_id: str
    note: Optional[str] = None

class PIRCreate(BaseModel):
    question: str
    priority: int = 2
    owner: str = "S2"
    subject_type: Optional[str] = None
    subject_id: Optional[str] = None
    expires_at: Optional[datetime] = None

class PIRUpdate(BaseModel):
    status: Optional[Literal["OPEN", "COLLECTING", "ANSWERED", "EXPIRED"]] = None
    priority: Optional[int] = None
    question: Optional[str] = None

class AssessmentDraftRequest(BaseModel):
    subject_type: Literal["trip", "event", "location", "pir"]
    subject_id: str

class AssessmentUpdate(BaseModel):
    status: Optional[Literal["draft", "review", "approved", "superseded"]] = None
    bluf: Optional[str] = None


class IncidentOpen(BaseModel):
    title: Optional[str] = None
    location_id: Optional[str] = None
    threat_id: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_km: float = 5.0
    notes: Optional[str] = None

class RosterUpdate(BaseModel):
    status: Literal["unaccounted", "contacted", "safe", "injured", "assist", "unreachable"]
    method: Optional[Literal["call", "sms", "app", "in_person"]] = "call"
    note: Optional[str] = None

class IncidentClose(BaseModel):
    notes: Optional[str] = None

class RosterAdd(BaseModel):
    """Decision N: anyone on the floor may add a missed name — an existing person by id, or a visitor/contractor by name."""
    person_id: Optional[str] = None
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = "Visitor"
    note: Optional[str] = None


class EstimateUpdate(BaseModel):
    assessment: str
    recommendation: str = ""

class WatchTake(BaseModel):
    battle_captain: str

class Handover(BaseModel):
    notes: Optional[str] = None
    nstr: bool = False

class Acknowledge(BaseModel):
    battle_captain: str
    acknowledged_item_ids: List[str] = Field(default_factory=list)

class WatchConfigUpdate(BaseModel):
    pattern: Literal["follow_the_sun", "day_night"]
    overlap_minutes: Optional[int] = None


# §5.10 #3 — operations
class TaskCreate(BaseModel):
    title: str
    section: Literal["S1", "S2", "S3", "S4", "S6"] = "S3"
    owner: str = ""
    due_at: Optional[datetime] = None
    note: str = ""

class OperationCreate(BaseModel):
    subject_type: Literal["event", "trip", "location"]
    subject_id: str
    title: Optional[str] = None
    from_assessment_id: Optional[str] = None
    from_area_id: Optional[str] = None
    notes: str = ""
    tasks: Optional[List[TaskCreate]] = None  # None → the standard skeleton for the subject kind

class OperationUpdate(BaseModel):
    status: Optional[Literal["planned", "active", "complete", "cancelled"]] = None
    notes: Optional[str] = None

class TaskUpdate(BaseModel):
    status: Optional[Literal["todo", "doing", "done", "blocked"]] = None
    owner: Optional[str] = None
    due_at: Optional[datetime] = None
    note: Optional[str] = None
    title: Optional[str] = None

class ResourceCreate(BaseModel):
    item: str
    qty: int = Field(1, ge=1)
    note: str = ""

class ResourceUpdate(BaseModel):
    status: Literal["requested", "approved", "issued", "denied"]
    note: Optional[str] = None


# §13 imports
class ImportText(BaseModel):
    text: str
    source: Optional[str] = None

class BadgeEvent(BaseModel):
    person_id: Optional[str] = None
    email: Optional[str] = None
    location_id: str
    at: Optional[str] = None
    direction: Literal["in", "out"] = "in"

class BadgeBatch(BaseModel):
    events: List[BadgeEvent]
    source: Optional[str] = "badge"
