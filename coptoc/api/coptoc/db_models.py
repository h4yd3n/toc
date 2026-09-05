from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared.database import Base


class LocationRow(Base):
    __tablename__ = "cop_locations"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    type: Mapped[str] = mapped_column(String)  # hq | office | datacenter | residence | venue
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    city: Mapped[str] = mapped_column(String)
    country: Mapped[str] = mapped_column(String)
    posture: Mapped[str] = mapped_column(String, default="normal")  # normal | guarded | elevated | high | critical (DEFCON 5 → 1) — set by a human
    sensitivity: Mapped[str] = mapped_column(String, default="standard")  # standard | restricted


class TeamRow(Base):
    __tablename__ = "cop_teams"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    location_id: Mapped[str] = mapped_column(ForeignKey("cop_locations.id"), index=True)
    function: Mapped[str] = mapped_column(String)
    is_security: Mapped[bool] = mapped_column(Boolean, default=False)


class PersonRow(Base):
    __tablename__ = "cop_people"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    team_id: Mapped[str] = mapped_column(ForeignKey("cop_teams.id"), index=True)
    is_vip: Mapped[bool] = mapped_column(Boolean, default=False)
    on_shift: Mapped[bool] = mapped_column(Boolean, default=False)
    shift_role: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    # Contact — what the accountability roll call dials. Synthetic in seed.
    phone: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, default="hris")  # provenance: hris | manual | …
    # Hybrid presence: a check-in inside the freshness window overrides the derived position.
    last_checkin_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_checkin_lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    last_checkin_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_checkin_note: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class EventRow(Base):
    """S3 — a planned corporate event. Attending people get trips generated."""
    __tablename__ = "cop_events"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    event_type: Mapped[str] = mapped_column(String)  # board_meeting | conference | offsite | summit | site_visit
    venue_location_id: Mapped[Optional[str]] = mapped_column(ForeignKey("cop_locations.id"), nullable=True)
    venue_name: Mapped[str] = mapped_column(String)
    venue_lat: Mapped[float] = mapped_column(Float)
    venue_lon: Mapped[float] = mapped_column(Float)
    start_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    description: Mapped[str] = mapped_column(Text, default="")
    security_plan: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    required_security: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # None → the default rule (see service.coverage_required)
    created_by: Mapped[str] = mapped_column(String, default="seed")
    source: Mapped[str] = mapped_column(String, default="calendar")  # provenance: calendar | manual | travel_system


class EventAttendeeRow(Base):
    __tablename__ = "cop_event_attendees"
    event_id: Mapped[str] = mapped_column(ForeignKey("cop_events.id"), primary_key=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("cop_people.id"), primary_key=True)


class TripRow(Base):
    __tablename__ = "cop_trips"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("cop_people.id"), index=True)
    origin_location_id: Mapped[str] = mapped_column(ForeignKey("cop_locations.id"))
    dest_location_id: Mapped[Optional[str]] = mapped_column(ForeignKey("cop_locations.id"), nullable=True)
    dest_name: Mapped[str] = mapped_column(String)
    dest_lat: Mapped[float] = mapped_column(Float)
    dest_lon: Mapped[float] = mapped_column(Float)
    depart_at: Mapped[datetime] = mapped_column(DateTime)
    return_at: Mapped[datetime] = mapped_column(DateTime)
    purpose: Mapped[str] = mapped_column(Text)
    event_id: Mapped[Optional[str]] = mapped_column(ForeignKey("cop_events.id"), nullable=True)
    created_by: Mapped[str] = mapped_column(String, default="seed")
    source: Mapped[str] = mapped_column(String, default="calendar")  # provenance: calendar | travel_system | manual | event


class TripLegRow(Base):
    """§6: one leg of a trip's itinerary — a flight, a ground move, or a night's lodging. Optional on every trip: present
    when the travel system or an EA supplied it, absent otherwise. Never required, never inferred."""
    __tablename__ = "cop_trip_legs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    trip_id: Mapped[str] = mapped_column(ForeignKey("cop_trips.id"), index=True)
    kind: Mapped[str] = mapped_column(String)  # flight | ground | lodging
    label: Mapped[str] = mapped_column(String, default="")  # carrier + number, property, or provider ("UA 954", "Ritz-Carlton Riyadh", "Car service")
    ref: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # confirmation / record locator
    from_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    from_lat: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    from_lon: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    to_name: Mapped[str] = mapped_column(String)  # for lodging: the property; the traveler's position while the leg is current
    to_lat: Mapped[float] = mapped_column(Float)
    to_lon: Mapped[float] = mapped_column(Float)
    start_at: Mapped[datetime] = mapped_column(DateTime)
    end_at: Mapped[datetime] = mapped_column(DateTime)
    note: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String, default="manual")
    created_by: Mapped[str] = mapped_column(String, default="seed")


