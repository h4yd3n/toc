from typing import Dict, List, Optional
from datetime import datetime, timezone

from shared.models import CollectionTasking, Signal, TaskingStatus
from sigtoc.connectors.base import BaseConnector, GeoScope, TimeWindow

class CollectionManager:
    def __init__(self, connectors: Dict[str, BaseConnector]):
        self.connectors = connectors
    
    async def run_collection(self, taskings: List[CollectionTasking],
                              geo_scope: Optional[GeoScope] = None,
                              query: Optional[str] = None) -> List[Signal]:
        """Run collection for the given taskings, return all collected signals."""
        all_signals = []
        for tasking in taskings:
            connector = self.connectors.get(tasking.source_id)
            if connector:
                signals = await connector.collect(geo_scope=geo_scope, query=query)
                all_signals.extend(signals)
                tasking.last_collected_at = datetime.now(timezone.utc)
                tasking.status = TaskingStatus.CURRENT
        return all_signals
    
    def get_matrix_status(self, taskings: List[CollectionTasking]) -> List[dict]:
        """Return synchronization matrix status for display."""
        status_matrix = []
        for tasking in taskings:
            connector = self.connectors.get(tasking.source_id)
            has_connector = connector is not None
            status_matrix.append({
                "tasking_id": tasking.tasking_id,
                "source_id": tasking.source_id,
                "status": tasking.status.value,
                "last_collected_at": tasking.last_collected_at,
                "has_connector": has_connector
            })
        return status_matrix
