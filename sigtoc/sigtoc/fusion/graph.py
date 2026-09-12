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

    def get_campaigns_for_actor(self, actor_name: str) -> List[str]:
        if actor_name not in self.graph:
            return []
        return [
            nbr for nbr in self.graph.neighbors(actor_name)
            if self.graph.nodes[nbr].get("entity_type") == "campaign"
        ]

    def get_tactics_for_campaign(self, campaign_name: str) -> List[str]:
        if campaign_name not in self.graph:
            return []
        return [
            nbr for nbr in self.graph.neighbors(campaign_name)
            if self.graph.nodes[nbr].get("entity_type") == "attack-pattern"
        ]

    def find_coordinated_clusters(self) -> List[List[str]]:
        """Returns connected components that represent coordinated campaign/actor clusters."""
        return [list(c) for c in nx.connected_components(self.graph) if len(c) > 1]

    def get_actors_targeting_sector(self, sector_name: str) -> List[str]:
        """Returns all threat actors linked to a specific targeted sector or industry."""
        if sector_name not in self.graph:
            return []
        return [
            nbr for nbr in self.graph.neighbors(sector_name)
            if self.graph.nodes[nbr].get("entity_type") in ("threat-actor", "actor")
        ]

    def get_all_entities(self) -> List[Dict]:
        nodes = []
        for n, data in self.graph.nodes(data=True):
            nodes.append({"name": n, **data})
        return nodes
