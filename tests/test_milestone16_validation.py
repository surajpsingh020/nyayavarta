"""Milestone 16 Regression Test Suite: Independent Legal Review & External Validation.

Tests:
1. Reviewer Pack Schema, Completeness, and Blinding Integrity.
2. Reviewer Annotation Validation (rejection of invalid enums, missing rationale, unknown IDs).
3. Secret Ground Truth Mapping Integrity.
4. Statistical Agreement Metrics (Cohen's Kappa).
5. Safe Answer Presentation Contract Enforcement.
6. Milestone 16 Unseen Evaluation Dataset and Results Integrity.
"""

import json
import pytest
from pathlib import Path

from services.rag.models import (
    ClaimAttribution,
    EvidencePassage,
    StructuredAnswer,
    StructuredClaim,
    CitationValidationResult,
    RAGResult,
)
from services.rag.claim_verifier import (
    ClaimVerifier,
    ClaimVerificationStatus,
)
from services.rag.validator import CitationValidator
from scripts.benchmark.evaluate_milestone16_review import (
    validate_reviewer_pack,
    load_and_validate_review_file,
    compute_metrics,
    compute_cohens_kappa,
    evaluate_pack_against_mapping,
    VALID_LABELS,
)


@pytest.fixture
def pack_path():
    return Path("evaluation/rag/milestone16_reviewer_pack.jsonl")


@pytest.fixture
def mapping_path():
    return Path("evaluation/rag/milestone16_reviewer_mapping.json")


@pytest.fixture
def unseen_claims_path():
    return Path("evaluation/rag/milestone16_unseen_claims.jsonl")


@pytest.fixture
def evaluation_results_path():
    return Path("evaluation/rag/milestone16_evaluation_results.json")


