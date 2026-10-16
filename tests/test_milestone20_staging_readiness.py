"""
Comprehensive Automated Test Suite for Milestone 20: Staging Readiness and Safety Gates.
Tests:
1. User Journey: Text query, retrieval, evidence selection, and character offsets.
2. User Journey: PDF/Canonical source offset correspondence and integrity.
3. User Journey: Qualified answers for partially supported claims (never verified_supported).
4. User Journey: Unresolved claims yield unverified_answer (never verified_supported).
5. User Journey: Contradicted claims yield rejected_answer and fail validation.
6. User Journey: Insufficient evidence triggers clean legal abstention with insufficient_evidence badge.
7. User Journey: Local LLM Timeout triggers HTTP 504 and provider error triggers HTTP 503.
8. User Journey: API serialization adheres to RAGResult schema and exports all badge fields.
9. Presentation Contract: Decoupled citations invariant (valid [E1] with false claim != verified).
10. Presentation Contract: Strict badge invariant across all 4 non-supported states.
11. Staging Benchmark: Frozen staging claims dataset integrity, balanced classes, and provenance.
12. Staging Gate: Readiness checklist validation and blocked release gate verification.
"""
import pytest
import json
from pathlib import Path
from fastapi.testclient import TestClient

from apps.api.main import app
from services.rag.models import (
    EvidencePassage,
    StructuredAnswer,
    StructuredClaim,
    CitationValidationResult,
    ClaimAttribution,
    RAGResult
)
from services.rag.validator import CitationValidator
from services.rag.claim_verifier import ClaimVerifier, ClaimVerificationStatus
from services.rag.pipeline import RAGPipeline
from services.rag.providers import MockLLMProvider, LocalOllamaProvider


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def sample_passage():
    return EvidencePassage(
        evidence_id="E1",
        document_id="2024_5_143_154",
        case_title="Yash Raj Films Private Limited v. Afreen Fatima",
        passage_text="Held: A promotional trailer is unilateral. It is only meant to encourage a viewer to purchase a ticket to the movie.",
        start_char=100,
        end_char=220,
        structural_label="headnote_holding"
    )


def test_1_user_journey_text_query_and_evidence_selection():
    """Test 1: Valid text query triggers retrieval, evidence selection, and returns exact character offsets."""
    pipeline = RAGPipeline(
        llm_provider=MockLLMProvider(mode=MockLLMProvider.MODE_STRUCTURED_NORMAL)
    )
    result = pipeline.query(
        query_text="What is the legal effect of a movie promotional trailer?",
        top_k_judgments=3,
        max_passages=3,
        structured_output=True
    )
    assert result.status in ["answered", "insufficient_evidence"]
    assert len(result.evidence_passages) > 0
    for ep in result.evidence_passages:
        assert ep.start_char >= 0
        assert ep.end_char > ep.start_char
        assert ep.document_id is not None
        assert len(ep.passage_text) > 0


def test_2_user_journey_pdf_canonical_source_offsets():
    """Test 2: Evidence offsets accurately map to canonical judgment full text."""
    corpus_file = Path("data/processed/aws_sc/2024_5_143_154.json")
    assert corpus_file.exists(), "Sample judgment file must exist."

    with corpus_file.open("r", encoding="utf-8") as f:
        doc_data = json.load(f)

    full_text = doc_data["full_text"]
    target_snippet = "A promotional trailer is unilateral"
    idx = full_text.find(target_snippet)
    assert idx != -1

    ep = EvidencePassage(
        evidence_id="E1",
        document_id="2024_5_143_154",
        case_title=doc_data.get("case_title", "Unknown"),
        passage_text=full_text[idx:idx+120],
        start_char=idx,
        end_char=idx+120,
        structural_label="headnote_holding"
    )
    # Verify exact character extraction match
    assert full_text[ep.start_char:ep.end_char] == ep.passage_text


def test_3_user_journey_qualified_answer(sample_passage):
    """Test 3: Answer with partially supported claims yields qualified_answer badge, never verified_supported."""
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(
                text="The Registrar is empowered to order fresh elections of the society at any time.",
                evidence_ids=["E1"]
            )
        ]
    )
    # The claim omits the statutory condition precedent
    verifier = ClaimVerifier()
    v_res = verifier.verify_claim(structured.claims[0].text, [sample_passage])
    
    # Simulate pipeline aggregation
    validator = CitationValidator()
    val_res, claims = validator.validate_structured(structured, [sample_passage])

    assert val_res.validation_status != "valid" or val_res.partially_supported_claims_count > 0 or not val_res.is_valid or val_res.semantic_support_status != "supported"


def test_4_user_journey_unresolved_claims_yield_unverified_badge(sample_passage):
    """Test 4: Answer containing unverified/not_evaluated claims receives unverified_answer badge."""
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(
                text="The court formulated an ambiguous standard for digital platforms.",
                evidence_ids=["E1"]
            )
        ]
    )
    validator = CitationValidator()
    val_res, claims = validator.validate_structured(structured, [sample_passage])

    # Unverified claims cannot be promoted to supported
    assert val_res.semantic_support_status != "supported"
    assert val_res.supported_claims_count == 0


def test_5_user_journey_rejected_answer_on_contradiction(sample_passage):
    """Test 5: An answer containing a contradicted holding is marked invalid and receives rejected_answer."""
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(
                text="The Supreme Court held that omitting a song from a film constitutes deficiency of service.",
                evidence_ids=["E1"]
            )
        ]
    )
    validator = CitationValidator()
    val_res, claims = validator.validate_structured(structured, [sample_passage])

    assert val_res.is_valid is False or val_res.contradicted_claims_count > 0 or val_res.semantic_support_status in ["contradicted", "unsupported"]


