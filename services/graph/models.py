"""
Domain models for NyayaVarta Knowledge Graph (Milestone 4B).

Defines:
- Node: Judgment, Act, Section, Article, Rule, Schedule, ExternalReference
- Edge: CITES, MENTIONS_PROVISION, PART_OF_ACT, CITES_EXTERNAL
- ExcludedEdge: Records rejected edges with auditable reason codes
- GraphManifest: Metadata and integrity summary
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import hashlib
import json


@dataclass
class Node:
    node_id: str
    node_type: str  # 'Judgment', 'Act', 'Section', 'Article', 'Rule', 'Schedule', 'ExternalReference'
    name: str
    canonical_id: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Edge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str  # 'CITES', 'MENTIONS_PROVISION', 'PART_OF_ACT', 'CITES_EXTERNAL'
    confidence: str  # 'high', 'medium', 'low'
    weight: float = 1.0
    mention_count: int = 1
    mentions: List[Dict[str, Any]] = field(default_factory=list)

    @staticmethod
    def generate_edge_id(source: str, target: str, rel: str) -> str:
        """Deterministic identity rule for deduplicating edges."""
        key = f"{source}->{rel}->{target}"
        return hashlib.sha256(key.encode('utf-8')).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExcludedEdge:
    source_node_id: str
    candidate_target: str
    relationship_type: str
    exclusion_reason: str  # e.g. 'SELF_CITATION', 'TARGET_NOT_IN_CORPUS', 'TITLE_ONLY_UNCORROBORATED', etc.
    exclusion_detail: str
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GraphManifest:
    manifest_version: str = "1.0.0"
    graph_version: str = "v1"
    created_at: str = ""
    nodes_count: int = 0
    nodes_by_type: Dict[str, int] = field(default_factory=dict)
    edges_count: int = 0
    edges_by_type: Dict[str, int] = field(default_factory=dict)
    excluded_edges_count: int = 0
    exclusions_by_reason: Dict[str, int] = field(default_factory=dict)
    unresolved_external_references_count: int = 0
    sha256_checksums: Dict[str, str] = field(default_factory=dict)
    export_files: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
