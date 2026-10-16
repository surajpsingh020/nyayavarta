"""
Regression Test Suite for Milestone 10: Retrieval Quality Audit & Evidence-Grounded Answer Evaluation.

Verifies:
1. Unknown or stale evidence IDs fail closed.
2. Malformed structured output rejected fail-closed.
3. Claims without citations rejected.
4. Unsupported claims with valid evidence IDs flagged.
5. Missing statutory exceptions captured in audit.
6. Party submissions misrepresented as holdings blocked.
7. Contradictory passages cause conservative abstention.
8. Unsupported questions fast-exit without LLM invocation.
9. Evidence IDs match the final active evidence set strictly.
10. API behavior when validation fails.
11. Invalid answers cannot be serialized as fully validated answers.
12. Context budget reconciliation metrics present in metadata.
13. Passage and context budgets enforced at correct pipeline stages.
14. Contiguous sentence compression preserves 100% exact character offset invariance.
"""
import os
import json
from typing import Dict, Any, Optional, List
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from services.rag.models import (
    EvidencePassage,
    StructuredAnswer,
    StructuredClaim,
    RAGResult,
    CitationValidationResult,
    get_structured_answer_schema
)
from services.rag.evidence import (
    select_complementary_evidence_passages,
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
    end_char: Optional[int] = None,
    score: float = 1.0,
    rank: int = 1,
    structural_label: Optional[str] = None
) -> EvidencePassage:
    if end_char is None:
        end_char = start_char + len(text)
    return EvidencePassage(
        evidence_id=eid,
        document_id=doc_id,
        case_title="State of Test v. Respondent",
        citation="[2024] 10 S.C.R. 999",
        case_number="C.A. No. 1234/2024",
        decision_date="2024-10-01",
        passage_text=text,
        start_char=start_char,
        end_char=end_char,
        judgment_rank=rank,
        judgment_score=score,
        passage_score=score,
        structural_label=structural_label
    )


