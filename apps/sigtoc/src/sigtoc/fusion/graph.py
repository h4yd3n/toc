from typing import Dict, List, Set
import networkx as nx
from shared.models import STIXThreatObject


class ThreatEntityGraph:
    """
    Entity Resolution & Threat Graph:
    Fuses threat actor aliases, infrastructure IPs, crypto wallets, and targets.
    """

    def __init__(self):
        self.graph = nx.Graph()

    def add_threat_entity(self, entity: STIXThreatObject):
        self.graph.add_node(
            entity.name,
            entity_id=entity.id,
            entity_type=entity.type,
            confidence=entity.confidence,
        )
        for alias in entity.aliases:
            self.graph.add_node(alias, entity_type="alias")
            self.graph.add_edge(entity.name, alias, relationship="same-as")

    def link_entities(self, entity_a: str, entity_b: str, relationship: str = "associated-with"):
        self.graph.add_edge(entity_a, entity_b, relationship=relationship)

    def get_related_entities(self, entity_name: str) -> List[str]:
        if entity_name not in self.graph:
            return []
        return list(self.graph.neighbors(entity_name))

    def get_all_entities(self) -> List[Dict]:
        nodes = []
        for n, data in self.graph.nodes(data=True):
            nodes.append({"name": n, **data})
        return nodes
