"""
Regression Test Suite for Milestone 8: Multi-Passage Evidence Selection and Context Budgeting.

Verifies:
1. Single-passage behavior remains available.
2. Two-passage and three-passage limits are respected.
3. Complementary passages can both be selected.
4. Duplicate passages do not consume the evidence budget unnecessarily.
5. Equal-score results use deterministic tie-breaking.
6. Exact source offsets remain valid.
7. Compressed sentences retain correct source references.
8. Evidence IDs are generated only for active passages.
9. Schema IDs match the final active evidence set.
10. Unsupported queries still abstain under multi-passage retrieval.
11. Conflicting passages do not produce an unsupported universal rule.
12. Missing statutory qualifications do not become fabricated conclusions.
13. Structured citation validation still fails closed.
14. API response behavior remains compatible.
"""
import os
import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from services.rag.models import (
    EvidencePassage,
    StructuredAnswer,
    StructuredClaim,
    get_structured_answer_schema
)
from services.rag.evidence import (
    select_complementary_evidence_passages,
    compute_jaccard_similarity,
    ExtractiveSentenceCompressor,
    verify_and_filter_evidence
)
from services.rag.grounding_gate import (
    PropositionGroundingGate,
    GroundingStatus,
    GroundingDecision
)
from services.rag.validator import CitationValidator
from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider
from apps.api.main import app

CORPUS_DIR = "data/processed/aws_sc"


@pytest.fixture
def api_client():
    return TestClient(app)


def _make_dummy_passage(
    eid: str,
    doc_id: str,
    text: str,
    start_char: int = 0,
    end_char: int = 100,
    score: float = 10.0,
    rank: int = 1
) -> EvidencePassage:
    return EvidencePassage(
        evidence_id=eid,
        document_id=doc_id,
        case_title=f"Case {doc_id}",
        citation="2024 INSC 100",
        passage_text=text,
        start_char=start_char,
        end_char=end_char,
        judgment_rank=rank,
        judgment_score=0.9,
        passage_score=score
    )


