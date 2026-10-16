"""
SQLite Graph Store for NyayaVarta Knowledge Graph (Milestone 4B).
Provides inspectable relational storage, indexing, and graph traversal queries.
"""
import sqlite3
import json
import os
from typing import Dict, Any, List, Optional, Tuple
from services.graph.models import Node, Edge, ExcludedEdge


from collections import defaultdict


class SQLiteGraphStore:
    def __init__(self, db_path: str = "data/processed/graph/v1/graph.db", preload_index: bool = False):
        self.db_path = db_path
        self._in_memory_loaded = False
        self._node_cache: Dict[str, Dict[str, Any]] = {}
        self._cited_edges: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._citing_edges: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._doc_to_provisions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._provision_to_docs: Dict[str, List[str]] = defaultdict(list)
        self._provision_df: Dict[str, int] = defaultdict(int)

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

        if preload_index and os.path.exists(self.db_path):
            self.load_in_memory_index()

    def load_in_memory_index(self):
        """Preload graph adjacency and provision metadata into memory for sub-millisecond traversal."""
        if not os.path.exists(self.db_path):
            return

        with self._get_connection() as conn:
            # 1. Preload nodes
            cursor = conn.execute("SELECT node_id, node_type, name, canonical_id, properties_json FROM nodes")
            for row in cursor.fetchall():
                self._node_cache[row["node_id"]] = {
                    "node_id": row["node_id"],
                    "node_type": row["node_type"],
                    "name": row["name"],
                    "canonical_id": row["canonical_id"],
                    "properties": json.loads(row["properties_json"])
                }

            # 2. Preload CITES edges
            cursor = conn.execute("""
                SELECT e.*, n.name as target_name, n.properties_json as target_props
                FROM edges e
                JOIN nodes n ON e.target_node_id = n.node_id
                WHERE e.relationship_type = 'CITES'
            """)
            for row in cursor.fetchall():
                d = dict(row)
                self._cited_edges[d["source_node_id"]].append(d)

            cursor = conn.execute("""
                SELECT e.*, n.name as source_name, n.properties_json as source_props
                FROM edges e
                JOIN nodes n ON e.source_node_id = n.node_id
                WHERE e.relationship_type = 'CITES'
            """)
            for row in cursor.fetchall():
                d = dict(row)
                self._citing_edges[d["target_node_id"]].append(d)

            # 3. Preload MENTIONS_PROVISION edges
            cursor = conn.execute("""
                SELECT e.*, n.node_type as provision_type, n.name as provision_name
                FROM edges e
                JOIN nodes n ON e.target_node_id = n.node_id
                WHERE e.relationship_type = 'MENTIONS_PROVISION'
            """)
            for row in cursor.fetchall():
                d = dict(row)
                src = d["source_node_id"]
                tgt = d["target_node_id"]
                self._doc_to_provisions[src].append(d)
                self._provision_to_docs[tgt].append(src)

            # 4. Compute provision document frequencies
            for prov_id, doc_list in self._provision_to_docs.items():
                self._provision_df[prov_id] = len(set(doc_list))

        self._in_memory_loaded = True

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    canonical_id TEXT,
                    properties_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS edges (
                    edge_id TEXT PRIMARY KEY,
                    source_node_id TEXT NOT NULL,
                    target_node_id TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    confidence TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 1.0,
                    mention_count INTEGER NOT NULL DEFAULT 1,
                    mentions_json TEXT NOT NULL,
                    FOREIGN KEY (source_node_id) REFERENCES nodes(node_id),
                    FOREIGN KEY (target_node_id) REFERENCES nodes(node_id)
                );

                CREATE TABLE IF NOT EXISTS excluded_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_node_id TEXT NOT NULL,
                    candidate_target TEXT NOT NULL,
                    relationship_type TEXT NOT NULL,
                    exclusion_reason TEXT NOT NULL,
                    exclusion_detail TEXT NOT NULL,
                    provenance_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_nodes_type ON nodes(node_type);
                CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_node_id);
                CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_node_id);
                CREATE INDEX IF NOT EXISTS idx_edges_rel ON edges(relationship_type);
                CREATE INDEX IF NOT EXISTS idx_edges_source_rel ON edges(source_node_id, relationship_type);
                CREATE INDEX IF NOT EXISTS idx_excluded_reason ON excluded_edges(exclusion_reason);
            """)

    def insert_nodes(self, nodes: List[Node]):
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO nodes (node_id, node_type, name, canonical_id, properties_json)
                VALUES (?, ?, ?, ?, ?)
            """, [
                (n.node_id, n.node_type, n.name, n.canonical_id, json.dumps(n.properties, ensure_ascii=False))
                for n in nodes
            ])

    def insert_edges(self, edges: List[Edge]):
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT OR REPLACE INTO edges (edge_id, source_node_id, target_node_id, relationship_type, confidence, weight, mention_count, mentions_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                (e.edge_id, e.source_node_id, e.target_node_id, e.relationship_type, e.confidence, e.weight, e.mention_count, json.dumps(e.mentions, ensure_ascii=False))
                for e in edges
            ])

    def insert_excluded_edges(self, excluded: List[ExcludedEdge]):
        with self._get_connection() as conn:
            conn.executemany("""
                INSERT INTO excluded_edges (source_node_id, candidate_target, relationship_type, exclusion_reason, exclusion_detail, provenance_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, [
                (x.source_node_id, x.candidate_target, x.relationship_type, x.exclusion_reason, x.exclusion_detail, json.dumps(x.provenance, ensure_ascii=False))
                for x in excluded
            ])

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        if self._in_memory_loaded and node_id in self._node_cache:
            return self._node_cache[node_id]

        with self._get_connection() as conn:
            cursor = conn.execute("SELECT * FROM nodes WHERE node_id = ?", (node_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "node_id": row["node_id"],
                "node_type": row["node_type"],
                "name": row["name"],
                "canonical_id": row["canonical_id"],
                "properties": json.loads(row["properties_json"])
            }

    def get_cited_judgments(self, judgment_node_id: str) -> List[Dict[str, Any]]:
        """Outgoing CITES edges: judgments cited by this judgment."""
        if self._in_memory_loaded:
            return self._cited_edges.get(judgment_node_id, [])

        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT e.*, n.name as target_name, n.properties_json as target_props
                FROM edges e
                JOIN nodes n ON e.target_node_id = n.node_id
                WHERE e.source_node_id = ? AND e.relationship_type = 'CITES'
            """, (judgment_node_id,))
            return [dict(r) for r in cursor.fetchall()]

    def get_citing_judgments(self, judgment_node_id: str) -> List[Dict[str, Any]]:
        """Incoming CITES edges: judgments that cite this judgment."""
        if self._in_memory_loaded:
            return self._citing_edges.get(judgment_node_id, [])

        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT e.*, n.name as source_name, n.properties_json as source_props
                FROM edges e
                JOIN nodes n ON e.source_node_id = n.node_id
                WHERE e.target_node_id = ? AND e.relationship_type = 'CITES'
            """, (judgment_node_id,))
            return [dict(r) for r in cursor.fetchall()]

    def get_provisions_mentioned(self, judgment_node_id: str) -> List[Dict[str, Any]]:
        """Provisions (Sections, Articles, Rules, Schedules) mentioned by judgment."""
        if self._in_memory_loaded:
            return self._doc_to_provisions.get(judgment_node_id, [])

        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT e.*, n.node_type as provision_type, n.name as provision_name
                FROM edges e
                JOIN nodes n ON e.target_node_id = n.node_id
                WHERE e.source_node_id = ? AND e.relationship_type = 'MENTIONS_PROVISION'
            """, (judgment_node_id,))
            return [dict(r) for r in cursor.fetchall()]

    def get_judgments_mentioning_provision(self, provision_node_id: str) -> List[str]:
        """All judgments that mention a specific provision."""
        if self._in_memory_loaded:
            return self._provision_to_docs.get(provision_node_id, [])

        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT source_node_id FROM edges
                WHERE target_node_id = ? AND relationship_type = 'MENTIONS_PROVISION'
            """, (provision_node_id,))
            return [row["source_node_id"] for row in cursor.fetchall()]

    def get_provision_df(self, provision_node_id: str) -> int:
        """Document frequency (number of distinct judgments mentioning this provision)."""
        if self._in_memory_loaded:
            return self._provision_df.get(provision_node_id, 0)

        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(DISTINCT source_node_id) FROM edges
                WHERE target_node_id = ? AND relationship_type = 'MENTIONS_PROVISION'
            """, (provision_node_id,))
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_graph_stats(self) -> Dict[str, Any]:
        with self._get_connection() as conn:
            n_total = conn.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
            n_by_type = dict(conn.execute("SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type").fetchall())

            e_total = conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
            e_by_type = dict(conn.execute("SELECT relationship_type, COUNT(*) FROM edges GROUP BY relationship_type").fetchall())

            x_total = conn.execute("SELECT COUNT(*) FROM excluded_edges").fetchone()[0]
            x_by_reason = dict(conn.execute("SELECT exclusion_reason, COUNT(*) FROM excluded_edges GROUP BY exclusion_reason").fetchall())

            return {
                "total_nodes": n_total,
                "nodes_by_type": n_by_type,
                "total_edges": e_total,
                "edges_by_type": e_by_type,
                "total_excluded_edges": x_total,
                "exclusions_by_reason": x_by_reason
            }
