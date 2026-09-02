import json
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

import typer
from rich.console import Console

from shared.models import Trip, Assessment, AssessmentStatus, AnalyticConfidence, DimensionScore, Evidence, GeoPoint, ItineraryLeg
from sigtoc.output.assessment_renderer import AssessmentRenderer
from sigtoc.output.intsum_renderer import INTSUMRenderer

app = typer.Typer(help="SIGTOC Command Line Interface")
trip_app = typer.Typer(help="Manage trips")
app.add_typer(trip_app, name="trip")

console = Console()
STATE_FILE = "sigtoc_state.json"

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            # deserialize
            return {
                "trips": {k: Trip(**v) for k, v in data.get("trips", {}).items()},
                "assessments": {k: Assessment(**v) for k, v in data.get("assessments", {}).items()}
            }
    return {"trips": {}, "assessments": {}}

def save_state(state):
    # serialize
    data = {
        "trips": {k: v.model_dump(mode="json") for k, v in state["trips"].items()},
        "assessments": {k: v.model_dump(mode="json") for k, v in state["assessments"].items()}
    }
    with open(STATE_FILE, "w") as f:
        json.dump(data, f, indent=2)

@trip_app.command("create")
def trip_create(
    traveler: str = typer.Option(..., help="Traveler ID/Name"),
    destination: str = typer.Option(..., help="Destination label"),
    lat: float = typer.Option(..., help="Destination latitude"),
    lon: float = typer.Option(..., help="Destination longitude"),
    arrive: str = typer.Option(..., help="Arrival date (YYYY-MM-DD)"),
    depart: str = typer.Option(..., help="Departure date (YYYY-MM-DD)"),
    purpose: str = typer.Option(..., help="Purpose of the trip")
):
    state = load_state()
    trip_id = f"trip_{uuid.uuid4().hex[:8]}"
    arrive_dt = datetime.strptime(arrive, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    depart_dt = datetime.strptime(depart, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    
    trip = Trip(
        trip_id=trip_id,
        person_id=traveler,
        purpose=purpose,
        legs=[
            ItineraryLeg(
                leg_id=f"leg_{uuid.uuid4().hex[:8]}",
                geo=GeoPoint(lat=lat, lon=lon, label=destination),
                arrive_at=arrive_dt,
                depart_at=depart_dt
            )
        ]
    )
    state["trips"][trip_id] = trip
    save_state(state)
    console.print(f"[green]Created trip [bold]{trip_id}[/bold] for {traveler} to {destination}[/green]")

@trip_app.command("list")
def trip_list():
    state = load_state()
    trips = state.get("trips", {})
    if not trips:
        console.print("No trips found.")
        return
    for trip_id, trip in trips.items():
        dest = trip.legs[0].geo.label if trip.legs else "Unknown"
        console.print(f"- {trip_id}: {trip.person_id} to {dest} ({trip.purpose})")

@app.command("collect")
def collect(trip: str = typer.Option(..., help="Trip ID")):
    state = load_state()
    if trip not in state["trips"]:
        console.print(f"[red]Trip {trip} not found[/red]")
        raise typer.Exit(1)
    
    # Mock collection
    console.print(f"[blue]Running Tier 1 collection for trip {trip}...[/blue]")
    console.print("[green]Collection complete! 14 signals gathered.[/green]")

@app.command("matrix")
def matrix(trip: str = typer.Option(..., help="Trip ID")):
    state = load_state()
    if trip not in state["trips"]:
        console.print(f"[red]Trip {trip} not found[/red]")
        raise typer.Exit(1)
    
    from rich.table import Table
    table = Table("Source ID", "Status", "Last Collected")
    table.add_row("osint_api", "CURRENT", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"))
    table.add_row("geo_feed", "DUE", "N/A")
    console.print(table)

@app.command("assess")
def assess(trip: str = typer.Option(..., help="Trip ID"), framework: str = typer.Option("mett-tc", help="Assessment framework")):
    state = load_state()
    t = state["trips"].get(trip)
    if not t:
        console.print(f"[red]Trip {trip} not found[/red]")
        raise typer.Exit(1)
    
    console.print(f"[blue]Running {framework} analysis...[/blue]")
    
    asmt_id = f"asmt_{uuid.uuid4().hex[:8]}"
    asmt = Assessment(
        assessment_id=asmt_id,
        subject_type="trip",
        subject_id=trip,
        framework=framework,
        inherent_score=75.5,
        analytic_confidence=AnalyticConfidence.MODERATE,
        status=AssessmentStatus.DRAFT,
        collection_gaps=["No ground truth from local assets"]
    )
    
    # Add dummy dimensions
    asmt.dimension_scores = [
        DimensionScore(assessment_id=asmt_id, dimension="Mission", base=70, delta=5, value=75, analytic_confidence=AnalyticConfidence.HIGH),
        DimensionScore(assessment_id=asmt_id, dimension="Enemy", base=80, delta=0, value=80, analytic_confidence=AnalyticConfidence.MODERATE),
    ]
    
    state["assessments"][asmt_id] = asmt
    save_state(state)
    console.print(f"[green]Assessment [bold]{asmt_id}[/bold] generated in DRAFT state.[/green]")

@app.command("approve")
def approve(assessment: str = typer.Option(..., help="Assessment ID"), reviewer: str = typer.Option(..., help="Reviewer email")):
    state = load_state()
    asmt = state["assessments"].get(assessment)
    if not asmt:
        console.print(f"[red]Assessment {assessment} not found[/red]")
        raise typer.Exit(1)
    
    asmt.status = AssessmentStatus.APPROVED
    asmt.reviewer_id = reviewer
    asmt.approved_at = datetime.now(timezone.utc)
    
    save_state(state)
    console.print(f"[green]Assessment [bold]{assessment}[/bold] APPROVED by {reviewer}.[/green]")

@app.command("report")
def report(assessment: str = typer.Option(..., help="Assessment ID"), format: str = typer.Option("terminal", help="Format: terminal or markdown")):
    state = load_state()
    asmt = state["assessments"].get(assessment)
    if not asmt:
        console.print(f"[red]Assessment {assessment} not found[/red]")
        raise typer.Exit(1)
    
    t = state["trips"].get(asmt.subject_id)
    if not t:
        console.print(f"[red]Associated trip {asmt.subject_id} not found[/red]")
        raise typer.Exit(1)
    
    evidence = [
        Evidence(dimension_score_id=f"{assessment}_Mission", event_id="evt_1", contribution=5.0, quote="High profile target detected")
    ]
    
    if format == "markdown":
        output = AssessmentRenderer.render_markdown(asmt, t, asmt.dimension_scores, evidence)
        console.print(output)
    else:
        AssessmentRenderer.render_terminal(asmt, t, asmt.dimension_scores, evidence)

@app.command("intsum")
def intsum(date: str = typer.Option("today", help="Date for INTSUM")):
    bluf = "Overall global risk remains moderate. Travel to region X requires heightened awareness."
    pirs = [{"id": "PIR-01", "status": "ANSWERED"}, {"id": "PIR-02", "status": "ACTIVE"}]
    signals = [{"source": "OSINT", "summary": "Protests reported in downtown", "credibility": 3}]
    scores = [{"entity": "Office A", "old": 40, "new": 60, "reason": "Local unrest"}]
    travel = [{"person": "CEO", "location": "Riyadh", "risk": "Moderate"}]
    gaps = [{"description": "Lack of updates from regional office"}]
    
    INTSUMRenderer.render_terminal(
        date_str=date,
        bluf=bluf,
        pir_statuses=pirs,
        significant_signals=signals,
        score_changes=scores,
        active_travel=travel,
        collection_gaps=gaps
    )

if __name__ == "__main__":
    app()