class TestMilestone8MultiPassageSelection:

    def test_single_passage_baseline_available(self):
        """1. Single-passage configuration (max_passages=1) preserves Milestone 7 baseline."""
        p1 = _make_dummy_passage("E1", "doc1", "Primary passage text on statutory interpretation.", score=15.0)
        p2 = _make_dummy_passage("E2", "doc1", "Secondary passage text with additional holding.", score=12.0)
        p3 = _make_dummy_passage("E3", "doc2", "Tertiary passage from another judgment.", score=10.0)

        selected = select_complementary_evidence_passages(
            passages=[p1, p2, p3],
            query="statutory interpretation principles",
            max_passages=1
        )
        assert len(selected) == 1
        assert selected[0].evidence_id == "E1"
        assert selected[0].document_id == "doc1"
        assert selected[0].passage_text == p1.passage_text

    def test_passage_limits_respected_two_and_three(self):
        """2. Two-passage and three-passage limits are strictly respected."""
        sample_texts = [
            "Contract formation requires lawful consideration and free consent.",
            "Tortious liability for economic loss under common law precedents.",
            "Equitable remedies of injunction and specific performance standards.",
            "Arbitration award enforcement under Section 34 of the Act.",
            "Writ jurisdiction under Article 226 for administrative violations."
        ]
        candidates = [
            _make_dummy_passage(f"E{i}", f"doc{i}", text, score=20.0 - i, rank=i)
            for i, text in enumerate(sample_texts, 1)
        ]
        sel2 = select_complementary_evidence_passages(candidates, query="contract remedies arbitration", max_passages=2)
        assert len(sel2) == 2
        assert [p.evidence_id for p in sel2] == ["E1", "E2"]

        sel3 = select_complementary_evidence_passages(candidates, query="contract remedies arbitration", max_passages=3)
        assert len(sel3) == 3
        assert [p.evidence_id for p in sel3] == ["E1", "E2", "E3"]

    def test_complementary_passages_both_selected(self):
        """3. Complementary passages offering distinct query terms or holding markers are selected."""
        p1 = _make_dummy_passage("E1", "2024_10_793_859", "Issue for consideration regarding Section 17(5)(d) plant eligibility.", score=18.0)
        p2 = _make_dummy_passage("E2", "2024_10_793_859", "Held: Functionality test to be applied to decide whether construction is a plant.", start_char=200, end_char=350, score=17.5)

        selected = select_complementary_evidence_passages(
            passages=[p1, p2],
            query="Does Section 17(5)(d) apply the functionality test?",
            max_passages=2
        )
        assert len(selected) == 2
        assert [p.evidence_id for p in selected] == ["E1", "E2"]
        assert any("functionality test" in p.passage_text.lower() for p in selected)
        assert any("section 17(5)(d)" in p.passage_text.lower() for p in selected)

    def test_duplicate_passages_deduplicated_not_wasting_budget(self):
        """4. Passages with overlapping character spans or near-identical text are deduplicated."""
        # Overlapping character spans in same doc
        p1 = _make_dummy_passage("E1", "docA", "Common law principles regarding contract formation and breach.", start_char=100, end_char=500, score=15.0)
        p_overlap = _make_dummy_passage("E2", "docA", "Common law principles regarding contract formation and breach.", start_char=200, end_char=600, score=14.0)
        p_distinct = _make_dummy_passage("E3", "docB", "Remedies available for liquidated damages under section 74.", start_char=0, end_char=300, score=13.0)

        selected = select_complementary_evidence_passages(
            passages=[p1, p_overlap, p_distinct],
            query="contract breach liquidated damages",
            max_passages=2
        )
        assert len(selected) == 2
        # p_overlap should be skipped in favor of p_distinct
        assert selected[0].document_id == "docA"
        assert selected[1].document_id == "docB"
        assert "liquidated damages" in selected[1].passage_text

    def test_equal_score_deterministic_tie_breaking(self):
        """5. Equal-score passages use deterministic tie-breaking (rank, start_char, doc_id)."""
        p_a = _make_dummy_passage("E1", "docX", "Specific performance of contract requiring readiness and willingness.", score=10.0, rank=1, start_char=100)
        p_b = _make_dummy_passage("E2", "docY", "Limitation period for filing arbitration appeal under section 37.", score=10.0, rank=1, start_char=500)

        res1 = select_complementary_evidence_passages([p_a, p_b], query="contract arbitration", max_passages=2)
        res2 = select_complementary_evidence_passages([p_b, p_a], query="contract arbitration", max_passages=2)

        assert [p.document_id for p in res1] == [p.document_id for p in res2]
        assert [p.evidence_id for p in res1] == ["E1", "E2"]

    def test_exact_source_offsets_remain_valid(self):
        """6. Exact source character offsets match canonical full_text slices perfectly."""
        # Test on real corpus judgment
        doc_id = "2024_10_793_859"  # Safari Retreats
        fpath = Path(CORPUS_DIR) / f"{doc_id}.json"
        assert fpath.exists(), f"Corpus document missing: {fpath}"

        with open(fpath, "r", encoding="utf-8") as f:
            full_text = json.load(f)["full_text"]

        p1_slice = full_text[0:1912]
        p2_slice = full_text[1914:4487]

        p1 = _make_dummy_passage("E1", doc_id, p1_slice, start_char=0, end_char=1912, score=19.5)
        p2 = _make_dummy_passage("E2", doc_id, p2_slice, start_char=1914, end_char=4487, score=19.0)

        selected = select_complementary_evidence_passages([p1, p2], query="functionality test CGST", max_passages=2)
        assert len(selected) == 2

        for p in selected:
            assert full_text[p.start_char:p.end_char] == p.passage_text

    def test_compressed_sentences_retain_correct_source_references(self):
        """7. Extractive sentence compressor preserves absolute document character offsets."""
        sample_text = (
            "The High Court held that the writ petition was maintainable. "
            "Section 18 of the Limitation Act applies to proceedings before NCLT. "
            "We find no merit in the appeal filed by the appellant."
        )
        base_offset = 5000
        sentences = ExtractiveSentenceCompressor.split_sentences_with_offsets(sample_text, base_offset=base_offset)
        assert len(sentences) == 3

        for s in sentences:
            expected_slice = sample_text[s["rel_start"]:s["rel_end"]]
            assert s["text"] == expected_slice
            assert s["abs_start"] == base_offset + s["rel_start"]
            assert s["abs_end"] == base_offset + s["rel_end"]

    def test_evidence_ids_generated_only_for_active_passages(self):
        """8. Evidence IDs are sequential E1..Ek matching only active budgeted passages."""
        sample_texts = [
            "First issue regarding jurisdiction of company court.",
            "Second point on moratorium under insolvency code.",
            "Third matter concerning recovery of statutory dues.",
            "Fourth question on priority of secured creditors.",
            "Fifth aspect of liquidation value distribution."
        ]
        candidates = [
            _make_dummy_passage(f"RAW{i}", f"doc{i}", text, score=15.0 - i)
            for i, text in enumerate(sample_texts, 1)
        ]
        selected = select_complementary_evidence_passages(candidates, query="insolvency moratorium", max_passages=2)
        assert len(selected) == 2
        assert [p.evidence_id for p in selected] == ["E1", "E2"]
        # Discarded candidates RAW3..RAW5 must not appear
        assert "E3" not in [p.evidence_id for p in selected]

    def test_schema_ids_match_final_active_evidence_set(self):
        """9. Schema enum constraint matches exactly the active evidence IDs."""
        active_ids = ["E1", "E2"]
        schema = get_structured_answer_schema(allowed_evidence_ids=active_ids)

        items_schema = schema["properties"]["claims"]["items"]["properties"]["evidence_ids"]["items"]
        assert items_schema["enum"] == ["E1", "E2"]
        assert "E3" not in items_schema["enum"]

    def test_unsupported_queries_still_abstain_under_multipassage(self):
        """10. Unanswerable queries still abstain even when multi-passage (max_passages=3) is enabled."""
        pipe = RAGPipeline(llm_provider=MockLLMProvider())
        # DPDP Act s.18 query from canonical abstention set
        q = "What are the eligibility criteria and tenure prescribed under Section 18 of the Digital Personal Data Protection Act, 2023 for members of the Data Protection Board of India?"
        result = pipe.query(q, max_passages=3, structured_output=True)

        assert result.status == "insufficient_evidence"
        assert "INSUFFICIENT EVIDENCE" in result.answer

    def test_conflicting_passages_do_not_produce_unsupported_universal_rule(self):
        """11. Contradictory evidence passages trigger conservative abstention."""
        gate = PropositionGroundingGate()
        p1 = _make_dummy_passage("E1", "doc1", "The statutory period is strictly non-extendable and a mandatory bar applies under all circumstances.")
        p2 = _make_dummy_passage("E2", "doc2", "The period is extendable with the consent of both parties and is not absolute or sacrosanct.")

        decision = gate.check_active_evidence_sufficiency(
            query="Is the statutory limitation period extendable?",
            active_passages=[p1, p2]
        )
        assert decision.is_grounded is False
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING
        assert "contradictory propositions" in decision.rationale

    def test_missing_statutory_qualifications_do_not_become_fabricated(self):
        """12. If active evidence lacks an inquired statutory test, gate abstains."""
        gate = PropositionGroundingGate()
        # Active passage has general tax issue but lacks functionality test
        p1 = _make_dummy_passage("E1", "doc1", "Matter pertains to Section 17(5)(d) of the CGST Act regarding input tax credit.")

        decision = gate.check_active_evidence_sufficiency(
            query="Does Section 17(5)(d) of the CGST Act apply the functionality test for building leases?",
            active_passages=[p1]
        )
        assert decision.is_grounded is False
        assert "functionality test" in decision.rationale

    def test_structured_citation_validation_fails_closed(self):
        """13. Structured citation validator rejects hallucinated evidence IDs beyond active set."""
        validator = CitationValidator()
        active_passages = [
            _make_dummy_passage("E1", "doc1", "Evidence one text."),
            _make_dummy_passage("E2", "doc2", "Evidence two text.")
        ]
        # Answer cites E3 which was not active
        ans_with_e3 = StructuredAnswer(
            status="answer",
            claims=[
                StructuredClaim(text="Claim one", evidence_ids=["E1"]),
                StructuredClaim(text="Claim two with phantom ID", evidence_ids=["E3"])
            ]
        )
        val_res, claims = validator.validate_structured(ans_with_e3, supplied_evidence=active_passages)

        assert val_res.is_valid is False
        assert "E3" in val_res.invalid_source_ids

    def test_api_response_behavior_remains_compatible(self, api_client):
        """14. FastAPI /v1/rag/query accepts max_passages and enable_compression and returns valid result."""
        payload = {
            "query": "Can an authorized signatory who signs a cheque on behalf of a company be directed to deposit an interim sum under Section 148?",
            "top_k_judgments": 2,
            "max_passages": 2,
            "provider_type": "mock",
            "enable_compression": False,
            "structured_output": True
        }
        resp = api_client.post("/v1/rag/query", json=payload)
        assert resp.status_code == 200
        data = resp.json()

        assert "status" in data
        assert "answer" in data
        assert "evidence_passages" in data
        assert len(data["evidence_passages"]) <= 2
        assert "citation_validation" in data
        assert data["citation_validation"]["is_valid"] is True
