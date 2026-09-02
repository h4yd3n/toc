import hashlib
import uuid
import httpx
import xml.etree.ElementTree as ET
from typing import List, Optional
from datetime import datetime, timezone

from shared.models import Source, Signal, AdmiraltyCredibility, GeoPoint
from .base import BaseConnector, GeoScope, TimeWindow, ConnectorHealth

class GDACSConnector(BaseConnector):
    """Connector for GDACS (Global Disaster Alert and Coordination System)."""

    RSS_URL = "https://www.gdacs.org/xml/rss.xml"

    async def collect(self, geo_scope: Optional[GeoScope] = None,
                      time_window: Optional[TimeWindow] = None,
                      query: Optional[str] = None) -> List[Signal]:
        signals = []
        try:
            # Try using gdacs_api if possible, but for simplicity and robustness we fallback to RSS immediately
            # because we need to parse specific event types and severities.
            async with httpx.AsyncClient() as client:
                response = await client.get(self.RSS_URL)
                if response.status_code == 200:
                    root = ET.fromstring(response.text)
                    for item in root.findall(".//item"):
                        title = item.findtext("title", "")
                        link = item.findtext("link", "")
                        description = item.findtext("description", "")
                        
                        # gdacs namespaces
                        gdacs_ns = {"gdacs": "http://www.gdacs.org"}
                        geo_ns = {"geo": "http://www.w3.org/2003/01/geo/wgs84_pos#"}
                        
                        event_type = item.findtext("gdacs:eventtype", "", gdacs_ns)
                        event_id = item.findtext("gdacs:eventid", "", gdacs_ns)
                        alert_level = item.findtext("gdacs:alertlevel", "", gdacs_ns)
                        severity = item.findtext("gdacs:severity", "", gdacs_ns)
                        lat_str = item.findtext("geo:lat", "", geo_ns)
                        lon_str = item.findtext("geo:long", "", geo_ns)
                        
                        origin_key = f"gdacs_{event_type}_{event_id}"
                        content_hash = hashlib.sha256(f"{title}{link}".encode("utf-8")).hexdigest()
                        
                        geo = None
                        if lat_str and lon_str:
                            try:
                                geo = GeoPoint(lat=float(lat_str), lon=float(lon_str))
                            except ValueError:
                                pass
                                
                        signal = Signal(
                            signal_id=str(uuid.uuid4()),
                            source_id=self.source.source_id,
                            credibility=AdmiraltyCredibility.CONFIRMED,
                            raw_text=f"{title} - {description} (Severity: {severity})",
                            url=link,
                            geo=geo,
                            content_hash=content_hash,
                            origin_key=origin_key,
                            collected_at=datetime.now(timezone.utc)
                        )
                        signals.append(signal)
                        
        except Exception as e:
            # fail gracefully
            pass
            
        return signals

    async def health_check(self) -> ConnectorHealth:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(self.RSS_URL)
                if resp.status_code == 200:
                    return ConnectorHealth(status="ok", last_success=datetime.now(timezone.utc).isoformat())
        except Exception as e:
            return ConnectorHealth(status="error", error_message=str(e))
        return ConnectorHealth(status="error", error_message="Status code != 200")
