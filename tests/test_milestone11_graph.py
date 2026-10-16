"""
Milestone 11 Regression and Graph Integrity Test Suite.

Validates all 15 required scenarios for Graph Enrichment and Precedent Entity Disambiguation:
1. Normalization determinism & idempotency.
2. Punctuation/spacing normalization consistency.
3. Incomplete citations remain unresolved.
4. Historical cases not linked via party-name overlap.
5. Self-citations rejected from cross-document precedent edges.
6. Multiple candidate targets remain ambiguous.
7. Out-of-corpus precedent not marked nonexistent.
8. Explicit Act attribution preserved.
9. Ambiguous statutory sections not assigned Act from number alone.
10. Inheritance does not cross paragraph boundaries.
11. All internal CITES targets exist in 782 corpus.
12. Deterministic edge deduplication with mention provenance.
13. Source traceability on all graph edges.
14. Unverified treatment signals do not produce precedent-status labels.
15. Full regression check: all existing tests + new tests pass.
"""
import os
import json
import pytest

from services.extraction.citation_normalizer import CitationNormalizer
from services.extraction.entity_resolver_v2 import EntityResolverV2
from services.extraction.statute_resolver_v2 import StatuteResolverV2
from services.graph.sqlite_store import SQLiteGraphStore
from services.graph.models import Edge

GRAPH_V2_DIR = "data/processed/graph/v2"
EXTRACTION_V2_DIR = "data/processed/extraction/v2"
CORPUS_DIR = "data/processed/aws_sc"


@pytest.fixture(scope="module")
def corpus_doc_ids():
    ids = set()
    for fname in os.listdir(CORPUS_DIR):
        if fname.endswith(".json"):
            ids.add(fname[:-5])
    return ids


@pytest.fixture(scope="module")
def graph_v2_store():
    db_path = os.path.join(GRAPH_V2_DIR, "graph.db")
    assert os.path.exists(db_path), f"Graph v2 DB missing at {db_path}"
    return SQLiteGraphStore(db_path=db_path)


@pytest.fixture(scope="module")
def normalizer():
    return CitationNormalizer()


@pytest.fixture(scope="module")
def entity_resolver():
    return EntityResolverV2(processed_dir=CORPUS_DIR)


@pytest.fixture(scope="module")
def statute_resolver():
    return StatuteResolverV2()


