from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

Posture = Literal["normal", "guarded", "elevated", "high", "critical"]

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
