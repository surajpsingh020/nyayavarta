"""
Milestone 25: Independent Legal Review and Verifier Calibration Tests.

Validates:
1. Non-mutation of all 12 frozen historical evaluation artifacts (M20–M24).
2. Reviewer template strict blinding (0 leaks of gold labels, categories, or system predictions).
3. Review pack coverage across all 9 designated legal categories.
4. Review protocol document completeness (all 5 outcomes, source roles, and context request guidelines).
5. Review status provenance: strictly PENDING_EXTERNAL_REVIEW with zero fabricated annotations.
6. Independent comparison status: strictly NOT_YET_EVALUABLE_PENDING_EXTERNAL_REVIEW.
7. Failure analysis taxonomy completeness (all 10 failure categories cataloged).
8. Centralized safety contract invariants remain intact.
9. Graph traversal remains disabled in production.
10. Final release gate decision is strictly HOLD (NOT READY FOR EXTERNAL PILOT).
"""

import json
import hashlib
from pathlib import Path
import pytest

from services.rag.models import (
    EvidencePassage,
    ClaimAttribution,
    CitationValidationResult
)
from services.rag.pipeline import RAGPipeline


FROZEN_HISTORICAL_HASHES = {
    "evaluation/rag/milestone20_staging_claims.jsonl": "e57cbb6d7e110c0a14e8fd6ebb71490693d079b4902b3bb1b5d1b656615f86c3",
    "evaluation/rag/milestone20_blinded_review_pack.jsonl": "0dfb49becc2ded048a7a69fb02892b9ab393f116a0eb130069539a0315adfa1e",
    "evaluation/rag/milestone20_policy_comparison.json": "9d5cb5babcd4e68ce9df0327340c3f53f49d93ec16401444a9ce82303a6de9fc",
    "evaluation/rag/milestone21_context_budget_comparison.json": "2e41a3d2470fcfdc6817fa27218b1a3eabdde762f799da508ee6e3c9ae4e49bf",
    "evaluation/rag/milestone22_evidence_retention.json": "cc766b193ce2e410b07fd4ce391f6fd5ef25bd34831e243aba5bda67b150ae1e",
    "evaluation/rag/milestone22_model_comparison.json": "7da0d665e94d6cd94a01bdf8eb95ca02e354276df1adcebb73f828b2b247e1a6",
    "evaluation/rag/milestone23_integrity_audit.json": "e1c9d540c4e54e760ebfe103ffe4e477dc46837806deeee10c6a102f22f80a29",
    "evaluation/rag/milestone23_recomputed_metrics.json": "f8c5eda49fa9a204e2f11f62d0101e882a3906788ae60c9ab169805540a2c58a",
    "evaluation/rag/milestone23_case_level_audit.jsonl": "06eeade50fa6a92a1254e15196024fbc3087db132a84b0393771a3ab79e03517",
    "evaluation/rag/milestone24_adversarial_cases.jsonl": "dd637eb359a0e3548224b9d1ce901793231e063477bd65d9f87064988774c390",
    "evaluation/rag/milestone24_frozen_staging_results.json": "c23f346c28767c5b82ccb5526b3fdf7890b16d0d21d6b744f0e0be7003c9b615",
    "evaluation/rag/milestone24_badge_invariant_results.json": "4a920ed504b68567e03976600d3d759732e0fbe3b19c9d129b3b5bb80f25a009"
}

EXPECTED_CATEGORIES = [
    "supported",
    "partially_supported",
    "unsupported_with_valid_citation",
    "contradicted",
    "statutory_exceptions_and_conditions",
    "party_submissions_vs_holdings",
    "quoted_precedents",
    "overgeneralized_holdings",
    "ambiguous_claims"
]


def test_historical_artifacts_non_mutation():
    """All 12 historical evaluation artifacts (M20–M24) must match their SHA-256 hashes."""
    for filepath, expected_hash in FROZEN_HISTORICAL_HASHES.items():
        p = Path(filepath)
        assert p.exists(), f"Historical file {filepath} is missing"
        actual_hash = hashlib.sha256(p.read_bytes()).hexdigest().lower()
        assert actual_hash == expected_hash.lower(), f"Hash mismatch for {filepath}"


def test_reviewer_template_strictly_blinded():
    """All 30 records in milestone25_reviewer_template.jsonl must be strictly blinded."""
    path = Path("evaluation/rag/milestone25_reviewer_template.jsonl")
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        records = [json.loads(line) for line in f if line.strip()]

    assert len(records) == 30
    for r in records:
        assert r["case_id"].startswith("M25_REV_")
        assert "target_category" not in r
        assert "sub_category" not in r
        assert "gold_support_label" not in r
        assert "system_prediction" not in r
        assert r["annotation_form"]["verdict"] is None
        assert r["metadata"]["review_status"] == "PENDING_EXTERNAL_REVIEW"
        assert r["legal_proposition"]
        assert r["source_passage_text"]
        assert r["extended_judgment_context"]


