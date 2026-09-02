import os
import uuid
import json
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Any

from pydantic import BaseModel, Field
from anthropic import Anthropic

from shared.models import Signal, Event, GeoPoint

class ScoredEvent(BaseModel):
    event: Event
    affected_dimensions: List[str]
    key_quotes: List[str]

class EventExtractor:
    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        if self.api_key:
            self.client = Anthropic(api_key=self.api_key)
        else:
            self.client = None

    def extract_events(self, signal: Signal) -> List[ScoredEvent]:
        if self.client:
            return self._extract_with_claude(signal)
        else:
            return self._extract_with_heuristics(signal)

    def _extract_with_claude(self, signal: Signal) -> List[ScoredEvent]:
        prompt = f"""
        Extract events from the following text.
        Text: {signal.raw_text}
        
        Provide the output as JSON with a list of events. Each event should have:
        - event_type (str)
        - severity (float 0.0 to 1.0)
        - affected_dimensions (list of str, e.g., 'civil_unrest', 'terrorism')
        - lat (float, optional)
        - lon (float, optional)
        - occurred_at (isoformat string, optional)
        - key_quotes (list of str)
        """
        
        # Simple extraction using tool schema
        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1024,
            tools=[{
                "name": "extract_events",
                "description": "Extract events from text",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "events": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "event_type": {"type": "string"},
                                    "severity": {"type": "number"},
                                    "affected_dimensions": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    },
                                    "lat": {"type": "number"},
                                    "lon": {"type": "number"},
                                    "occurred_at": {"type": "string"},
                                    "key_quotes": {
                                        "type": "array",
                                        "items": {"type": "string"}
                                    }
                                },
                                "required": ["event_type", "severity", "affected_dimensions", "key_quotes"]
                            }
                        }
                    },
                    "required": ["events"]
                }
            }],
            tool_choice={"type": "tool", "name": "extract_events"},
            messages=[{"role": "user", "content": prompt}]
        )
        
        result_events = []
        for content in response.content:
            if content.type == "tool_use" and content.name == "extract_events":
                events_data = content.input.get("events", [])
                for ed in events_data:
                    geo = None
                    if "lat" in ed and "lon" in ed and ed["lat"] is not None and ed["lon"] is not None:
                        geo = GeoPoint(lat=ed["lat"], lon=ed["lon"])
                    
                    occurred_at = None
                    if ed.get("occurred_at"):
                        try:
                            occurred_at = datetime.fromisoformat(ed["occurred_at"].replace("Z", "+00:00"))
                        except ValueError:
                            pass
                    
                    event = Event(
                        event_id=str(uuid.uuid4()),
                        signal_ids=[signal.signal_id],
                        event_type=ed["event_type"],
                        severity=ed["severity"],
                        geo=geo,
                        occurred_at=occurred_at
                    )
                    
                    result_events.append(
                        ScoredEvent(
                            event=event,
                            affected_dimensions=ed["affected_dimensions"],
                            key_quotes=ed["key_quotes"]
                        )
                    )
                break
                
        return result_events

    def _extract_with_heuristics(self, signal: Signal) -> List[ScoredEvent]:
        # Fallback heuristic logic
        text_lower = signal.raw_text.lower()
        events = []
        
        if "protest" in text_lower or "riot" in text_lower:
            event = Event(
                event_id=str(uuid.uuid4()),
                signal_ids=[signal.signal_id],
                event_type="protest",
                severity=0.6,
                geo=None,
                occurred_at=datetime.now(timezone.utc)
            )
            events.append(ScoredEvent(
                event=event,
                affected_dimensions=["civil_unrest"],
                key_quotes=[signal.raw_text[:100]]
            ))
            
        if "explosion" in text_lower or "attack" in text_lower:
            event = Event(
                event_id=str(uuid.uuid4()),
                signal_ids=[signal.signal_id],
                event_type="attack",
                severity=0.9,
                geo=None,
                occurred_at=datetime.now(timezone.utc)
            )
            events.append(ScoredEvent(
                event=event,
                affected_dimensions=["terrorism", "violent_crime"],
                key_quotes=[signal.raw_text[:100]]
            ))
            
        if not events:
            event = Event(
                event_id=str(uuid.uuid4()),
                signal_ids=[signal.signal_id],
                event_type="general",
                severity=0.1,
                geo=None,
                occurred_at=datetime.now(timezone.utc)
            )
            events.append(ScoredEvent(
                event=event,
                affected_dimensions=[],
                key_quotes=[]
            ))
            
        return events
