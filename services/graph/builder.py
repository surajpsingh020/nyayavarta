"""
Graph Builder for NyayaVarta Knowledge Graph (Milestone 4B).

Transforms validated Milestone 4A.1 extraction JSONL outputs into a
restricted, inspectable, deterministic graph model in SQLite and JSONL formats.

Enforces all 8 Mandatory Restrictions:
1. Rejects self-citations (source_doc_id == target_doc_id).
2. Rejects resolved targets not in canonical corpus.
3. Rejects title-only matches without corroboration.
4. Rejects historical citations (< 2024) resolving to 2024 judgments.
5. Rejects Act relationships for bare sections with governing_statute=null.
6. Preserves ambiguous/unresolved mentions without converting to resolved edges.
7. Deduplicates edges using deterministic (source, target, rel) identity while preserving mention arrays.
8. Preserves underlying mention records even when an edge is excluded.
"""
import os
import json
import re
import hashlib
from datetime import datetime
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple, Set

from services.graph.models import Node, Edge, ExcludedEdge, GraphManifest
from services.graph.sqlite_store import SQLiteGraphStore

PROCESSED_DIR = "data/processed/aws_sc"
EXTRACTION_DIR = "data/processed/extraction/v1"
GRAPH_OUTPUT_DIR = "data/processed/graph/v1"

ACRONYM_TO_ACT = {
    "IPC": "Indian Penal Code, 1860",
    "CRPC": "Code of Criminal Procedure, 1973",
    "CPC": "Code of Civil Procedure, 1908",
    "PMLA": "Prevention of Money Laundering Act, 2002",
    "IBC": "Insolvency and Bankruptcy Code, 2016",
    "NI ACT": "Negotiable Instruments Act, 1881",
    "TPA": "Transfer of Property Act, 1882",
    "POCSO": "Protection of Children from Sexual Offences Act, 2012",
    "POCSO ACT": "Protection of Children from Sexual Offences Act, 2012",
    "SARFAESI": "Securitisation and Reconstruction of Financial Assets and Enforcement of Security Interest Act, 2002",
    "SARFAESI ACT": "Securitisation and Reconstruction of Financial Assets and Enforcement of Security Interest Act, 2002",
    "UAPA": "Unlawful Activities (Prevention) Act, 1967",
    "NDPS": "Narcotic Drugs and Psychotropic Substances Act, 1985",
    "NDPS ACT": "Narcotic Drugs and Psychotropic Substances Act, 1985",
    "CGST": "Central Goods and Services Tax Act, 2017",
    "CGST ACT": "Central Goods and Services Tax Act, 2017",
    "RTI": "Right to Information Act, 2005",
    "RTI ACT": "Right to Information Act, 2005",
    "EVIDENCE ACT": "Indian Evidence Act, 1872",
    "MOTOR VEHICLES ACT": "Motor Vehicles Act, 1988",
    "LAND ACQUISITION ACT": "Land Acquisition Act, 1894",
    "MMDR ACT": "Mines and Minerals (Development and Regulation) Act, 1957",
    "CONSTITUTION": "Constitution of India"
}

CANONICAL_ALIASES = {
    "indian penal code": "Indian Penal Code, 1860",
    "penal code 1860": "Indian Penal Code, 1860",
    "penal code": "Indian Penal Code, 1860",
    "indian evidence act 1872": "Indian Evidence Act, 1872",
    "evidence act 1872": "Indian Evidence Act, 1872",
    "evidence act": "Indian Evidence Act, 1872",
    "code of criminal procedure": "Code of Criminal Procedure, 1973",
    "code of civil procedure": "Code of Civil Procedure, 1908",
    "negotiable instruments act": "Negotiable Instruments Act, 1881",
    "transfer of property act": "Transfer of Property Act, 1882",
    "arbitration and conciliation act": "Arbitration and Conciliation Act, 1996",
    "limitation act": "Limitation Act, 1963",
    "land acquisition act": "Land Acquisition Act, 1894",
    "companies act": "Companies Act, 2013",
    "mmdr act 1957": "Mines and Minerals (Development and Regulation) Act, 1957"
}

