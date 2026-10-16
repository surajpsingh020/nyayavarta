"""
Graph Builder V2 for NyayaVarta Knowledge Graph (Milestone 11 Task 5).

Builds an isolated, verified legal knowledge graph in data/processed/graph/v2/
using extraction v2 artifacts.

Enforces:
1. Zero self-loop CITES edges.
2. Verified canonical targets: all internal CITES edges must target an existing 2024 judgment.
3. Pure observational treatment signals: preserves treatment_signal in mention metadata
   without synthesizing authoritative precedent-validity labels (no 'good_law', 'overruled').
4. Conservative statutory grounding:
   - Links Section -> Act via PART_OF_ACT ONLY when attribution_type is 'explicit' or 'inherited'.
   - Sections with attribution_type 'ambiguous' or 'unresolved' are preserved without PART_OF_ACT edges.
5. Deterministic edge deduplication while preserving all mention provenance.
6. Clearly separated ExternalReference stubs for historical citations.
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))
import json
import re
from collections import defaultdict
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set

from services.graph.models import Node, Edge, ExcludedEdge, GraphManifest
from services.graph.sqlite_store import SQLiteGraphStore
from services.extraction.statute_resolver_v2 import StatuteResolverV2

PROCESSED_DIR = "data/processed/aws_sc"
EXTRACTION_DIR_V2 = "data/processed/extraction/v2"
GRAPH_OUTPUT_DIR_V2 = "data/processed/graph/v2"


class GraphBuilderV2:
    VERSION = "2.0.0"

    def __init__(
        self,
        corpus_dir: str = PROCESSED_DIR,
        extraction_dir: str = EXTRACTION_DIR_V2,
        output_dir: str = GRAPH_OUTPUT_DIR_V2,
        include_external_stubs: bool = True
    ):
        self.corpus_dir = corpus_dir
        self.extraction_dir = extraction_dir
        self.output_dir = output_dir
        self.include_external_stubs = include_external_stubs

        self.nodes: Dict[str, Node] = {}
        self.edges: Dict[str, Edge] = {}
        self.excluded_edges: List[ExcludedEdge] = []
        self.corpus_doc_ids: Set[str] = set()

        self.statute_resolver = StatuteResolverV2()

        os.makedirs(self.output_dir, exist_ok=True)
        self._load_corpus_metadata()

    def _normalize_key(self, text: str) -> str:
        clean = re.sub(r'[^\w\s]', '', text.lower())
        return re.sub(r'\s+', '_', clean.strip())

    def _load_corpus_metadata(self):
        """Index all canonical judgment metadata to populate Judgment nodes."""
        if not os.path.exists(self.corpus_dir):
            return

        for fname in os.listdir(self.corpus_dir):
            if not fname.endswith('.json'):
                continue
            doc_id = fname[:-5]
            self.corpus_doc_ids.add(doc_id)

            fpath = os.path.join(self.corpus_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                doc = json.load(f)

            node_id = f"doc:{doc_id}"
            title = doc.get("case_title", doc_id)
            self.nodes[node_id] = Node(
                node_id=node_id,
                node_type="Judgment",
                name=title,
                canonical_id=doc_id,
                properties={
                    "document_id": doc_id,
                    "case_title": title,
                    "case_number": doc.get("case_number"),
                    "citation": doc.get("citation"),
                    "decision_date": doc.get("decision_date"),
                    "judges": doc.get("judges"),
                    "header_citations": []
                }
            )

    def _add_or_update_edge(
        self,
        source_id: str,
        target_id: str,
        rel_type: str,
        confidence: str,
        mention_payload: Dict[str, Any]
    ):
        edge_id = Edge.generate_edge_id(source_id, target_id, rel_type)
        if edge_id in self.edges:
            edge = self.edges[edge_id]
            edge.mention_count += 1
            edge.mentions.append(mention_payload)
            if confidence == "high":
                edge.confidence = "high"
        else:
            self.edges[edge_id] = Edge(
                edge_id=edge_id,
                source_node_id=source_id,
                target_node_id=target_id,
                relationship_type=rel_type,
                confidence=confidence,
                weight=1.0,
                mention_count=1,
                mentions=[mention_payload]
            )

    def process_citations(self):
        """Process extraction v2 citations and resolutions."""
        cites_path = os.path.join(self.extraction_dir, "case_citations.jsonl")
        res_path = os.path.join(self.extraction_dir, "resolved_entities.jsonl")

        if not os.path.exists(cites_path) or not os.path.exists(res_path):
            print(f"Extraction v2 files not found in {self.extraction_dir}")
            return

        with open(cites_path, "r", encoding="utf-8") as f_c, open(res_path, "r", encoding="utf-8") as f_r:
            for line_c, line_r in zip(f_c, f_r):
                c = json.loads(line_c)
                r = json.loads(line_r)

                source_doc_id = c["source_doc_id"]
                source_node_id = f"doc:{source_doc_id}"
                raw_text = c.get("raw_text", "")
                norm_cite = c.get("normalized_citation", "")
                c_type = c.get("citation_type", "")
                status = r.get("resolution_status", "unresolved")
                target_doc_id = r.get("resolved_document_id")
                is_self = r.get("is_self_citation", False)
                match_method = r.get("match_method", "")
                treatment = c.get("treatment_signal")

                mention_payload = {
                    "source_doc_id": source_doc_id,
                    "citation_type": c_type,
                    "raw_text": raw_text,
                    "normalized_citation": norm_cite,
                    "start_char": c.get("start_char"),
                    "end_char": c.get("end_char"),
                    "extraction_method": c.get("extraction_method"),
                    "match_method": match_method,
                    "treatment_signal": treatment,
                    "resolution_reason": r.get("resolution_reason"),
                    "provenance": c.get("provenance", "AWS Open Data")
                }

                # 1. Reject Self-Citations from Graph Edges
                if is_self or (target_doc_id and target_doc_id == source_doc_id):
                    self.excluded_edges.append(ExcludedEdge(
                        source_node_id=source_node_id,
                        candidate_target=norm_cite or raw_text,
                        relationship_type="CITES",
                        exclusion_reason="SELF_CITATION",
                        exclusion_detail="Source judgment cites its own title or header citation.",
                        provenance=mention_payload
                    ))
                    if source_node_id in self.nodes:
                        self.nodes[source_node_id].properties["header_citations"].append(norm_cite or raw_text)
                    continue

                # 2. Ambiguous Mentions
                if status == "ambiguous":
                    candidates = r.get("ambiguous_candidate_ids", [])
                    self.excluded_edges.append(ExcludedEdge(
                        source_node_id=source_node_id,
                        candidate_target=norm_cite or raw_text,
                        relationship_type="CITES",
                        exclusion_reason="AMBIGUOUS_CANDIDATE",
                        exclusion_detail=f"Mention matches {len(candidates)} tied candidates: {candidates}",
                        provenance=mention_payload
                    ))
                    continue

                # 3. Unresolved Mentions / Historical Precedents
                if status == "unresolved" or not target_doc_id:
                    reason = "HISTORICAL_PRE_2024" if "pre_2024" in match_method else "UNRESOLVED_MENTION"
                    self.excluded_edges.append(ExcludedEdge(
                        source_node_id=source_node_id,
                        candidate_target=norm_cite or raw_text,
                        relationship_type="CITES",
                        exclusion_reason=reason,
                        exclusion_detail=r.get("resolution_reason", f"Unresolved via {match_method}"),
                        provenance=mention_payload
                    ))

                    # External reference stub
                    if self.include_external_stubs and norm_cite:
                        stub_id = f"ext:historical:{self._normalize_key(norm_cite)}"
                        if stub_id not in self.nodes:
                            self.nodes[stub_id] = Node(
                                node_id=stub_id,
                                node_type="ExternalReference",
                                name=norm_cite,
                                canonical_id=None,
                                properties={
                                    "raw_text": raw_text,
                                    "citation_type": c_type,
                                    "verified": False,
                                    "external_source": "Unverified Historical Reference"
                                }
                            )
                        self._add_or_update_edge(
                            source_id=source_node_id,
                            target_id=stub_id,
                            rel_type="CITES_EXTERNAL",
                            confidence="low",
                            mention_payload=mention_payload
                        )
                    continue

                # 4. Target Corpus Validation
                if target_doc_id not in self.corpus_doc_ids:
                    self.excluded_edges.append(ExcludedEdge(
                        source_node_id=source_node_id,
                        candidate_target=target_doc_id,
                        relationship_type="CITES",
                        exclusion_reason="TARGET_NOT_IN_CORPUS",
                        exclusion_detail=f"Target {target_doc_id} not in canonical 782 corpus.",
                        provenance=mention_payload
                    ))
                    continue

                # 5. Valid Cross-Document CITES Edge
                target_node_id = f"doc:{target_doc_id}"
                self._add_or_update_edge(
                    source_id=source_node_id,
                    target_id=target_node_id,
                    rel_type="CITES",
                    confidence="high",
                    mention_payload=mention_payload
                )

    def process_statutes(self):
        """Process statutory_references.jsonl with conservative inheritance."""
        stat_path = os.path.join(self.extraction_dir, "statutory_references.jsonl")
        if not os.path.exists(stat_path):
            return

        with open(stat_path, "r", encoding="utf-8") as f:
            for line in f:
                rec = json.loads(line)
                source_doc_id = rec["source_doc_id"]
                source_node_id = f"doc:{source_doc_id}"
                ref_type = rec.get("reference_type")
                raw_text = rec.get("raw_text", "")
                norm_ref = rec.get("normalized_reference", "")
                components = rec.get("components", {})
                confidence = rec.get("confidence", "high")
                attribution_type = rec.get("attribution_type", "explicit")
                attribution_source = rec.get("attribution_source", "")

                mention_payload = {
                    "source_doc_id": source_doc_id,
                    "reference_type": ref_type,
                    "raw_text": raw_text,
                    "normalized_reference": norm_ref,
                    "start_char": rec.get("start_char"),
                    "end_char": rec.get("end_char"),
                    "extraction_method": rec.get("extraction_method"),
                    "attribution_type": attribution_type,
                    "attribution_source": attribution_source,
                    "provenance": rec.get("provenance", "AWS Open Data")
                }

                # 1. Constitutional Article
                if ref_type == "constitutional_article":
                    articles = components.get("articles", [])
                    const_act_id = "act:constitution_of_india"
                    if const_act_id not in self.nodes:
                        self.nodes[const_act_id] = Node(
                            node_id=const_act_id,
                            node_type="Act",
                            name="Constitution of India",
                            canonical_id="Constitution of India",
                            properties={"enactment_year": 1950}
                        )

                    for art in articles:
                        art_node_id = f"article:constitution:{self._normalize_key(art)}"
                        if art_node_id not in self.nodes:
                            self.nodes[art_node_id] = Node(
                                node_id=art_node_id,
                                node_type="Article",
                                name=f"Article {art} of the Constitution",
                                canonical_id=f"Article {art}",
                                properties={"article_number": art, "governing_act": "Constitution of India"}
                            )
                            self._add_or_update_edge(
                                source_id=art_node_id,
                                target_id=const_act_id,
                                rel_type="PART_OF_ACT",
                                confidence="high",
                                mention_payload=mention_payload
                            )

                        self._add_or_update_edge(
                            source_id=source_node_id,
                            target_id=art_node_id,
                            rel_type="MENTIONS_PROVISION",
                            confidence=confidence,
                            mention_payload=mention_payload
                        )

                # 2. Formal Act
                elif ref_type == "statute_act":
                    raw_act_name = components.get("canonical_title") or norm_ref
                    act_name = self.statute_resolver.clean_and_validate_act(raw_act_name)
                    if not act_name:
                        continue
                    act_node_id = f"act:{self._normalize_key(act_name)}"
                    if act_node_id not in self.nodes:
                        self.nodes[act_node_id] = Node(
                            node_id=act_node_id,
                            node_type="Act",
                            name=act_name,
                            canonical_id=act_name,
                            properties={"year": components.get("year")}
                        )

                    self._add_or_update_edge(
                        source_id=source_node_id,
                        target_id=act_node_id,
                        rel_type="MENTIONS_PROVISION",
                        confidence=confidence,
                        mention_payload=mention_payload
                    )

                # 3. Procedural Order / Rule
                elif ref_type == "procedural_order_rule":
                    rule_node_id = f"rule:{self._normalize_key(norm_ref)}"
                    if rule_node_id not in self.nodes:
                        self.nodes[rule_node_id] = Node(
                            node_id=rule_node_id,
                            node_type="Rule",
                            name=norm_ref,
                            canonical_id=norm_ref,
                            properties={"components": components}
                        )

                    self._add_or_update_edge(
                        source_id=source_node_id,
                        target_id=rule_node_id,
                        rel_type="MENTIONS_PROVISION",
                        confidence=confidence,
                        mention_payload=mention_payload
                    )

                # 4. Schedule
                elif ref_type == "statutory_schedule":
                    sched_node_id = f"schedule:{self._normalize_key(norm_ref)}"
                    if sched_node_id not in self.nodes:
                        self.nodes[sched_node_id] = Node(
                            node_id=sched_node_id,
                            node_type="Schedule",
                            name=norm_ref,
                            canonical_id=norm_ref,
                            properties={"schedule_name": norm_ref}
                        )

                    self._add_or_update_edge(
                        source_id=source_node_id,
                        target_id=sched_node_id,
                        rel_type="MENTIONS_PROVISION",
                        confidence=confidence,
                        mention_payload=mention_payload
                    )

                # 5. Statutory Section
                elif ref_type == "statutory_section":
                    sec_nums = components.get("section_numbers", "")
                    governing_act = components.get("governing_statute")

                    if not governing_act or attribution_type in ["ambiguous", "unresolved"]:
                        # Bare or ambiguous section
                        sec_node_id = f"section:unspecified:{self._normalize_key(sec_nums)}"
                        if sec_node_id not in self.nodes:
                            self.nodes[sec_node_id] = Node(
                                node_id=sec_node_id,
                                node_type="Section",
                                name=f"Section {sec_nums} (Unspecified Act)",
                                canonical_id=None,
                                properties={"section_numbers": sec_nums, "governing_statute": None}
                            )

                        self._add_or_update_edge(
                            source_id=source_node_id,
                            target_id=sec_node_id,
                            rel_type="MENTIONS_PROVISION",
                            confidence="medium",
                            mention_payload=mention_payload
                        )

                        reason = "AMBIGUOUS_STATUTORY_CONTEXT" if attribution_type == "ambiguous" else "BARE_SECTION_UNSPECIFIED_ACT"
                        self.excluded_edges.append(ExcludedEdge(
                            source_node_id=sec_node_id,
                            candidate_target="UNSPECIFIED_ACT",
                            relationship_type="PART_OF_ACT",
                            exclusion_reason=reason,
                            exclusion_detail=f"Section '{sec_nums}' attribution is {attribution_type} ({attribution_source}).",
                            provenance=mention_payload
                        ))
                    else:
                        # Grounded Section with validated explicit or inherited governing statute
                        act_node_id = f"act:{self._normalize_key(governing_act)}"
                        if act_node_id not in self.nodes:
                            self.nodes[act_node_id] = Node(
                                node_id=act_node_id,
                                node_type="Act",
                                name=governing_act,
                                canonical_id=governing_act,
                                properties={}
                            )

                        sec_node_id = f"section:{self._normalize_key(governing_act)}:{self._normalize_key(sec_nums)}"
                        if sec_node_id not in self.nodes:
                            self.nodes[sec_node_id] = Node(
                                node_id=sec_node_id,
                                node_type="Section",
                                name=f"Section {sec_nums} of {governing_act}",
                                canonical_id=f"Section {sec_nums}",
                                properties={
                                    "section_numbers": sec_nums,
                                    "governing_statute": governing_act,
                                    "attribution_type": attribution_type
                                }
                            )

                            self._add_or_update_edge(
                                source_id=sec_node_id,
                                target_id=act_node_id,
                                rel_type="PART_OF_ACT",
                                confidence="high",
                                mention_payload=mention_payload
                            )

                        self._add_or_update_edge(
                            source_id=source_node_id,
                            target_id=sec_node_id,
                            rel_type="MENTIONS_PROVISION",
                            confidence=confidence,
                            mention_payload=mention_payload
                        )

    def build_and_export(self):
        """Run graph compilation, populate SQLite DB and export JSONL files."""
        print("=== Building Graph V2 ===")
        self.process_citations()
        print(f"Processed citations. Nodes: {len(self.nodes)}, Edges: {len(self.edges)}, Exclusions: {len(self.excluded_edges)}")
        self.process_statutes()
        print(f"Processed statutes. Total Nodes: {len(self.nodes)}, Total Edges: {len(self.edges)}, Total Exclusions: {len(self.excluded_edges)}")

        # 1. Export SQLite
        db_path = os.path.join(self.output_dir, "graph.db")
        if os.path.exists(db_path):
            os.remove(db_path)
        store = SQLiteGraphStore(db_path=db_path)

        store.insert_nodes(list(self.nodes.values()))
        store.insert_edges(list(self.edges.values()))
        store.insert_excluded_edges(self.excluded_edges)

        # 2. Export JSONL
        nodes_file = os.path.join(self.output_dir, "nodes.jsonl")
        edges_file = os.path.join(self.output_dir, "edges.jsonl")
        excl_file = os.path.join(self.output_dir, "excluded_edges.jsonl")

        with open(nodes_file, "w", encoding="utf-8") as f:
            for n in self.nodes.values():
                f.write(json.dumps(n.to_dict(), ensure_ascii=False) + "\n")

        with open(edges_file, "w", encoding="utf-8") as f:
            for e in self.edges.values():
                f.write(json.dumps(e.to_dict(), ensure_ascii=False) + "\n")

        with open(excl_file, "w", encoding="utf-8") as f:
            for x in self.excluded_edges:
                f.write(json.dumps(x.to_dict(), ensure_ascii=False) + "\n")

        # 3. Export Manifest
        node_counts = defaultdict(int)
        for n in self.nodes.values():
            node_counts[n.node_type] += 1

        edge_counts = defaultdict(int)
        for e in self.edges.values():
            edge_counts[e.relationship_type] += 1

        excl_counts = defaultdict(int)
        for x in self.excluded_edges:
            excl_counts[x.exclusion_reason] += 1

        manifest = {
            "graph_version": self.VERSION,
            "created_at": datetime.now().isoformat(),
            "nodes_count": len(self.nodes),
            "edges_count": len(self.edges),
            "excluded_edges_count": len(self.excluded_edges),
            "node_type_breakdown": dict(node_counts),
            "edge_type_breakdown": dict(edge_counts),
            "exclusion_reason_breakdown": dict(excl_counts),
            "output_directory": self.output_dir
        }

        manifest_file = os.path.join(self.output_dir, "graph_manifest.json")
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=4)

        print(f"Graph V2 built successfully in {self.output_dir}!")
        print(f"Nodes: {dict(node_counts)}")
        print(f"Edges: {dict(edge_counts)}")
        print(f"Exclusions: {dict(excl_counts)}")
        return manifest


if __name__ == "__main__":
    builder = GraphBuilderV2()
    builder.build_and_export()