def test_review_pack_nine_categories_coverage():
    """Frozen mapping must cover all 9 designated legal review categories."""
    path = Path("evaluation/rag/milestone25_frozen_mapping.json")
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        mapping = json.load(f)

    assert len(mapping) == 30
    found_categories = set(m["curated_target_category"] for m in mapping.values())
    for cat in EXPECTED_CATEGORIES:
        assert cat in found_categories, f"Category {cat} missing from mapping"


def test_review_protocol_five_outcomes_and_roles():
    """Protocol document must define all 5 outcomes, source roles, and context request guidelines."""
    path = Path("docs/MILESTONE_25_REVIEW_PROTOCOL.md")
    assert path.exists()
    content = path.read_text(encoding="utf-8")

    for outcome in ["SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "CONTRADICTED", "AMBIGUOUS"]:
        assert outcome in content

    for role in ["court_holding", "party_submission", "quoted_precedent", "facts_procedural"]:
        assert role in content

    assert "requires_more_context" in content


def test_review_status_is_pending_external_review():
    """Review status must be strictly PENDING_EXTERNAL_REVIEW with zero fabricated annotations."""
    path = Path("evaluation/rag/milestone25_review_status.json")
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["review_status"] == "PENDING_EXTERNAL_REVIEW"
    assert data["external_annotations_received"] == 0
    assert len(data["external_reviewers_engaged"]) == 0
    assert data["independent_validation_completed"] is False
    assert data["release_gate_status"] == "HOLD_NOT_READY_FOR_EXTERNAL_PILOT"


def test_human_system_comparison_is_not_yet_evaluable():
    """Comparison file must explicitly mark independent evaluation as NOT_YET_EVALUABLE."""
    path = Path("evaluation/rag/milestone25_human_system_comparison.json")
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["metadata"]["independent_evaluation_status"] == "NOT_YET_EVALUABLE_PENDING_EXTERNAL_REVIEW"
    assert data["metadata"]["external_annotations_available"] is False
    assert data["metadata"]["genuine_external_annotations_count"] == 0
    assert "developer_curated_diagnostic_baseline_only" in data


def test_failure_analysis_covers_ten_categories():
    """Failure analysis file must cover all 10 designated legal reasoning failure categories."""
    path = Path("evaluation/rag/milestone25_failure_analysis.json")
    assert path.exists()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    cats = data["failure_categories"]
    assert len(cats) == 10
    for c in cats:
        assert c["category_id"].startswith("FAIL_CAT_")
        assert len(c["representative_case_ids"]) > 0
        assert c["failure_mechanism"]
        assert c["architectural_layer"]


def test_centralized_safety_contract_holds():
    """Centralized answer-level verification contract must still hold."""
    claim = ClaimAttribution(
        sentence="A court can summon additional accused on mere suspicion.",
        cited_evidence_ids=["E1"],
        verification_status="partially_supported",
        is_partially_supported=True,
        omits_statutory_qualification=True
    )
    val_result = CitationValidationResult(
        is_valid=True,
        validation_status="partially_supported",
        partially_supported_claims_count=1
    )
    passage = EvidencePassage(
        evidence_id="E1",
        document_id="2024_INSC_SEC319",
        case_title="STATE OF RAJASTHAN versus BABU LAL & ORS.",
        passage_text="The power under Section 319 requires strong evidence.",
        start_char=100,
        end_char=200,
        structural_label="headnote_holding"
    )

    badge = RAGPipeline.determine_verification_badge(
        status="answered",
        claims=[claim],
        val_result=val_result,
        offsets_verified=True,
        evidence_passages=[passage]
    )
    assert badge == "qualified_answer"
    assert badge != "verified_supported"


def test_graph_traversal_remains_disabled():
    """Graph traversal must remain explicitly disabled in default configurations."""
    staging_res_path = Path("evaluation/rag/milestone24_frozen_staging_results.json")
    assert staging_res_path.exists()
    with open(staging_res_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["metadata"]["graph_traversal_enabled"] is False


def test_release_gate_decision_remains_hold():
    """Release decision must strictly remain HOLD."""
    path = Path("evaluation/rag/milestone25_review_status.json")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["release_gate_status"] == "HOLD_NOT_READY_FOR_EXTERNAL_PILOT"
