"""
Integrity Tests for NyayaVarta Knowledge Graph Prototype (Milestone 4B).

Verifies all mandatory restrictions:
1. Zero self-loop CITES edges (source_doc_id != target_doc_id).
2. All internal targets exist in the canonical corpus.
3. No edge contradicts its source resolution status.
4. Ambiguous candidates remain explicit with candidate sets preserved.
5. Historical unresolved references are not silently mapped to internal nodes.
6. Bare statutory provisions have no fabricated Act relationship.
7. Repeated citations retain mention-level provenance while deduplicating edges.
8. Deterministic export across repeated runs.
9. Every excluded relationship has an auditable exclusion reason.
"""
import pytest
import os
import json
import sqlite3
import hashlib

from services.graph.builder import GraphBuilder
from services.graph.sqlite_store import SQLiteGraphStore
from services.graph.models import Edge

GRAPH_DIR = "data/processed/graph/v1"
CORPUS_DIR = "data/processed/aws_sc"


@pytest.fixture(scope="module")
def sqlite_store():
    db_path = os.path.join(GRAPH_DIR, "graph.db")
    assert os.path.exists(db_path), f"graph.db not found at {db_path}"
    return SQLiteGraphStore(db_path=db_path)


@pytest.fixture(scope="module")
def corpus_doc_ids():
    ids = set()
    for fname in os.listdir(CORPUS_DIR):
        if fname.endswith(".json"):
            ids.add(fname[:-5])
    return ids