PSEUDO_ACT_REGEX = re.compile(r'^(?:the|said|aforesaid|this|an|such)\s+(?:\d{4}\s+)?(?:act|code)$', re.IGNORECASE)
DISALLOWED_TERMS = {
    'fact', 'charact', 'pract', 'attract', 'prescribed', 'provision', 'because', 'owing to',
    'application to', 'filed', 'clause', 'section', 'read with', 'unlawful act', 'petition', 'under'
}


class GraphBuilder:
    VERSION = "1.1.0"

    def __init__(
        self,
        corpus_dir: str = PROCESSED_DIR,
        extraction_dir: str = EXTRACTION_DIR,
        output_dir: str = GRAPH_OUTPUT_DIR,
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

        os.makedirs(self.output_dir, exist_ok=True)
        self._load_corpus_metadata()

    def clean_and_validate_governing_act(self, raw_act: Optional[str]) -> Optional[str]:
        """
        Validates and cleans governing statute names.
        Rejects pseudo-Acts, anaphoric references, and malformed captures.
        Resolves acronyms and canonical aliases.
        Returns None if the Act name is invalid or cannot be grounded.
        """
        if not raw_act:
            return None
        cleaned = re.sub(r'\s+', ' ', raw_act).strip(' ,.-;')
        if not cleaned or len(cleaned) < 2:
            return None
        if PSEUDO_ACT_REGEX.match(cleaned):
            return None
        lower = cleaned.lower()
        if lower in {'the act', 'said act', 'the said act', 'this act', 'an act', 'act', 'the code', 'said code', 'this code', 'code'}:
            return None
        if any(t in lower for t in DISALLOWED_TERMS):
            return None
        if cleaned.count('(') != cleaned.count(')'):
            return None

        # Check acronyms (e.g. 'the CrPC' -> 'CrPC')
        test_str = cleaned
        if test_str.lower().startswith('the '):
            test_str = test_str[4:].strip()
        if test_str.upper() in ACRONYM_TO_ACT:
            return ACRONYM_TO_ACT[test_str.upper()]
        if cleaned.upper() in ACRONYM_TO_ACT:
            return ACRONYM_TO_ACT[cleaned.upper()]

        # Check canonical aliases
        norm_key = re.sub(r'[^\w\s]', '', lower).strip()
        if norm_key.startswith('the '):
            norm_key = norm_key[4:].strip()
        if norm_key in CANONICAL_ALIASES:
            return CANONICAL_ALIASES[norm_key]

        # Strip leading 'The ' on formal Acts (e.g. 'The Advocates Act, 1961' -> 'Advocates Act, 1961')
        if cleaned.lower().startswith('the ') and ('act' in lower or 'code' in lower):
            return cleaned[4:].strip()

        return cleaned

    def _normalize_key(self, text: str) -> str:
        """Create a deterministic alphanumeric identifier."""
        clean = re.sub(r'[^\w\s]', '', text.lower())
        return re.sub(r'\s+', '_', clean.strip())

    def _load_corpus_metadata(self):
        """Load all canonical judgment metadata to populate Judgment nodes."""
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
                    "header_citations": []  # Stores self-citations as properties
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
        # Validate character spans
        start_char = mention_payload.get("start_char")
        end_char = mention_payload.get("end_char")
        if start_char is not None and end_char is not None:
            if start_char < 0 or end_char < start_char:
                raise ValueError(f"Invalid character span: start={start_char}, end={end_char}")

        # Validate that mention source agrees with edge source
        if source_id.startswith("doc:"):
            expected_src = source_id.replace("doc:", "")
            m_src = mention_payload.get("source_doc_id")
            if m_src and m_src != expected_src:
                raise ValueError(f"Mention source '{m_src}' disagrees with edge source '{expected_src}'")

        edge_id = Edge.generate_edge_id(source_id, target_id, rel_type)
        if edge_id in self.edges:
            edge = self.edges[edge_id]
            edge.mention_count += 1
            edge.mentions.append(mention_payload)
            # Update confidence if higher
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
        """Process case_citations.jsonl and resolved_entities.jsonl applying Restrictions 1-4, 6, 7."""
        cites_path = os.path.join(self.extraction_dir, "case_citations.jsonl")
        res_path = os.path.join(self.extraction_dir, "resolved_entities.jsonl")

        if not os.path.exists(cites_path) or not os.path.exists(res_path):
            print(f"Extraction files not found in {self.extraction_dir}")
            return

        # Explicit count verification before processing
        with open(cites_path, "r", encoding="utf-8") as f_c:
            c_count = sum(1 for _ in f_c)
        with open(res_path, "r", encoding="utf-8") as f_r:
            r_count = sum(1 for _ in f_r)

        if c_count != r_count:
            raise ValueError(
                f"Extraction record count mismatch: case_citations.jsonl has {c_count} lines, "
                f"while resolved_entities.jsonl has {r_count} lines. Aborting graph build."
            )

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
                components = c.get("components", {})
                cite_year = components.get("year")

                mention_payload = {
                    "source_doc_id": source_doc_id,
                    "citation_type": c_type,
                    "raw_text": raw_text,
                    "normalized_citation": norm_cite,
                    "start_char": c.get("start_char"),
                    "end_char": c.get("end_char"),
                    "extraction_method": c.get("extraction_method"),
                    "match_method": match_method,
                    "treatment_signal": c.get("treatment_signal"),
                    "provenance": c.get("provenance", "AWS Open Data")
                }

                # Restriction 1: Reject Self-Citations
                if is_self or (target_doc_id and target_doc_id == source_doc_id):
                    self.excluded_edges.append(ExcludedEdge(
                        source_node_id=source_node_id,
                        candidate_target=norm_cite or raw_text,
                        relationship_type="CITES",
                        exclusion_reason="SELF_CITATION",
                        exclusion_detail="Source document cites its own introductory header citation or case title.",
                        provenance=mention_payload
                    ))
                    # Store as node property on Judgment node
                    if source_node_id in self.nodes:
                        self.nodes[source_node_id].properties["header_citations"].append(norm_cite or raw_text)
                    continue

                # Restriction 6: Ambiguous Mentions
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

                # Restriction 4 & 6: Unresolved Mentions / Historical Precedents
                if status == "unresolved" or not target_doc_id:
                    if match_method == "historical_reporter_pre_2024" or (cite_year and cite_year < 2024):
                        reason = "HISTORICAL_PRE_2024"
                        detail = f"Precedent from year {cite_year or 'pre-2024'} outside 2024 corpus."
                    else:
                        reason = "UNRESOLVED_MENTION"
                        detail = f"Unresolved mention via method '{match_method}'."

                    self.excluded_edges.append(ExcludedEdge(
                        source_node_id=source_node_id,
                        candidate_target=norm_cite or raw_text,
                        relationship_type="CITES",
                        exclusion_reason=reason,
                        exclusion_detail=detail,
                        provenance=mention_payload
                    ))

                    # Optional: create explicitly labeled external unverified stub node
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

                # Restriction 2: Reject Target Not in Canonical Corpus
                if target_doc_id not in self.corpus_doc_ids:
                    self.excluded_edges.append(ExcludedEdge(
                        source_node_id=source_node_id,
                        candidate_target=target_doc_id,
                        relationship_type="CITES",
                        exclusion_reason="TARGET_NOT_IN_CORPUS",
                        exclusion_detail=f"Target doc ID {target_doc_id} not in canonical 782 corpus.",
                        provenance=mention_payload
                    ))
                    continue

                # Restriction 3 & 4: Corroboration Guardrail for Title Matches
                if match_method in ["title_keyword_overlap", "unanchored_unique_keyword_match"]:
                    # Must have year >= 2024 or exact neutral corroboration
                    if cite_year and cite_year < 2024:
                        self.excluded_edges.append(ExcludedEdge(
                            source_node_id=source_node_id,
                            candidate_target=target_doc_id,
                            relationship_type="CITES",
                            exclusion_reason="HISTORICAL_PRE_2024",
                            exclusion_detail=f"Title matched but citation year {cite_year} is historical pre-2024.",
                            provenance=mention_payload
                        ))
                        continue

                    # If no year is present, verify title overlap confidence score >= 0.85
                    conf_score = r.get("confidence_score", 0.0)
                    if conf_score < 0.85:
                        self.excluded_edges.append(ExcludedEdge(
                            source_node_id=source_node_id,
                            candidate_target=target_doc_id,
                            relationship_type="CITES",
                            exclusion_reason="TITLE_ONLY_UNCORROBORATED",
                            exclusion_detail=f"Title match confidence score {conf_score} < 0.85 without year corroboration.",
                            provenance=mention_payload
                        ))
                        continue

                # Valid Cross-Document CITES Edge
                target_node_id = f"doc:{target_doc_id}"
                confidence = "high" if match_method == "exact_neutral_citation" else "medium"
                self._add_or_update_edge(
                    source_id=source_node_id,
                    target_id=target_node_id,
                    rel_type="CITES",
                    confidence=confidence,
                    mention_payload=mention_payload
                )

    def process_statutes(self):
        """Process statutory_references.jsonl applying Restriction 5."""
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

                mention_payload = {
                    "source_doc_id": source_doc_id,
                    "reference_type": ref_type,
                    "raw_text": raw_text,
                    "normalized_reference": norm_ref,
                    "start_char": rec.get("start_char"),
                    "end_char": rec.get("end_char"),
                    "extraction_method": rec.get("extraction_method"),
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
                            # Link Article -> Act
                            self._add_or_update_edge(
                                source_id=art_node_id,
                                target_id=const_act_id,
                                rel_type="PART_OF_ACT",
                                confidence="high",
                                mention_payload=mention_payload
                            )

                        # Link Judgment -> Article
                        self._add_or_update_edge(
                            source_id=source_node_id,
                            target_id=art_node_id,
                            rel_type="MENTIONS_PROVISION",
                            confidence=confidence,
                            mention_payload=mention_payload
                        )

                # 2. Procedural Order / Rule
                elif ref_type == "procedural_order_rule":
                    order = components.get("order")
                    rule = components.get("rule") or components.get("standalone_rule")
                    rule_node_id = f"rule:{self._normalize_key(norm_ref)}"
                    if rule_node_id not in self.nodes:
                        self.nodes[rule_node_id] = Node(
                            node_id=rule_node_id,
                            node_type="Rule",
                            name=norm_ref,
                            canonical_id=norm_ref,
                            properties={"order": order, "rule": rule}
                        )

                    self._add_or_update_edge(
                        source_id=source_node_id,
                        target_id=rule_node_id,
                        rel_type="MENTIONS_PROVISION",
                        confidence=confidence,
                        mention_payload=mention_payload
                    )

                # 3. Constitutional / Statutory Schedule
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

                # 4. Formal Act
                # 4. Formal Act
                elif ref_type == "statute_act":
                    raw_act_name = components.get("canonical_title") or norm_ref
                    act_name = self.clean_and_validate_governing_act(raw_act_name)
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

                # 5. Statutory Section
                elif ref_type == "statutory_section":
                    sec_nums = components.get("section_numbers", "")
                    raw_gov = components.get("governing_statute")
                    governing_act = self.clean_and_validate_governing_act(raw_gov)

                    # Restriction 5: Bare Section with governing_statute=null
                    if not governing_act:
                        sec_node_id = f"section:unspecified:{self._normalize_key(sec_nums)}"
                        if sec_node_id not in self.nodes:
                            self.nodes[sec_node_id] = Node(
                                node_id=sec_node_id,
                                node_type="Section",
                                name=f"Section {sec_nums} (Unspecified Act)",
                                canonical_id=None,
                                properties={"section_numbers": sec_nums, "governing_statute": None}
                            )

                        # Link Judgment -> Bare Section
                        self._add_or_update_edge(
                            source_id=source_node_id,
                            target_id=sec_node_id,
                            rel_type="MENTIONS_PROVISION",
                            confidence="medium",
                            mention_payload=mention_payload
                        )

                        # Log excluded Act relationship
                        self.excluded_edges.append(ExcludedEdge(
                            source_node_id=sec_node_id,
                            candidate_target="UNSPECIFIED_ACT",
                            relationship_type="PART_OF_ACT",
                            exclusion_reason="BARE_SECTION_UNSPECIFIED_ACT",
                            exclusion_detail=f"Section '{sec_nums}' mentioned without identifiable governing Act in token/sentence.",
                            provenance=mention_payload
                        ))
                    else:
                        # Grounded Section with validated governing statute
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
                                properties={"section_numbers": sec_nums, "governing_statute": governing_act}
                            )
                            # Link Section -> Act
                            self._add_or_update_edge(
                                source_id=sec_node_id,
                                target_id=act_node_id,
                                rel_type="PART_OF_ACT",
                                confidence="high",
                                mention_payload=mention_payload
                            )

                        # Link Judgment -> Section
                        self._add_or_update_edge(
                            source_id=source_node_id,
                            target_id=sec_node_id,
                            rel_type="MENTIONS_PROVISION",
                            confidence="high",
                            mention_payload=mention_payload
                        )

    def export(self, timestamp: Optional[str] = None) -> GraphManifest:
        """Export nodes, edges, and exclusions to JSONL and SQLite; compute SHA256 hashes."""
        nodes_file = os.path.join(self.output_dir, "nodes.jsonl")
        edges_file = os.path.join(self.output_dir, "edges.jsonl")
        excluded_file = os.path.join(self.output_dir, "excluded_edges.jsonl")
        db_file = os.path.join(self.output_dir, "graph.db")
        manifest_file = os.path.join(self.output_dir, "graph_manifest.json")

        # 1. Deterministic JSONL Export (sorted by primary key)
        sorted_nodes = sorted(self.nodes.values(), key=lambda n: n.node_id)
        sorted_edges = sorted(self.edges.values(), key=lambda e: e.edge_id)
        sorted_excluded = sorted(self.excluded_edges, key=lambda x: (x.source_node_id, x.exclusion_reason, x.candidate_target))

        with open(nodes_file, "w", encoding="utf-8") as f:
            for n in sorted_nodes:
                f.write(json.dumps(n.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

        with open(edges_file, "w", encoding="utf-8") as f:
            for e in sorted_edges:
                f.write(json.dumps(e.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

        with open(excluded_file, "w", encoding="utf-8") as f:
            for x in sorted_excluded:
                f.write(json.dumps(x.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")

        # 2. SQLite Export (ensure fresh database without stale rows from previous builds)
        if os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass
        store = SQLiteGraphStore(db_path=db_file)
        store.insert_nodes(sorted_nodes)
        store.insert_edges(sorted_edges)
        store.insert_excluded_edges(sorted_excluded)

        # 3. Compute Checksums
        def get_sha256(path):
            h = hashlib.sha256()
            with open(path, "rb") as fp:
                while chunk := fp.read(65536):
                    h.update(chunk)
            return h.hexdigest()

        checksums = {
            "nodes.jsonl": get_sha256(nodes_file),
            "edges.jsonl": get_sha256(edges_file),
            "excluded_edges.jsonl": get_sha256(excluded_file),
            "graph.db": get_sha256(db_file)
        }

        # 4. Compile Manifest
        nodes_by_type = defaultdict(int)
        for n in sorted_nodes:
            nodes_by_type[n.node_type] += 1

        edges_by_type = defaultdict(int)
        for e in sorted_edges:
            edges_by_type[e.relationship_type] += 1

        exclusions_by_reason = defaultdict(int)
        for x in sorted_excluded:
            exclusions_by_reason[x.exclusion_reason] += 1

        ext_count = nodes_by_type.get("ExternalReference", 0)

        manifest = GraphManifest(
            manifest_version=self.VERSION,
            graph_version="v1",
            created_at=timestamp or datetime.now().isoformat(),
            nodes_count=len(sorted_nodes),
            nodes_by_type=dict(nodes_by_type),
            edges_count=len(sorted_edges),
            edges_by_type=dict(edges_by_type),
            excluded_edges_count=len(sorted_excluded),
            exclusions_by_reason=dict(exclusions_by_reason),
            unresolved_external_references_count=ext_count,
            sha256_checksums=checksums,
            export_files={
                "nodes": nodes_file,
                "edges": edges_file,
                "excluded_edges": excluded_file,
                "sqlite_db": db_file
            }
        )

        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=4, sort_keys=True)

        return manifest

    def build(self, timestamp: Optional[str] = None) -> GraphManifest:
        print(f"Building restricted graph from {len(self.corpus_doc_ids)} canonical judgments...")
        self.process_citations()
        print(f"Processed citations: {len(self.edges)} edges created, {len(self.excluded_edges)} excluded so far.")
        self.process_statutes()
        print(f"Processed statutes: {len(self.edges)} total edges, {len(self.nodes)} total nodes.")
        manifest = self.export(timestamp=timestamp)
        print("Graph export complete.")
        return manifest
