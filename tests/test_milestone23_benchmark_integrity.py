"""
Test Suite for Milestone 23: Benchmark Integrity Audit and Independent Review Readiness.

Validates:
1. Frozen dataset immutability and cryptographic hash verification.
2. Confusion matrix totals equal total evaluated records (40).
3. Every reported metric mathematically matches its numerator / denominator.
4. Claim-level FAR and answer-level false verification are strictly decoupled.
5. Explicit accounting of missing labels and NOT_EVALUATED predictions.
6. Evidence character counts and token counts use clearly separated fields.
7. Valid citation ID does not imply semantic verification.
8. Safety invariants: No contradicted, partially supported, or unverified claim receives verified_supported badge.
9. Final presentation badge agrees with claim states and validation results.
10. Blinded review pack integrity and PENDING_EXTERNAL_REVIEW status.
"""

import json
import hashlib
from pathlib import Path
import pytest

from services.rag.models import (
    EvidencePassage,
    CitationValidationResult,
    ClaimAttribution
)
from services.rag.claim_verifier import (
    ClaimVerifier,
    ClaimVerificationResult,
    ClaimVerificationStatus
)
from services.rag.pipeline import RAGPipeline


FROZEN_FILE_HASHES = {
    "evaluation/rag/milestone20_staging_claims.jsonl": "e57cbb6d7e110c0a14e8fd6ebb71490693d079b4902b3bb1b5d1b656615f86c3",
    "evaluation/rag/milestone20_blinded_review_pack.jsonl": "0dfb49becc2ded048a7a69fb02892b9ab393f116a0eb130069539a0315adfa1e",
    "evaluation/rag/milestone20_policy_comparison.json": "9d5cb5babcd4e68ce9df0327340c3f53f49d93ec16401444a9ce82303a6de9fc",
    "evaluation/rag/milestone21_context_budget_comparison.json": "2e41a3d2470fcfdc6817fa27218b1a3eabdde762f799da508ee6e3c9ae4e49bf",
    "evaluation/rag/milestone22_evidence_retention.json": "cc766b193ce2e410b07fd4ce391f6fd5ef25bd34831e243aba5bda67b150ae1e",
    "evaluation/rag/milestone22_model_comparison.json": "7da0d665e94d6cd94a01bdf8eb95ca02e354276df1adcebb73f828b2b247e1a6",
}


def test_frozen_dataset_hashes_unmutated():
    """Verify that all historical evaluation artifacts match their frozen SHA-256 hashes."""
    for rel_path, expected_hash in FROZEN_FILE_HASHES.items():
        p = Path(rel_path)
        assert p.exists(), f"Historical file {rel_path} does not exist"
        actual_hash = hashlib.sha256(p.read_bytes()).hexdigest()
        assert actual_hash == expected_hash, (
            f"MUTATION DETECTED in {rel_path}!\nExpected: {expected_hash}\nActual:   {actual_hash}"
        )


def test_recomputed_metrics_confusion_matrix_sum():
    """Verify that confusion-matrix cell totals in all policies strictly equal the record count (40)."""
    p = Path("evaluation/rag/milestone23_recomputed_metrics.json")
    assert p.exists(), "milestone23_recomputed_metrics.json missing"
    data = json.loads(p.read_text(encoding="utf-8"))

    for pol_key, pol_data in data.items():
        matrix = pol_data["confusion_matrix"]
        total_records = pol_data["total_records"]
        assert total_records == 40, f"{pol_key} record count should be 40, got {total_records}"

        matrix_sum = sum(
            matrix[gold][pred]
            for gold in matrix
            for pred in matrix[gold]
        )
        assert matrix_sum == 40, (
            f"Confusion matrix for {pol_key} sums to {matrix_sum}, expected {total_records}"
        )