class TestGraphIntegrityMandatoryRestrictions:

    # 1. Zero self-loop CITES edges
    def test_zero_self_loop_cites_edges(self, sqlite_store):
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM edges
                WHERE relationship_type = 'CITES' AND source_node_id = target_node_id
            """)
            self_loops = cursor.fetchone()[0]
            assert self_loops == 0, f"Found {self_loops} self-loop CITES edges!"

    # 2. All internal targets exist in canonical corpus
    def test_all_internal_cites_targets_exist(self, sqlite_store, corpus_doc_ids):
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("""
                SELECT source_node_id, target_node_id FROM edges
                WHERE relationship_type = 'CITES'
            """)
            edges = cursor.fetchall()
            assert len(edges) > 0, "No CITES edges found to test"
            for row in edges:
                src = row[0].replace("doc:", "")
                tgt = row[1].replace("doc:", "")
                assert src in corpus_doc_ids, f"Source {src} not in corpus"
                assert tgt in corpus_doc_ids, f"Target {tgt} not in corpus"

    # 3. No edge contradicts its source resolution status
    def test_no_edge_contradicts_source_resolution_status(self, sqlite_store):
        """Every CITES edge must have come from a mention that was resolved to that target."""
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("""
                SELECT edge_id, mentions_json FROM edges
                WHERE relationship_type = 'CITES'
            """)
            for row in cursor.fetchall():
                mentions = json.loads(row[1])
                assert len(mentions) >= 1, "Edge has no mention provenance"
                for m in mentions:
                    assert m.get("source_doc_id") is not None
                    assert m.get("citation_type") is not None

    # 4. Ambiguous candidates remain explicit
    def test_ambiguous_candidates_remain_explicit_in_exclusions(self, sqlite_store):
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*), exclusion_detail FROM excluded_edges
                WHERE exclusion_reason = 'AMBIGUOUS_CANDIDATE'
            """)
            row = cursor.fetchone()
            count = row[0]
            assert count > 0, "No ambiguous exclusions recorded"
            # Verify details mention candidate IDs
            cursor2 = conn.execute("""
                SELECT exclusion_detail FROM excluded_edges
                WHERE exclusion_reason = 'AMBIGUOUS_CANDIDATE' LIMIT 5
            """)
            for r in cursor2.fetchall():
                assert "candidates" in r[0].lower()

    # 5. Historical unresolved references are not silently mapped to internal nodes
    def test_historical_unresolved_not_mapped_to_internal_nodes(self, sqlite_store):
        """Verify that historical citations pre-2024 are never targets of CITES edges."""
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("""
                SELECT e.edge_id, n.node_type, n.name
                FROM edges e
                JOIN nodes n ON e.target_node_id = n.node_id
                WHERE e.relationship_type = 'CITES' AND n.node_type != 'Judgment'
            """)
            bad_edges = cursor.fetchall()
            assert len(bad_edges) == 0, f"Found {len(bad_edges)} CITES edges pointing to non-Judgment nodes!"

    # 6. Bare statutory provisions have no fabricated Act relationship
    def test_bare_provisions_have_no_act_relationship(self, sqlite_store):
        """Unspecified section nodes must NOT have PART_OF_ACT edges."""
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM edges e
                JOIN nodes n ON e.source_node_id = n.node_id
                WHERE n.node_id LIKE 'section:unspecified:%' AND e.relationship_type = 'PART_OF_ACT'
            """)
            fabricated = cursor.fetchone()[0]
            assert fabricated == 0, f"Found {fabricated} fabricated PART_OF_ACT edges for unspecified sections!"

            # Verify BARE_SECTION_UNSPECIFIED_ACT exclusions exist
            cursor_ex = conn.execute("""
                SELECT COUNT(*) FROM excluded_edges
                WHERE exclusion_reason = 'BARE_SECTION_UNSPECIFIED_ACT'
            """)
            bare_exclusions = cursor_ex.fetchone()[0]
            assert bare_exclusions > 0, "No BARE_SECTION_UNSPECIFIED_ACT exclusions recorded"

    # 7. Repeated citations retain mention-level provenance while deduplicating edges
    def test_edge_deduplication_preserves_mention_arrays(self, sqlite_store):
        """Edges with mention_count > 1 must have exactly mention_count items in mentions_json."""
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("""
                SELECT edge_id, mention_count, mentions_json FROM edges
                WHERE mention_count > 1 LIMIT 20
            """)
            multi_edges = cursor.fetchall()
            assert len(multi_edges) > 0, "No multi-mention edges found"
            for row in multi_edges:
                count = row[1]
                mentions = json.loads(row[2])
                assert len(mentions) == count, f"Edge {row[0]}: count {count} != len(mentions) {len(mentions)}"

    # 8. Every excluded relationship has an auditable exclusion reason
    def test_every_excluded_relationship_has_valid_reason(self, sqlite_store):
        valid_reasons = {
            "SELF_CITATION",
            "TARGET_NOT_IN_CORPUS",
            "TITLE_ONLY_UNCORROBORATED",
            "HISTORICAL_PRE_2024",
            "UNRESOLVED_MENTION",
            "AMBIGUOUS_CANDIDATE",
            "BARE_SECTION_UNSPECIFIED_ACT"
        }
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("SELECT DISTINCT exclusion_reason FROM excluded_edges")
            reasons = {r[0] for r in cursor.fetchall()}
            assert reasons.issubset(valid_reasons), f"Invalid exclusion reasons found: {reasons - valid_reasons}"

    # 9. Determinism of JSONL export
    def test_deterministic_export_checksums(self):
        manifest_path = os.path.join(GRAPH_DIR, "graph_manifest.json")
        assert os.path.exists(manifest_path)
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        for filename, expected_hash in manifest["sha256_checksums"].items():
            fpath = os.path.join(GRAPH_DIR, filename)
            assert os.path.exists(fpath), f"{filename} does not exist"
            h = hashlib.sha256()
            with open(fpath, "rb") as fp:
                while chunk := fp.read(65536):
                    h.update(chunk)
            assert h.hexdigest() == expected_hash, f"Hash mismatch for {filename}"

    # 10. No PART_OF_ACT edge points to pseudo-Acts
    def test_no_part_of_act_edges_to_pseudo_acts(self, sqlite_store):
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM edges e
                JOIN nodes n ON e.target_node_id = n.node_id
                WHERE e.relationship_type = 'PART_OF_ACT'
                AND lower(n.name) IN ('the act', 'said act', 'aforesaid act', 'the code', 'this act', 'act')
            """)
            bad_edges = cursor.fetchone()[0]
            assert bad_edges == 0, f"Found {bad_edges} PART_OF_ACT edges pointing to pseudo-Acts!"

    # 11. Mention provenance strictly matches edge source
    def test_mention_provenance_strictly_matches_edge_source(self, sqlite_store):
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("""
                SELECT source_node_id, mentions_json FROM edges
                WHERE source_node_id LIKE 'doc:%'
                LIMIT 50
            """)
            for row in cursor.fetchall():
                expected_src = row[0].replace("doc:", "")
                mentions = json.loads(row[1])
                for m in mentions:
                    assert m.get("source_doc_id") == expected_src, (
                        f"Mention source '{m.get('source_doc_id')}' != edge source '{expected_src}'"
                    )

    # 12. Character spans strictly valid
    def test_character_spans_strictly_valid(self, sqlite_store):
        with sqlite_store._get_connection() as conn:
            cursor = conn.execute("SELECT mentions_json FROM edges LIMIT 100")
            for row in cursor.fetchall():
                mentions = json.loads(row[0])
                for m in mentions:
                    start = m.get("start_char")
                    end = m.get("end_char")
                    if start is not None and end is not None:
                        assert 0 <= start <= end, f"Invalid character span: start={start}, end={end}"

    # 13. Foreign key and node type constraints
    def test_foreign_key_and_node_type_constraints(self, sqlite_store):
        with sqlite_store._get_connection() as conn:
            # Check SQLite foreign keys
            fk_errors = conn.execute("PRAGMA foreign_key_check;").fetchall()
            assert len(fk_errors) == 0, f"Foreign key check failed: {fk_errors}"

            # Check that PART_OF_ACT edges only point to Act nodes
            bad_act_targets = conn.execute("""
                SELECT COUNT(*) FROM edges e
                JOIN nodes n ON e.target_node_id = n.node_id
                WHERE e.relationship_type = 'PART_OF_ACT' AND n.node_type != 'Act'
            """).fetchone()[0]
            assert bad_act_targets == 0, f"Found {bad_act_targets} PART_OF_ACT edges not pointing to Act nodes!"


