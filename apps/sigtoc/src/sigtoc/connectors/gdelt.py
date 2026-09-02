import hashlib
import uuid
import httpx
from typing import List, Optional
from datetime import datetime, timezone

from shared.models import Source, Signal, AdmiraltyCredibility
from .base import BaseConnector, GeoScope, TimeWindow, ConnectorHealth

class GDELTConnector(BaseConnector):
    """Connector for GDELT Doc API."""

    API_URL = "http://api.gdeltproject.org/api/v2/doc/doc"

    async def collect(self, geo_scope: Optional[GeoScope] = None,
                      time_window: Optional[TimeWindow] = None,
                      query: Optional[str] = None) -> List[Signal]:
        signals = []
        if not query:
            return signals

        params = {
            "query": query,
            "mode": "artlist",
            "format": "json",
            "maxrecords": "50"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.API_URL, params=params)
                if response.status_code == 200:
                    data = response.json()
                    
                    if "articles" in data:
                        for article in data["articles"]:
                            url = article.get("url", "")
                            title = article.get("title", "")
                            if not url:
                                continue
                                
                            origin_key = url
                            content_to_hash = title + url
                            content_hash = hashlib.sha256(content_to_hash.encode("utf-8")).hexdigest()
                            
                            signal = Signal(
                                signal_id=str(uuid.uuid4()),
                                source_id=self.source.source_id,
                                credibility=AdmiraltyCredibility.POSSIBLY_TRUE,
                                raw_text=title,
                                url=url,
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
                resp = await client.get(self.API_URL, params={"query": "test", "mode": "artlist", "format": "json", "maxrecords": "1"})
                if resp.status_code == 200:
                    return ConnectorHealth(status="ok", last_success=datetime.now(timezone.utc).isoformat())
        except Exception as e:
            return ConnectorHealth(status="error", error_message=str(e))
        return ConnectorHealth(status="error", error_message="Status code != 200")