def test_every_reported_percentage_matches_numerator_denominator():
    """Verify that every percentage matches round(numerator / denominator, 4) in recomputed metrics."""
    p = Path("evaluation/rag/milestone23_recomputed_metrics.json")
    data = json.loads(p.read_text(encoding="utf-8"))

    for pol_key, pol_data in data.items():
        metrics = pol_data["metrics"]
        for m_name, m_info in metrics.items():
            num = m_info["numerator"]
            den = m_info["denominator"]
            val = m_info["value"]
            if isinstance(num, (int, float)) and isinstance(den, (int, float)) and den > 0:
                expected_val = round(num / den, 4)
                assert val == expected_val, (
                    f"Mismatch in {pol_key} {m_name}: val={val}, num={num}, den={den}, expected={expected_val}"
                )


def test_claim_level_and_answer_level_metrics_cannot_be_interchanged():
    """Verify that claim-level non-supported FAR and answer-level false verification are distinct metrics."""
    p = Path("evaluation/rag/milestone23_recomputed_metrics.json")
    data = json.loads(p.read_text(encoding="utf-8"))

    p3_metrics = data["policy_3"]["metrics"]
    claim_far = p3_metrics["non_supported_far"]
    answer_far = p3_metrics["answer_level_false_verification_rate"]

    # Verify distinct units of analysis
    assert claim_far["unit"] == "claim"
    assert answer_far["unit"] == "answer"

    # In Policy 3, claim-level FAR is 5/30 = 0.1667
    assert claim_far["numerator"] == 5
    assert claim_far["denominator"] == 30
    assert claim_far["value"] == 0.1667

    # Answer-level false verification is evaluated on whole answer objects
    assert answer_far["unit"] == "answer"
    assert answer_far["denominator"] == 40


def test_missing_labels_and_not_evaluated_accounted_explicitly():
    """Verify that not_evaluated predictions are tracked with exact counts and rates."""
    p = Path("evaluation/rag/milestone23_recomputed_metrics.json")
    data = json.loads(p.read_text(encoding="utf-8"))

    # In Policy 3: 12 claims are not_evaluated (3 supported, 4 partial, 2 unsupported, 3 contradicted)
    p3_not_eval = data["policy_3"]["metrics"]["not_evaluated_rate"]
    assert p3_not_eval["numerator"] == 12
    assert p3_not_eval["denominator"] == 40
    assert p3_not_eval["value"] == 0.3000

    # In Policy 4: 23 claims are not_evaluated due to hybrid uncertainty
    p4_not_eval = data["policy_4"]["metrics"]["not_evaluated_rate"]
    assert p4_not_eval["numerator"] == 23
    assert p4_not_eval["denominator"] == 40
    assert p4_not_eval["value"] == 0.5750


def test_evidence_characters_and_tokens_distinct_fields():
    """Verify that M23 audit explicitly differentiates character counts from actual tokenizer counts."""
    p = Path("evaluation/rag/milestone23_integrity_audit.json")
    assert p.exists(), "milestone23_integrity_audit.json missing"
    data = json.loads(p.read_text(encoding="utf-8"))

    phase_a = data["phase_a_evidence_budget_audit"]
    m22_tok = phase_a["m22_budget_audit"]["token_measurement_comparison"]

    assert "total_characters" in m22_tok
    assert "heuristic_estimated_tokens" in m22_tok
    assert "actual_bge_minilm_tokens" in m22_tok
    assert "chars_per_actual_token" in m22_tok

    # Verify that heuristic token count exceeds actual BGE/MiniLM token count
    assert m22_tok["heuristic_estimated_tokens"] > m22_tok["actual_bge_minilm_tokens"]
    assert m22_tok["chars_per_actual_token"] > 4.5


def test_valid_citation_id_does_not_imply_semantic_support():
    """Verify that a valid citation ID does not bypass verifier or force verified_supported."""
    # Build a test passage and contradictory claim that references citation [E1]
    passage = EvidencePassage(
        evidence_id="E1",
        document_id="2024_8_647_655",
        start_char=1000,
        end_char=1800,
        passage_text=(
            "The High Court fell in error in directing deposit of 20% of the compensation "
            "under Section 148 of the Negotiable Instruments Act. The appellant was merely an "
            "authorized signatory of the company and not the drawer of the cheque. An authorized "
            "signatory who is not the drawer could not be directed to pay interim compensation "
            "under Section 148. The impugned condition is accordingly set aside."
        ),
        case_title="Bijay Agarwal v. M/s Medilines",
        structural_label="judicial_holding"
    )
    verifier = ClaimVerifier()
    claim_text = "The Appellate Court may order an authorized signatory to deposit interim compensation under Section 148."
    res = verifier.verify_claim(claim_text, [passage])

    # Verifier must detect contradiction despite matching citation ID E1
    assert res.status == ClaimVerificationStatus.CONTRADICTED
    assert res.is_contradicted is True


