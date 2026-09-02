from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from shared.models import Source, Signal, GeoPoint

@dataclass
class GeoScope:
    center: GeoPoint
    radius_km: float

@dataclass
class TimeWindow:
    start: str  # ISO format
    end: str    # ISO format

@dataclass
class ConnectorHealth:
    status: str  # 'ok', 'degraded', 'error'
    last_success: Optional[str] = None
    error_message: Optional[str] = None

class BaseConnector(ABC):
    """Base class for all OSINT collection connectors."""
    
    def __init__(self, source: Source):
        self.source = source
    
    @abstractmethod
    async def collect(self, geo_scope: Optional[GeoScope] = None,
                      time_window: Optional[TimeWindow] = None,
                      query: Optional[str] = None) -> List[Signal]:
        """Collect raw signals. Returns immutable Signal objects."""
        pass
    
    @abstractmethod
    async def health_check(self) -> ConnectorHealth:
        """Return connector health for synchronization matrix."""
        pass