class ThreatRow(Base):
    """S2. Synthetic rows are seed data; real rows come from Sigtoc collectors (GDACS today)."""
    __tablename__ = "cop_threats"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    external_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, unique=True)  # collector upsert key
    title: Mapped[str] = mapped_column(String)
    summary: Mapped[str] = mapped_column(Text)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String)  # low | moderate | elevated | critical
    event_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String)
    url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    confidence: Mapped[str] = mapped_column(String)  # low | moderate | high
    observed_at: Mapped[datetime] = mapped_column(DateTime)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    country: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # ISO code when the reporting names a country
    scope: Mapped[str] = mapped_column(String, default="point")  # point | country — country-scoped items sit at our nearest site


class ThreatLinkRow(Base):
    """Analyst-confirmed link between a threat and a site or person. Proximity only *suggests*;
    this row is what changes posture."""
    __tablename__ = "cop_threat_links"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    threat_id: Mapped[str] = mapped_column(ForeignKey("cop_threats.id"), index=True)
    target_type: Mapped[str] = mapped_column(String)  # location | person
    target_id: Mapped[str] = mapped_column(String, index=True)
    confirmed_by: Mapped[str] = mapped_column(String)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PIRRow(Base):
    __tablename__ = "cop_pirs"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="OPEN")  # OPEN | COLLECTING | ANSWERED | EXPIRED
    owner: Mapped[str] = mapped_column(String, default="S2")
    priority: Mapped[int] = mapped_column(Integer, default=2)  # 1 high … 3 low
    subject_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # trip | event | location | person
    subject_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class AssessmentRow(Base):
    __tablename__ = "cop_assessments"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    subject_type: Mapped[str] = mapped_column(String)  # trip | event | location | pir
    subject_id: Mapped[str] = mapped_column(String, index=True)
    likelihood: Mapped[str] = mapped_column(String)  # one of the seven ICD 203 terms
    band: Mapped[str] = mapped_column(String)
    confidence: Mapped[str] = mapped_column(String)  # low | moderate | high | insufficient — computed by code
    bluf: Mapped[str] = mapped_column(Text)
    key_judgments_json: Mapped[str] = mapped_column(Text, default="[]")
    evidence_json: Mapped[str] = mapped_column(Text, default="[]")
    gaps_json: Mapped[str] = mapped_column(Text, default="[]")
    author: Mapped[str] = mapped_column(String)  # "ai:<model>" or a person
    status: Mapped[str] = mapped_column(String, default="draft")  # draft | review | approved | superseded
    created_at: Mapped[datetime] = mapped_column(DateTime)
    approved_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class IncidentRow(Base):
    """S6 — an accountability roll call. Opened on a site or a threat; the roster is everyone whose
    current position was in the area when it opened. The TOC's job is to reach every one of them."""
    __tablename__ = "cop_incidents"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)  # site | threat | manual
    location_id: Mapped[Optional[str]] = mapped_column(ForeignKey("cop_locations.id"), nullable=True)
    threat_id: Mapped[Optional[str]] = mapped_column(ForeignKey("cop_threats.id"), nullable=True)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String, default="open")  # open | closed
    opened_by: Mapped[str] = mapped_column(String)
    opened_at: Mapped[datetime] = mapped_column(DateTime)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class AccountabilityRow(Base):
    __tablename__ = "cop_accountability"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("cop_incidents.id"), index=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("cop_people.id"), index=True)
    status: Mapped[str] = mapped_column(String, default="unaccounted")  # unaccounted | contacted | safe | injured | assist | unreachable
    basis: Mapped[str] = mapped_column(String, default="in_area")  # present | in_area | assigned — why this name is on the roster (Decision A)
    checkin_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # Decision B
    method: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # call | sms | app | in_person
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    updated_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class DeliveryRow(Base):
    """One outbound message attempt for a roll-call check-in request (Decision 1: SMS + chat)."""
    __tablename__ = "cop_deliveries"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("cop_incidents.id"), index=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("cop_people.id"), index=True)
    channel: Mapped[str] = mapped_column(String)  # sms | chat
    status: Mapped[str] = mapped_column(String)   # sent | simulated | failed
    provider_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime)


class EventCoverageRow(Base):
    """S3 long-range planning: a security person assigned to cover an event, in a role."""
    __tablename__ = "cop_event_coverage"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("cop_events.id"), index=True)
    person_id: Mapped[str] = mapped_column(ForeignKey("cop_people.id"), index=True)
    role: Mapped[str] = mapped_column(String, default="agent")  # lead | agent | advance | driver
    assigned_by: Mapped[str] = mapped_column(String)
    assigned_at: Mapped[datetime] = mapped_column(DateTime)