# ---------------------------------------------------------------------------
# Test 1: Reviewer Pack Schema, Completeness, and Blinding
# ---------------------------------------------------------------------------
def test_reviewer_pack_schema_and_blinding(pack_path, mapping_path):
    """Ensure pack contains at least 30 cases, all required fields, and zero internal leakage."""
    assert pack_path.exists(), "Reviewer pack JSONL must exist"
    valid, errors = validate_reviewer_pack(pack_path, mapping_path)
    assert valid, f"Pack validation failed: {errors}"

    lines = [json.loads(line) for line in pack_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(lines) >= 30, f"Expected at least 30 blinded cases, found {len(lines)}"

    for case in lines:
        assert case["case_id"].startswith("M16_REV_"), f"Invalid ID format: {case['case_id']}"
        assert case["reviewer_label"] is None, "Pack must have null reviewer_label"
        assert case["reviewer_rationale"] is None, "Pack must have null reviewer_rationale"
        assert "[PRECEDING TEXT]" in case["surrounding_context"], "Must contain preceding context marker"
        assert "[CITED EVIDENCE PASSAGE]" in case["surrounding_context"], "Must contain cited passage marker"
        assert "[SUCCEEDING TEXT]" in case["surrounding_context"], "Must contain succeeding context marker"


# ---------------------------------------------------------------------------
# Test 2: Mapping File Integrity and Coverage
# ---------------------------------------------------------------------------
def test_reviewer_mapping_integrity(mapping_path, pack_path):
    """Ensure mapping file covers every case in the pack with complete gold and predicted metadata."""
    assert mapping_path.exists(), "Mapping file must exist"
    mapping_data = json.loads(mapping_path.read_text(encoding="utf-8"))
    cases = mapping_data.get("cases", mapping_data)

    pack_lines = [json.loads(l) for l in pack_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    pack_ids = {c["case_id"] for c in pack_lines}

    assert set(cases.keys()) == pack_ids, "Mapping cases must match pack cases exactly"

    for cid, cinfo in cases.items():
        assert cinfo["gold_support_label"] in VALID_LABELS
        assert cinfo["system_predicted_status"] in VALID_LABELS
        assert "original_review_id" in cinfo
        assert "system_verification_method" in cinfo


# ---------------------------------------------------------------------------
# Test 3: Rejection of Invalid Reviewer Inputs
# ---------------------------------------------------------------------------
def test_reviewer_submission_validation_rejection(tmp_path):
    """Verify that malformed or invalid reviewer submissions are rejected with clear errors."""
    expected_ids = {"M16_REV_001", "M16_REV_002"}

    # Case A: Invalid label enum
    bad_file = tmp_path / "bad_label.jsonl"
    bad_file.write_text(json.dumps({
        "case_id": "M16_REV_001",
        "reviewer_label": "somewhat_true",  # invalid
        "reviewer_rationale": "Valid length rationale explaining why.",
        "confidence": "high",
        "reviewer_id": "REV_01"
    }) + "\n", encoding="utf-8")

    reviews, errors = load_and_validate_review_file(bad_file, expected_ids)
    assert reviews is None
    assert any("Invalid label" in e for e in errors)

    # Case B: Unknown case ID
    bad_id_file = tmp_path / "bad_id.jsonl"
    bad_id_file.write_text(json.dumps({
        "case_id": "M16_REV_999",  # unknown
        "reviewer_label": "supported",
        "reviewer_rationale": "Valid length rationale explaining why.",
        "confidence": "high",
        "reviewer_id": "REV_01"
    }) + "\n", encoding="utf-8")

    reviews, errors = load_and_validate_review_file(bad_id_file, expected_ids)
    assert reviews is None
    assert any("Unknown case_id" in e for e in errors)

    # Case C: Insufficient rationale
    short_rationale_file = tmp_path / "short_rationale.jsonl"
    short_rationale_file.write_text(json.dumps({
        "case_id": "M16_REV_001",
        "reviewer_label": "supported",
        "reviewer_rationale": "Short",  # < 10 chars
        "confidence": "high",
        "reviewer_id": "REV_01"
    }) + "\n", encoding="utf-8")

    reviews, errors = load_and_validate_review_file(short_rationale_file, expected_ids)
    assert reviews is None
    assert any("insufficient" in e for e in errors)


# ---------------------------------------------------------------------------
# Test 4: Statistical Metrics and Inter-Annotator Agreement
# ---------------------------------------------------------------------------
def test_cohens_kappa_calculation():
    """Verify Cohen's Kappa computes exact values for identical, partial, and inverse raters."""
    labels = ["supported", "partially_supported", "unsupported", "contradicted", "not_evaluated"]

    # Identical ratings -> Kappa = 1.0
    r1 = ["supported", "partially_supported", "contradicted", "unsupported"]
    r2 = ["supported", "partially_supported", "contradicted", "unsupported"]
    assert pytest.approx(compute_cohens_kappa(r1, r2, labels), 0.001) == 1.0

    # Orthogonal ratings -> Kappa <= 0.0
    r3 = ["supported", "supported", "supported", "supported"]
    r4 = ["contradicted", "contradicted", "contradicted", "contradicted"]
    assert compute_cohens_kappa(r3, r4, labels) <= 0.0


# ---------------------------------------------------------------------------
# Test 5: Safe Answer Presentation Contract Enforcement
# ---------------------------------------------------------------------------
def test_answer_presentation_contract_safety():
    """Verify that an answer is NEVER promoted to verified_supported if any claim is non-supported."""
    validator = CitationValidator()

    p1 = EvidencePassage(
        evidence_id="E1",
        document_id="doc1",
        case_title="Case 1",
        passage_text="Caste-based labor segregation in prisons violates Article 14 and Article 21.",
        start_char=0,
        end_char=80,
        structural_label="headnote_holding"
    )
    p2 = EvidencePassage(
        evidence_id="E2",
        document_id="doc2",
        case_title="Case 2",
        passage_text="rules of the game must not be changed during the course of the game. The rules cannot be changed midway.",
        start_char=0,
        end_char=110,
        structural_label="judicial_holding"
    )

    # Mixed answer: one supported, one contradicted
    sa = StructuredAnswer(
        status="answer",
        claims=[
            StructuredClaim(text="Caste-based labor segregation in prisons violates the Constitution.", evidence_ids=["E1"]),
            StructuredClaim(text="The recruiting authority is empowered to alter qualification criteria midway.", evidence_ids=["E2"])
        ]
    )

    val_res, claims_attr = validator.validate_structured(sa, [p1, p2])
    policy = ClaimVerifier.evaluate_acceptance_policy(val_res, claims_attr)

    # Acceptance policy must reject or qualify, NEVER promote to fully supported
    assert val_res.is_valid is False
    assert val_res.validation_status == "contradicted"
    assert val_res.contradicted_claims_count == 1

    assert policy["is_valid"] is False
    assert policy["accepted_status"] == "validation_failed"
    assert policy["accepted_status"] != "answered"


# ---------------------------------------------------------------------------
# Test 6: Milestone 16 Unseen Claims Dataset and Results
# ---------------------------------------------------------------------------
def test_milestone16_unseen_claims_dataset_integrity(unseen_claims_path, evaluation_results_path):
    """Verify that the unseen evaluation dataset contains 20 claims from unstudied judgments."""
    assert unseen_claims_path.exists(), "Unseen claims JSONL must exist"
    assert evaluation_results_path.exists(), "Evaluation results JSON must exist"

    lines = [json.loads(l) for l in unseen_claims_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) >= 20, f"Expected 20 unseen claims, found {len(lines)}"

    doc_ids = {c["supporting_passages"][0]["document_id"] for c in lines}
    assert len(doc_ids) == 20, f"All 20 claims must be from 20 distinct judgments, found {len(doc_ids)}"

    # Check results file
    results = json.loads(evaluation_results_path.read_text(encoding="utf-8"))
    assert results["total_unseen_claims"] == 20
    assert results["safe_answer_aggregation"]["safe_promotions_violated"] == 3
    assert results["evaluation_metrics"]["per_class_metrics"]["supported"]["recall"] == 1.0


# ---------------------------------------------------------------------------
# Test 7: Reviewer Pack Evaluation Runner CLI
# ---------------------------------------------------------------------------
def test_evaluation_runner_mapping_benchmark(mapping_path, pack_path):
    """Verify that evaluate_pack_against_mapping executes and verifies internal safety compliance."""
    res = evaluate_pack_against_mapping(mapping_path)
    assert res["pack_case_count"] == 36
    assert res["review_status"] == "PENDING_EXTERNAL_REVIEW"
    assert res["system_vs_gold_benchmark"]["answer_level_safety"]["safe_promotions_violated"] == 0
    assert res["system_vs_gold_benchmark"]["answer_level_safety"]["safety_compliance_rate"] == 1.0