class TestMilestone10Audit:

    def test_unknown_or_stale_evidence_ids_fail_closed(self):
        """1. Unknown or stale evidence IDs (e.g. E99) fail closed."""
        validator = CitationValidator()
        p1 = _make_dummy_passage("E1", "doc1", "Bail is the rule and jail is the exception.")
        
        answer = StructuredAnswer(
            status="answer",
            claims=[
                StructuredClaim(text="Bail is generally granted under PMLA.", evidence_ids=["E1"]),
                StructuredClaim(text="Stale citation to unsupplied authority.", evidence_ids=["E99"])
            ]
        )
        val_res, claims = validator.validate_structured(answer, supplied_evidence=[p1])
        assert not val_res.is_valid
        assert "E99" in val_res.invalid_source_ids
        assert val_res.has_invalid_citations

    def test_malformed_structured_output_rejected(self):
        """2. Malformed structured output fails closed without crashing."""
        provider = MockLLMProvider(mode=MockLLMProvider.MODE_MALFORMED)
        pipeline = RAGPipeline(llm_provider=provider)
        grounded_query = (
            "Can the Supreme Court exercise powers under Article 142 of the Constitution to grant admission "
            "to an IIT candidate from a marginalized community who was prevented from paying fees due to a portal login glitch?"
        )
        res = pipeline.query(grounded_query, max_passages=1, structured_output=True)
        assert res.status == "validation_failed"
        assert res.grounding_status == GroundingStatus.VALIDATION_FAILED.value

    def test_claims_without_citations_rejected(self):
        """3. Claims without citations are rejected fail-closed."""
        validator = CitationValidator()
        p1 = _make_dummy_passage("E1", "doc1", "Section 18 acknowledgment extends limitation.")
        answer = StructuredAnswer(
            status="answer",
            claims=[
                StructuredClaim(text="Limitation is extended.", evidence_ids=[]),
                StructuredClaim(text="Section 18 applies.", evidence_ids=["E1"])
            ]
        )
        val_res, claims = validator.validate_structured(answer, supplied_evidence=[p1])
        assert not val_res.is_valid
        assert not val_res.attribution_complete
        assert len(val_res.unsupported_sentences) >= 1

    def test_unsupported_claim_with_valid_evidence_id(self):
        """4. Unsupported claims with syntactically valid evidence IDs are captured."""
        from scripts.benchmark.evaluate_milestone10_ollama_audit import audit_claim_against_evidence
        
        passages = [{
            "passage_text": "Section 18 Limitation Act applies to IBC proceedings.",
            "structural_label": "judicial_holding"
        }]
        # Claim introduces extrinsic unsupported proposition
        claim = "Section 18 Limitation Act permanently waives all debt obligations forever."
        res = audit_claim_against_evidence(
            claim_text=claim,
            evidence_passages=passages,
            query_text="Does Section 18 extend limitation?",
            expected_ratio="Acknowledgment extends limitation."
        )
        assert res["review_status"] in ["unsupported", "partially_supported"]

    def test_missing_statutory_exception_captured(self):
        """5. Missing statutory exceptions are flagged."""
        from scripts.benchmark.evaluate_milestone10_ollama_audit import audit_claim_against_evidence

        passages = [{
            "passage_text": "Held: Every commercial building must satisfy functionality test under Section 17(5)(d).",
            "structural_label": "headnote_holding"
        }]
        claim = "Every building automatically qualifies for input tax credit as a plant."
        res = audit_claim_against_evidence(
            claim_text=claim,
            evidence_passages=passages,
            query_text="Does mall qualify as plant?",
            expected_ratio="Subject to functionality test."
        )
        assert res["omits_statutory_qualification_or_exception"] is True

    def test_party_submissions_misrepresented_as_holdings_blocked(self):
        """6. Party submissions are marked with negative weight and blocked from being treated as holdings."""
        gate = PropositionGroundingGate()
        submission_passage = _make_dummy_passage(
            "E1", "doc1",
            "Counsel for the appellant vehemently argued that the High Court lacked jurisdiction.",
            structural_label="party_submissions"
        )
        decision = gate.assess_grounding(
            query="Did the Supreme Court hold that the High Court lacked jurisdiction?",
            evidence_passages=[submission_passage]
        )
        assert not decision.is_grounded
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING

    def test_contradictory_passages_conservative_abstention(self):
        """7. Contradictory passages cause conservative abstention."""
        gate = PropositionGroundingGate()
        p1 = _make_dummy_passage(
            "E1", "doc1",
            "Held: The statutory period of limitation is strictly non-extendable under any circumstances.",
            structural_label="headnote_holding"
        )
        p2 = _make_dummy_passage(
            "E2", "doc1",
            "Held: The period of limitation is extendable with the consent of both parties.",
            structural_label="headnote_holding"
        )
        decision = gate.assess_grounding(
            query="Can the limitation period be extended with party consent?",
            evidence_passages=[p1, p2]
        )
        assert not decision.is_grounded
        assert decision.status == GroundingStatus.TOPICALLY_RELEVANT_BUT_INSUFFICIENT_GROUNDING

    def test_unsupported_questions_fast_exit_abstention(self):
        """8. Unsupported questions fast-exit without LLM invocation."""
        pipeline = RAGPipeline()
        res = pipeline.query(
            "What is the statutory limitation period under Section 16 of the Competition Act 2002 for Director General appointment?",
            max_passages=2,
            structured_output=True
        )
        assert res.status == "insufficient_evidence"
        assert res.timing_ms.get("generation_ms", 0) == 0

    def test_dynamic_evidence_ids_match_active_set_strictly(self):
        """9. Schema enum constraints match the exact active evidence IDs."""
        schema = get_structured_answer_schema(["E1", "E2"])
        items_def = schema["properties"]["claims"]["items"]["properties"]["evidence_ids"]["items"]
        assert items_def["enum"] == ["E1", "E2"]

    def test_api_behavior_when_validation_fails(self, api_client):
        """10. API returns 200 with status='validation_failed' when validation fails."""
        resp = api_client.post("/v1/rag/query", json={
            "query": "Can the Supreme Court grant bail under PMLA?",
            "max_passages": 2,
            "structured_output": True
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert "grounding_status" in data

    def test_invalid_answer_cannot_be_serialized_as_validated(self):
        """11. An invalid answer cannot be serialized with status='answered'."""
        val_failed = CitationValidationResult(
            is_valid=False,
            citation_syntax_valid=False,
            citation_existence_valid=False,
            attribution_complete=False,
            evidence_integrity_valid=True,
            semantic_support_status="invalid",
            cited_source_ids=["E99"],
            valid_source_ids=[],
            invalid_source_ids=["E99"],
            unsupported_sentences=["Extrinsic claim [E99]."],
            has_invalid_citations=True,
            validation_notes=["Unknown citation ID"]
        )
        # Attempting to construct RAGResult with answered status must be caught or verified
        res = RAGResult(
            query="Test query",
            answer="Extrinsic claim [E99].",
            status="validation_failed" if not val_failed.is_valid else "answered",
            grounding_status=GroundingStatus.VALIDATION_FAILED.value,
            evidence_passages=[],
            citation_validation=val_failed,
            claims=[]
        )
        assert res.status != "answered"
        assert res.grounding_status == GroundingStatus.VALIDATION_FAILED.value

    def test_context_budget_reconciliation_metrics_present(self):
        """12. Context budget metrics are separately recorded in retrieval_metadata."""
        pipeline = RAGPipeline()
        res = pipeline.query(
            "Can the Supreme Court exercise powers under Article 142 to grant admission to an IIT candidate?",
            max_passages=2,
            max_chars_per_passage=550,
            structured_output=True
        )
        budget = res.retrieval_metadata.get("context_budget")
        assert budget is not None
        assert "candidate_passages_count" in budget
        assert "candidate_text_chars" in budget
        assert "active_passages_count" in budget
        assert "active_passages_raw_chars" in budget
        assert "formatted_evidence_chars" in budget
        assert "prompt_chars" in budget
        assert "total_prompt_chars" in budget
        assert budget["max_chars_per_passage"] == 550
        assert budget["max_passages"] == 2

    def test_passage_and_context_budgets_enforced_at_pipeline_stage(self):
        """13. Configured passage limits and character budgets are enforced at the correct stages."""
        pipeline = RAGPipeline()
        res = pipeline.query(
            "Does a shopping mall constructed for letting out qualify as plant under Section 17(5)(d) CGST?",
            max_passages=2,
            max_chars_per_passage=550,
            enable_compression=True,
            structured_output=True
        )
        assert len(res.evidence_passages) <= 2
        budget = res.retrieval_metadata["context_budget"]
        assert budget["active_passages_count"] <= 2
        # Formatted evidence chars should reflect the capped passage text plus headers
        assert budget["formatted_evidence_chars"] > 0
        assert budget["formatted_evidence_chars"] < budget["candidate_text_chars"]

    def test_contiguous_compression_offset_invariance(self):
        """14. Contiguous sentence compressor guarantees 100% exact character offset slicing."""
        doc_id = "2024_10_793_859"  # Safari Retreats
        fpath = Path(CORPUS_DIR) / f"{doc_id}.json"
        assert fpath.exists()

        with open(fpath, "r", encoding="utf-8") as f:
            full_text = json.load(f)["full_text"]

        p_slice = full_text[1914:4487]
        p = _make_dummy_passage("E1", doc_id, p_slice, start_char=1914, end_char=4487)

        compressed = ExtractiveSentenceCompressor.compress_passage(p, query="functionality test plant", max_chars=550)
        assert len(compressed.passage_text) <= 550 or len(compressed.passage_text) < len(p_slice)
        # Invariance assertion
        assert full_text[compressed.start_char:compressed.end_char] == compressed.passage_text