def test_safety_badge_invariants_fail_closed():
    """Verify determine_verification_badge never awards verified_supported to non-supported answers."""
    # 1. Contradicted claim in answer
    v_contra = CitationValidationResult(
        is_valid=False,
        validation_status="contradicted",
        semantic_support_status="contradicted",
        contradicted_claims_count=1,
        supported_claims_count=0,
        attribution_complete=True
    )
    badge_contra = RAGPipeline.determine_verification_badge("validation_failed", v_contra, [{}])
    assert badge_contra == "rejected_answer"

    # 2. Partially supported claim in answer
    v_partial = CitationValidationResult(
        is_valid=True,
        validation_status="partially_supported",
        semantic_support_status="partially_supported",
        partially_supported_claims_count=1,
        supported_claims_count=0,
        attribution_complete=True
    )
    badge_partial = RAGPipeline.determine_verification_badge("answered_with_qualification", v_partial, [{}])
    assert badge_partial == "qualified_answer"

    # 3. Unsupported claim in answer
    v_unsupp = CitationValidationResult(
        is_valid=False,
        validation_status="unsupported",
        semantic_support_status="unsupported",
        unsupported_claims_count=1,
        supported_claims_count=0,
        attribution_complete=True
    )
    badge_unsupp = RAGPipeline.determine_verification_badge("validation_failed", v_unsupp, [{}])
    assert badge_unsupp in ["rejected_answer", "unverified_answer"]
    assert badge_unsupp != "verified_supported"

    # 4. Mixed claims: 1 supported + 1 partially supported
    v_mixed = CitationValidationResult(
        is_valid=True,
        validation_status="partially_supported",
        semantic_support_status="partially_supported",
        supported_claims_count=1,
        partially_supported_claims_count=1,
        contradicted_claims_count=0,
        unsupported_claims_count=0,
        attribution_complete=True
    )
    badge_mixed = RAGPipeline.determine_verification_badge("answered", v_mixed, [{}, {}])
    assert badge_mixed != "verified_supported"
    assert badge_mixed in ["qualified_answer", "unverified_answer"]


def test_case_level_audit_table_completeness():
    """Verify that milestone23_case_level_audit.jsonl contains 40 cases with the 10-step audit chain."""
    p = Path("evaluation/rag/milestone23_case_level_audit.jsonl")
    assert p.exists(), "milestone23_case_level_audit.jsonl missing"

    lines = [json.loads(l) for l in p.open("r", encoding="utf-8") if l.strip()]
    assert len(lines) == 40, f"Expected 40 records, found {len(lines)}"

    required_keys = [
        "case_id", "query_id", "1_input_query", "2_selected_evidence",
        "3_generated_model_output", "4_extracted_claims",
        "5_claim_verifier_states_and_scores", "6_citation_validation_results",
        "7_final_pipeline_status", "8_final_presentation_badge",
        "9_gold_label_and_adjudication", "10_safety_invariant_violation"
    ]

    for item in lines:
        for k in required_keys:
            assert k in item, f"Missing required step {k} in {item.get('case_id')}"

        # External review must be pending
        assert item["9_gold_label_and_adjudication"]["external_review_status"] == "PENDING_EXTERNAL_REVIEW"


def test_independent_review_pack_is_pending():
    """Verify that all 30 cases in the blinded review pack remain PENDING_EXTERNAL_REVIEW."""
    pack_path = Path("evaluation/rag/milestone20_blinded_review_pack.jsonl")
    cases = [json.loads(l) for l in pack_path.open("r", encoding="utf-8") if l.strip()]
    assert len(cases) == 30

    for c in cases:
        assert c["review_status"] == "PENDING_EXTERNAL_REVIEW"
        assert c["reviewer_verdict"] is None