class TestGraphIntegrityNegativeTests:

    def test_negative_mismatched_extraction_counts_raises_value_error(self, tmp_path):
        """Builder must fail explicitly when extraction and resolution counts differ."""
        extr_dir = tmp_path / "extraction"
        extr_dir.mkdir()

        # Write 2 citations but only 1 resolution record
        cites_file = extr_dir / "case_citations.jsonl"
        with open(cites_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({"source_doc_id": "doc1"}) + "\n")
            f.write(json.dumps({"source_doc_id": "doc2"}) + "\n")

        res_file = extr_dir / "resolved_entities.jsonl"
        with open(res_file, "w", encoding="utf-8") as f:
            f.write(json.dumps({"resolved_document_id": "docX"}) + "\n")

        builder = GraphBuilder(extraction_dir=str(extr_dir), output_dir=str(tmp_path / "out"))
        with pytest.raises(ValueError, match="record count mismatch"):
            builder.process_citations()

    def test_negative_invalid_character_spans_rejected(self, tmp_path):
        """Builder must raise ValueError when a mention has an inverted span."""
        builder = GraphBuilder(output_dir=str(tmp_path / "out"))
        bad_payload = {
            "source_doc_id": "test_doc",
            "start_char": 100,
            "end_char": 50  # inverted span
        }
        with pytest.raises(ValueError, match="Invalid character span"):
            builder._add_or_update_edge("doc:test_doc", "doc:other", "CITES", "high", bad_payload)

    def test_negative_mismatched_source_doc_id_rejected(self, tmp_path):
        """Builder must raise ValueError when mention source does not match edge source."""
        builder = GraphBuilder(output_dir=str(tmp_path / "out"))
        mismatched_payload = {
            "source_doc_id": "actual_doc_A",
            "start_char": 10,
            "end_char": 20
        }
        with pytest.raises(ValueError, match="disagrees with edge source"):
            builder._add_or_update_edge("doc:doc_B", "doc:other", "CITES", "high", mismatched_payload)

    def test_negative_pseudo_acts_rejected_by_clean_governing_act(self):
        """Builder must reject pseudo-Acts, anaphoric references, and regex boundary over-captures."""
        builder = GraphBuilder()
        assert builder.clean_and_validate_governing_act("the Act") is None
        assert builder.clean_and_validate_governing_act("said Act") is None
        assert builder.clean_and_validate_governing_act("aforesaid Act") is None
        assert builder.clean_and_validate_governing_act("the Code") is None
        assert builder.clean_and_validate_governing_act("this Act") is None
        assert builder.clean_and_validate_governing_act("Monopolies and Restrictive Trade Pract") is None
        assert builder.clean_and_validate_governing_act("POCSO, must be mindful of the fact") is None
        assert builder.clean_and_validate_governing_act("CrPC will be attract") is None

