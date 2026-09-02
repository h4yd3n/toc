import hashlib
import uuid
import httpx
from typing import List, Optional
from datetime import datetime, timezone

from shared.models import Source, Signal, AdmiraltyCredibility
from .base import BaseConnector, GeoScope, TimeWindow, ConnectorHealth

class StateDeptConnector(BaseConnector):
    """Connector for US State Department Travel Advisories."""

    API_URL = "https://cadataapi.state.gov/api/TravelAdvisories"
    FALLBACK_URL = "https://travel.state.gov/_res/rss/TWs.xml"

    async def collect(self, geo_scope: Optional[GeoScope] = None,
                      time_window: Optional[TimeWindow] = None,
                      query: Optional[str] = None) -> List[Signal]:
        signals = []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.API_URL)
                if response.status_code == 200:
                    data = response.json()
                    
                    if "Data" in data:
                        for entry in data["Data"]:
                            advisory = entry.get("TravelAdvisory", {})
                            country_code = advisory.get("iso_code", "XX")
                            date_str = advisory.get("advisory_date", "")
                            text = advisory.get("advisory_text", "")
                            
                            # Skip if no text
                            if not text:
                                continue
                                
                            origin_key = f"state_dept_{country_code}_{date_str}"
                            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
                            
                            signal = Signal(
                                signal_id=str(uuid.uuid4()),
                                source_id=self.source.source_id,
                                credibility=AdmiraltyCredibility.PROBABLY_TRUE,
                                raw_text=text,
                                url=advisory.get("url", self.API_URL),
                                content_hash=content_hash,
                                origin_key=origin_key,
                                collected_at=datetime.now(timezone.utc)
                            )
                            signals.append(signal)
                            
        except Exception as e:
            # We fail gracefully on error
            pass
            
        return signals

    async def health_check(self) -> ConnectorHealth:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.API_URL)
                if resp.status_code == 200:
                    return ConnectorHealth(status="ok", last_success=datetime.now(timezone.utc).isoformat())
        except Exception as e:
            return ConnectorHealth(status="error", error_message=str(e))
        return ConnectorHealth(status="error", error_message="Status code != 200")
