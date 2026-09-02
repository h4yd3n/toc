import hashlib
import uuid
import httpx
from bs4 import BeautifulSoup
from typing import List, Optional
from datetime import datetime, timezone

from shared.models import Source, Signal, AdmiraltyCredibility
from .base import BaseConnector, GeoScope, TimeWindow, ConnectorHealth

class HealthNoticesConnector(BaseConnector):
    """Connector for WHO/CDC Health Notices."""

    URL = "https://wwwnc.cdc.gov/travel/notices"

    async def collect(self, geo_scope: Optional[GeoScope] = None,
                      time_window: Optional[TimeWindow] = None,
                      query: Optional[str] = None) -> List[Signal]:
        signals = []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(self.URL)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    notices = soup.find_all('div', class_='notice')
                    
                    # Also try a more generic approach if class 'notice' is not present
                    if not notices:
                        notices = soup.find_all('li', class_='list-group-item')
                        
                    for notice in notices:
                        title_elem = notice.find(['h3', 'h4', 'a'])
                        if not title_elem:
                            continue
                            
                        title = title_elem.text.strip()
                        date = datetime.now().strftime("%Y-%m-%d") # simplified date
                        
                        origin_key = f"cdc_{title}_{date}"
                        content_hash = hashlib.sha256(title.encode("utf-8")).hexdigest()
                        
                        signal = Signal(
                            signal_id=str(uuid.uuid4()),
                            source_id=self.source.source_id,
                            credibility=AdmiraltyCredibility.CONFIRMED,
                            raw_text=title,
                            url=self.URL,
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
                resp = await client.get(self.URL)
                if resp.status_code == 200:
                    return ConnectorHealth(status="ok", last_success=datetime.now(timezone.utc).isoformat())
        except Exception as e:
            return ConnectorHealth(status="error", error_message=str(e))
        return ConnectorHealth(status="error", error_message="Status code != 200")