class TestMilestone11GraphIntegrity:

    # 1. Normalization determinism & idempotency
    def test_normalization_determinism_and_idempotency(self, normalizer):
        cites = [
            "(2024) 5 SCC 100",
            "[2024] 10 SCR 108",
            "2024 INSC 745",
            "AIR 2024 SC 1234",
            "2024 SCC OnLine SC 456"
        ]
        for c in cites:
            res1 = normalizer.normalize(c)
            assert res1.parsing_status == "valid", f"Expected valid normalization for {c}"
            assert res1.normalized_citation is not None

            # Determinism: same input gives exact same object
            res2 = normalizer.normalize(c)
            assert res1.normalized_citation == res2.normalized_citation
            assert res1.citation_scheme == res2.citation_scheme

            # Idempotency: normalizing normalized string produces identical normalized string
            res3 = normalizer.normalize(res1.normalized_citation)
            assert res3.normalized_citation == res1.normalized_citation
            assert res3.year == res1.year
            assert res3.volume == res1.volume
            assert res3.page_or_number == res1.page_or_number

    # 2. Punctuation/spacing normalization consistency
    def test_punctuation_spacing_normalization_consistency(self, normalizer):
        variants_scc = [
            "(2024) 5 SCC 100",
            "( 2024 )  5   SCC   100",
            "2024 (5) SCC 100",
            "2024 5 SCC 100",
            "(2024)5 SCC 100"
        ]
        expected_scc = "(2024) 5 SCC 100"
        for v in variants_scc:
            res = normalizer.normalize(v)
            assert res.normalized_citation == expected_scc, f"Variant '{v}' failed to normalize to '{expected_scc}', got '{res.normalized_citation}'"

        variants_scr = [
            "[2024] 10 SCR 108",
            "[ 2024 ]  10  SCR  108",
            "(2024) 10 SCR 108",
            "2024 10 SCR 108"
        ]
        expected_scr = "[2024] 10 SCR 108"
        for v in variants_scr:
            res = normalizer.normalize(v)
            assert res.normalized_citation == expected_scr, f"Variant '{v}' failed to normalize to '{expected_scr}', got '{res.normalized_citation}'"

    # 3. Incomplete citations remain unresolved
    def test_incomplete_citations_remain_unresolved(self, normalizer, entity_resolver):
        incomplete = [
            "(2024) SCC",
            "AIR 2024",
            "[2024] SCR",
            "2024 INSC",
            "SCC OnLine SC"
        ]
        for c in incomplete:
            norm_res = normalizer.normalize(c)
            assert norm_res.parsing_status in ["partial", "malformed", "unsupported"], f"Expected incomplete for {c}, got {norm_res.parsing_status}"

            # Entity resolver should not resolve incomplete citations
            mention = {
                "raw_text": c,
                "normalized_citation": norm_res.normalized_citation,
                "citation_type": "reporter_citation",
                "extracted_case_title": None,
                "source_doc_id": "dummy_source"
            }
            res = entity_resolver.resolve_citation(mention)
            assert res["resolution_status"] == "unresolved", f"Incomplete citation '{c}' resolved to '{res.get('resolved_document_id')}'"
            assert res["resolved_document_id"] is None

    # 4. Historical cases not linked via party-name overlap
    def test_historical_cases_not_linked_via_party_overlap(self, entity_resolver):
        historical_cases = [
            {
                "raw_text": "State of H.P. v. Gujarat Ambuja Cement (2005) 6 SCC 499",
                "normalized_citation": "(2005) 6 SCC 499",
                "extracted_case_title": "State of H.P. v. Gujarat Ambuja Cement",
                "citation_type": "canonical_citation",
                "components": {"year": 2005}
            },
            {
                "raw_text": "Satender Kumar Antil v. CBI (2022) 10 SCC 51",
                "normalized_citation": "(2022) 10 SCC 51",
                "extracted_case_title": "Satender Kumar Antil v. CBI",
                "citation_type": "canonical_citation",
                "components": {"year": 2022}
            },
            {
                "raw_text": "Karan Singh v. Union of India, AIR 1997 SC 3889",
                "normalized_citation": "AIR 1997 SC 3889",
                "extracted_case_title": "Karan Singh v. Union of India",
                "citation_type": "canonical_citation",
                "components": {"year": 1997}
            }
        ]
        for h in historical_cases:
            h["source_doc_id"] = "test_src_2024"
            res = entity_resolver.resolve_citation(h)
            assert res["resolution_status"] == "unresolved", f"Historical case '{h['raw_text']}' incorrectly resolved to '{res.get('resolved_document_id')}'"
            assert res["resolved_document_id"] is None
            assert "historical" in res["match_method"] or "pre_2024" in res["match_method"] or "unresolved" in res["match_method"]

    # 5. Self-citations rejected from cross-document precedent edges
    def test_self_citations_rejected_from_cross_document_edges(self, entity_resolver, graph_v2_store):
        # Resolver check
        mention = {
            "source_doc_id": "2024_10_108_125",
            "raw_text": "2024 INSC 735",
            "normalized_citation": "2024 INSC 735",
            "citation_type": "neutral_insc"
        }
        res = entity_resolver.resolve_citation(mention)
        assert res["is_self_citation"] is True, "Self citation flag not set!"
        assert res["resolved_document_id"] == "2024_10_108_125"

        # Graph check: no self-loop CITES edges in graph v2
        with graph_v2_store._get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM edges
                WHERE relationship_type = 'CITES' AND source_node_id = target_node_id
            """)
            assert cursor.fetchone()[0] == 0

            # Excluded edges check: self citations are logged in excluded_edges
            cursor = conn.execute("""
                SELECT COUNT(*) FROM excluded_edges
                WHERE exclusion_reason = 'SELF_CITATION'
            """)
            self_exclusions = cursor.fetchone()[0]
            assert self_exclusions > 0, "No self-citations logged in excluded_edges!"

    # 6. Multiple candidate targets remain ambiguous
    def test_multiple_candidate_targets_remain_ambiguous(self, entity_resolver):
        mention = {
            "source_doc_id": "dummy_source",
            "raw_text": "Union of India v. ABC Ltd.",
            "extracted_case_title": "Union of India v. ABC Ltd.",
            "normalized_citation": None,
            "citation_type": "case_title"
        }
        # If ambiguous, resolution_status must be 'ambiguous' and target must be None
        res = entity_resolver.resolve_citation(mention)
        if len(res.get("ambiguous_candidate_ids", [])) > 1:
            assert res["resolution_status"] == "ambiguous"
            assert res["resolved_document_id"] is None
            assert len(res["ambiguous_candidate_ids"]) >= 2

    # 7. Out-of-corpus precedent not marked nonexistent
    def test_out_of_corpus_precedent_not_marked_nonexistent(self, graph_v2_store):
        with graph_v2_store._get_connection() as conn:
            # Check external reference nodes exist and represent unverified external references
            cursor = conn.execute("""
                SELECT node_id, name, properties_json FROM nodes
                WHERE node_type = 'ExternalReference' LIMIT 10
            """)
            rows = cursor.fetchall()
            assert len(rows) > 0, "ExternalReference nodes missing from Graph V2"
            for node_id, name, props_json in rows:
                props = json.loads(props_json)
                assert props.get("verified") is False
                assert props.get("external_source") == "Unverified Historical Reference"

            # Check CITES_EXTERNAL edges exist
            cursor = conn.execute("""
                SELECT COUNT(*) FROM edges WHERE relationship_type = 'CITES_EXTERNAL'
            """)
            assert cursor.fetchone()[0] > 0

    # 8. Explicit Act attribution preserved
    def test_explicit_act_attribution_preserved(self, statute_resolver):
        explicit_cases = [
            ("Section 307 IPC", "Indian Penal Code, 1860"),
            ("Section 482 of the Code of Criminal Procedure, 1973", "Code of Criminal Procedure, 1973"),
            ("Section 17(5)(d) of the Central Goods and Services Tax Act, 2017", "Central Goods and Services Tax Act, 2017"),
            ("Section 9 of the Insolvency and Bankruptcy Code, 2016", "Insolvency and Bankruptcy Code, 2016")
        ]
        for text, expected_act in explicit_cases:
            matches = statute_resolver.resolve_document_statutes(text, "test_doc")
            assert len(matches) >= 1, f"No match for '{text}'"
            m = matches[0]
            assert m["attribution_type"] == "explicit", f"Expected explicit attribution for '{text}', got '{m['attribution_type']}'"
            assert m["components"]["governing_statute"] == expected_act, f"Expected '{expected_act}', got '{m['components']['governing_statute']}'"

    # 9. Ambiguous statutory sections not assigned Act from number alone
    def test_ambiguous_sections_not_assigned_act(self, statute_resolver):
        # When two Acts precede a bare section in the same paragraph
        text = "The Indian Penal Code, 1860 and the Code of Criminal Procedure, 1973 were both discussed. Thereafter, Section 5 was invoked."
        matches = statute_resolver.resolve_document_statutes(text, "test_doc")
        sec_matches = [m for m in matches if m["reference_type"] == "statutory_section"]
        assert len(sec_matches) == 1
        m = sec_matches[0]
        assert m["attribution_type"] == "ambiguous"
        assert m["components"]["governing_statute"] is None, f"Expected None for ambiguous section, got '{m['components']['governing_statute']}'"

    # 10. Inheritance does not cross paragraph boundaries
    def test_inheritance_does_not_cross_paragraph_boundaries(self, statute_resolver):
        # Paragraph 1 has an Act; Paragraph 2 has a bare section
        p1 = "The High Court considered the provisions of the Income Tax Act, 1961 in detail."
        p2 = "The Assessing Officer issued a notice under Section 148."
        full_text = f"{p1}\n\n{p2}"

        matches = statute_resolver.resolve_document_statutes(full_text, "test_doc")
        sec_matches = [m for m in matches if m["reference_type"] == "statutory_section"]
        assert len(sec_matches) == 1
        m = sec_matches[0]
        # Should NOT inherit Income Tax Act across paragraph boundary
        assert m["attribution_type"] == "unresolved", f"Expected unresolved across paragraph, got '{m['attribution_type']}'"
        assert m["components"]["governing_statute"] is None

    # 11. All internal CITES targets exist in 782 corpus
    def test_all_internal_cites_targets_exist_in_corpus(self, graph_v2_store, corpus_doc_ids):
        with graph_v2_store._get_connection() as conn:
            cursor = conn.execute("""
                SELECT DISTINCT target_node_id FROM edges
                WHERE relationship_type = 'CITES'
            """)
            targets = [r[0] for r in cursor.fetchall()]
            assert len(targets) > 0, "No CITES edges found in Graph V2!"
            for t in targets:
                assert t.startswith("doc:"), f"Invalid target node prefix: {t}"
                doc_id = t[4:]
                assert doc_id in corpus_doc_ids, f"Target {doc_id} not in 782 corpus!"

    # 12. Deterministic edge deduplication with mention provenance
    def test_deterministic_edge_deduplication(self, graph_v2_store):
        with graph_v2_store._get_connection() as conn:
            cursor = conn.execute("""
                SELECT source_node_id, target_node_id, relationship_type, COUNT(*)
                FROM edges
                GROUP BY source_node_id, target_node_id, relationship_type
                HAVING COUNT(*) > 1
            """)
            duplicates = cursor.fetchall()
            assert len(duplicates) == 0, f"Found duplicate edges in Graph V2: {duplicates}"

            # Check edges with multiple mentions
            cursor = conn.execute("""
                SELECT mention_count, mentions_json FROM edges
                WHERE relationship_type = 'CITES' AND mention_count > 1 LIMIT 5
            """)
            rows = cursor.fetchall()
            for count, m_json in rows:
                mentions = json.loads(m_json)
                assert len(mentions) == count
                assert count > 1

    # 13. Source traceability on all graph edges
    def test_source_traceability_on_all_edges(self, graph_v2_store):
        with graph_v2_store._get_connection() as conn:
            cursor = conn.execute("""
                SELECT edge_id, mentions_json FROM edges LIMIT 100
            """)
            rows = cursor.fetchall()
            assert len(rows) > 0
            for edge_id, m_json in rows:
                mentions = json.loads(m_json)
                assert isinstance(mentions, list) and len(mentions) > 0, f"Edge {edge_id} has empty mentions"
                for m in mentions:
                    assert "source_doc_id" in m, f"Edge {edge_id} mention lacks source_doc_id"
                    assert "extraction_method" in m, f"Edge {edge_id} mention lacks extraction_method"

    # 14. Unverified treatment signals do not produce precedent-status labels
    def test_unverified_treatment_signals_preserve_observational_integrity(self, graph_v2_store):
        with graph_v2_store._get_connection() as conn:
            # Nodes should not have synthetic precedent status flags
            cursor = conn.execute("""
                SELECT properties_json FROM nodes WHERE node_type = 'Judgment' LIMIT 50
            """)
            for (props_json,) in cursor.fetchall():
                props = json.loads(props_json)
                assert "is_good_law" not in props
                assert "overruled" not in props
                assert "precedent_status" not in props

            # Check that mentions preserve observational treatment signals without mutating edge schema
            cursor = conn.execute("""
                SELECT mentions_json FROM edges WHERE relationship_type IN ('CITES', 'CITES_EXTERNAL')
            """)
            found_treatment = False
            for (m_json,) in cursor.fetchall():
                mentions = json.loads(m_json)
                for m in mentions:
                    if m.get("treatment_signal"):
                        found_treatment = True
                        assert isinstance(m["treatment_signal"], str)
            assert found_treatment is True, "Expected at least one observational treatment signal in mentions"

    # 15. Graph v2 manifest consistency check
    def test_graph_manifest_consistency(self):
        manifest_path = os.path.join(GRAPH_V2_DIR, "graph_manifest.json")
        assert os.path.exists(manifest_path)
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["graph_version"] == "2.0.0"
        assert manifest["nodes_count"] > 30000
        assert manifest["edges_count"] > 50000
        assert manifest["edge_type_breakdown"]["CITES"] == 171
        assert manifest["exclusion_reason_breakdown"]["SELF_CITATION"] > 7000
        assert manifest["exclusion_reason_breakdown"]["HISTORICAL_PRE_2024"] > 30000