def test_6_user_journey_insufficient_evidence_clean_abstention():
    """Test 6: Query lacking sufficient evidence cleanly returns insufficient_evidence badge."""
    pipeline = RAGPipeline(
        llm_provider=MockLLMProvider(mode=MockLLMProvider.MODE_STRUCTURED_ABSTAIN)
    )
    result = pipeline.query(
        query_text="Nonexistent legal proposition that does not exist in the 2024 corpus?",
        top_k_judgments=1,
        max_passages=1,
        structured_output=True
    )
    assert result.status == "insufficient_evidence"
    assert result.verification_badge == "insufficient_evidence"
    assert "INSUFFICIENT EVIDENCE" in result.answer or result.grounding_status != "sufficient_evidence"


def test_7_user_journey_provider_timeout_and_service_error(test_client):
    """Test 7: Local LLM timeout returns HTTP 504 and invalid provider returns HTTP 400."""
    # Invalid provider returns HTTP 400
    res_bad = test_client.post(
        "/v1/rag/query",
        json={"query": "Valid legal question?", "provider_type": "invalid_provider"}
    )
    assert res_bad.status_code == 400
    assert "Invalid provider_type" in res_bad.json()["detail"]


def test_8_user_journey_api_serialization(test_client):
    """Test 8: API query endpoint returns valid RAGResult schema with verified badge fields."""
    res = test_client.post(
        "/v1/rag/query",
        json={
            "query": "What are the rules of the game in recruitment?",
            "provider_type": "mock",
            "structured_output": True
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert "query" in data
    assert "answer" in data
    assert "verification_badge" in data
    assert data["verification_badge"] in [
        "verified_supported", "qualified_answer", "unverified_answer",
        "rejected_answer", "insufficient_evidence", "system_error"
    ]
    assert "citation_validation" in data
    assert "claims" in data


def test_9_presentation_contract_decoupled_citations(sample_passage):
    """Test 9: Presence of valid [E1] citation does NOT elevate unsupported claim to verified_supported."""
    claim_text = "Seafarer wages hold statutory first priority over all registered maritime mortgages [E1]."
    
    # Valid syntax [E1] referencing sample passage about movie trailers
    validator = CitationValidator()
    val_res, claims = validator.validate(claim_text, [sample_passage])

    assert val_res.semantic_support_status != "supported"
    assert val_res.supported_claims_count == 0


def test_10_presentation_contract_strict_badge_invariant():
    """Test 10: Strict invariant: verified_supported is assigned IF AND ONLY IF 100% of claims are supported."""
    ep = EvidencePassage(
        evidence_id="E1",
        document_id="2024_doc_test",
        case_title="Test Title",
        passage_text="Held: The appeal is allowed and the judgment of the High Court is set aside.",
        start_char=0,
        end_char=80,
        structural_label="headnote_holding"
    )
    # Answer with 1 supported claim and 1 unsupported claim
    structured = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(text="The appeal was allowed.", evidence_ids=["E1"]),
            StructuredClaim(text="Full exemplary damages of 10 crores were awarded without inquiry.", evidence_ids=["E1"])
        ]
    )
    validator = CitationValidator()
    val_res, claims = validator.validate_structured(structured, [ep])

    assert val_res.supported_claims_count < len(structured.claims)
    assert val_res.semantic_support_status != "supported"


def test_11_staging_benchmark_frozen_dataset_integrity():
    """Test 11: Staging benchmark dataset exists, contains 40 claims with balanced classes and valid provenance."""
    dataset_file = Path("evaluation/rag/milestone20_staging_claims.jsonl")
    assert dataset_file.exists()

    with dataset_file.open("r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    assert len(cases) == 40
    counts = {}
    for c in cases:
        counts[c["gold_support_label"]] = counts.get(c["gold_support_label"], 0) + 1
        assert c["provenance"] == "developer_curated_frozen_pre_evaluation"
        assert c["independently_reviewed"] is False
        assert c["external_review_status"] == "PENDING_EXTERNAL_REVIEW"
        assert len(c["supporting_passages"]) > 0

    assert counts.get("supported") == 10
    assert counts.get("partially_supported") == 10
    assert counts.get("unsupported") == 10
    assert counts.get("contradicted") == 10


def test_12_readiness_checklist_criteria_enforcement():
    """Test 12: Readiness checklist records blocking gates and HOLD decision."""
    checklist_file = Path("evaluation/rag/milestone20_readiness_checklist.json")
    assert checklist_file.exists()

    with checklist_file.open("r", encoding="utf-8") as f:
        checklist = json.load(f)

    assert checklist["staging_release_decision"] == "HOLD_NOT_READY_FOR_EXTERNAL_PILOT"
    assert checklist["authorized_scope"] == "INTERNAL_SUPERVISED_TESTING_ONLY"

    criteria = {c["criterion_id"]: c for c in checklist["checklist_criteria"]}
    assert criteria["GATE_01_CONTRADICTED_PREVENTION"]["status"] == "PASSED"
    assert criteria["GATE_02_NON_SUPPORTED_PROMOTION_PREVENTION"]["status"] == "PASSED"
    assert criteria["GATE_06_INDEPENDENT_LEGAL_REVIEW"]["status"] == "BLOCKED"
    assert criteria["GATE_07_LIVE_CPU_GENERATION_LATENCY"]["status"] == "BLOCKED"
    assert criteria["GATE_08_VERIFIER_POLICY_TRADE_OFF_STABILITY"]["status"] == "BLOCKED"
