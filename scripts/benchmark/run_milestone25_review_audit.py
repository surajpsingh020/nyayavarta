"""
Milestone 25: Independent Legal Review and Verifier Calibration Audit.

Audits:
1. Non-mutation of all 12 historical evaluation artifacts (M20–M24).
2. Review pack integrity: 30 cases spanning 9 categories, strict blinding.
3. Review protocol completeness: 5 outcomes, source roles, context request mechanism.
4. Review status provenance: strictly PENDING_EXTERNAL_REVIEW with zero fabricated annotations.
5. Human-system comparison: strictly NOT_YET_EVALUABLE for independent review.
6. Failure taxonomy: 10 systematic legal reasoning failure modes cataloged.
7. Release gate enforcement: HOLD (NOT READY FOR EXTERNAL PILOT).
"""

import json
import hashlib
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add repository root to pythonpath
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

# Cryptographic hashes of all 12 frozen historical evaluation files
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


def verify_historical_hashes() -> Dict[str, bool]:
    """Verify that all 12 frozen historical artifacts are completely intact."""
    status = {}
    for filepath, expected_hash in FROZEN_HISTORICAL_HASHES.items():
        p = Path(filepath)
        if not p.exists():
            raise FileNotFoundError(f"Missing historical artifact: {filepath}")
        actual_hash = hashlib.sha256(p.read_bytes()).hexdigest().lower()
        assert actual_hash == expected_hash.lower(), (
            f"MUTATION DETECTED: {filepath}\nExpected: {expected_hash}\nActual:   {actual_hash}"
        )
        status[filepath] = True
    return status


def verify_review_pack_blinding_and_coverage() -> Dict[str, Any]:
    """Verify that the reviewer template is strictly blinded and covers all 9 categories."""
    template_path = Path("evaluation/rag/milestone25_reviewer_template.jsonl")
    mapping_path = Path("evaluation/rag/milestone25_frozen_mapping.json")

    assert template_path.exists(), f"Missing template file: {template_path}"
    assert mapping_path.exists(), f"Missing mapping file: {mapping_path}"

    with template_path.open("r", encoding="utf-8") as f:
        template_cases = [json.loads(line) for line in f if line.strip()]

    with mapping_path.open("r", encoding="utf-8") as f:
        mapping = json.load(f)

    assert len(template_cases) == 30, f"Expected 30 template cases, found {len(template_cases)}"
    assert len(mapping) == 30, f"Expected 30 mapping records, found {len(mapping)}"

    # Check blinding in template
    for tc in template_cases:
        cid = tc["case_id"]
        assert "target_category" not in tc, f"Blinding violation: target_category in {cid}"
        assert "sub_category" not in tc, f"Blinding violation: sub_category in {cid}"
        assert "gold_support_label" not in tc, f"Blinding violation: gold label in {cid}"
        assert "system_prediction" not in tc, f"Blinding violation: system prediction in {cid}"
        assert tc["annotation_form"]["verdict"] is None, f"Verdict not null in template {cid}"
        assert tc["metadata"]["review_status"] == "PENDING_EXTERNAL_REVIEW"

    # Check categories covered in mapping
    categories_found = set(m["curated_target_category"] for m in mapping.values())
    for exp_cat in EXPECTED_CATEGORIES:
        assert exp_cat in categories_found, f"Category {exp_cat} missing from mapping"

    return {
        "total_cases": len(template_cases),
        "blinding_verified": True,
        "categories_covered": len(categories_found)
    }


def verify_protocol_completeness() -> Dict[str, Any]:
    """Verify that the review protocol document covers the 5 outcomes and source roles."""
    protocol_path = Path("docs/MILESTONE_25_REVIEW_PROTOCOL.md")
    assert protocol_path.exists(), f"Missing protocol file: {protocol_path}"
    content = protocol_path.read_text(encoding="utf-8")

    outcomes = ["SUPPORTED", "PARTIALLY_SUPPORTED", "UNSUPPORTED", "CONTRADICTED", "AMBIGUOUS"]
    for out in outcomes:
        assert f"`{out}`" in content or out in content, f"Protocol missing outcome: {out}"

    roles = ["court_holding", "party_submission", "quoted_precedent", "facts_procedural"]
    for role in roles:
        assert role in content, f"Protocol missing source role: {role}"

    assert "requires_more_context" in content, "Protocol missing context request guidance"
    return {"protocol_valid": True, "outcomes_covered": len(outcomes)}


def verify_review_status_and_provenance() -> Dict[str, Any]:
    """Verify that review status is strictly PENDING_EXTERNAL_REVIEW with no fabricated records."""
    status_path = Path("evaluation/rag/milestone25_review_status.json")
    comp_path = Path("evaluation/rag/milestone25_human_system_comparison.json")

    assert status_path.exists(), f"Missing status file: {status_path}"
    assert comp_path.exists(), f"Missing comparison file: {comp_path}"

    with status_path.open("r", encoding="utf-8") as f:
        st = json.load(f)

    with comp_path.open("r", encoding="utf-8") as f:
        comp = json.load(f)

    assert st["review_status"] == "PENDING_EXTERNAL_REVIEW"
    assert st["external_annotations_received"] == 0
    assert len(st["external_reviewers_engaged"]) == 0
    assert st["independent_validation_completed"] is False
    assert st["release_gate_status"] == "HOLD_NOT_READY_FOR_EXTERNAL_PILOT"

    assert comp["metadata"]["independent_evaluation_status"] == "NOT_YET_EVALUABLE_PENDING_EXTERNAL_REVIEW"
    assert comp["metadata"]["external_annotations_available"] is False
    assert comp["metadata"]["genuine_external_annotations_count"] == 0

    return {
        "review_status": st["review_status"],
        "external_annotations_count": st["external_annotations_received"],
        "comparison_status": comp["metadata"]["independent_evaluation_status"],
        "provenance_intact": True
    }


def verify_failure_analysis_taxonomy() -> Dict[str, Any]:
    """Verify that all 10 legal failure modes are documented."""
    analysis_path = Path("evaluation/rag/milestone25_failure_analysis.json")
    assert analysis_path.exists(), f"Missing failure analysis file: {analysis_path}"

    with analysis_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    cats = data["failure_categories"]
    assert len(cats) == 10, f"Expected 10 failure categories, found {len(cats)}"

    for c in cats:
        assert c["category_id"].startswith("FAIL_CAT_")
        assert len(c["representative_case_ids"]) > 0
        assert c["architectural_layer"] in ["retrieval", "extraction", "verification", "presentation", "retrieval_and_budgeting", "retrieval_and_structural_classification", "generation_and_verification", "extraction_and_verification", "retrieval_and_presentation"]

    return {"total_failure_categories": len(cats)}


def main():
    print("=" * 80)
    print("NYAYAVARTA MILESTONE 25: INDEPENDENT LEGAL REVIEW & AUDIT")
    print("=" * 80)

    # 1. Historical File Non-Mutation Check
    print("\n[Step 1] Verifying non-mutation of all 12 frozen historical artifacts (M20–M24)...")
    hashes = verify_historical_hashes()
    for fp in hashes:
        print(f"  OK: {fp} (hash verified)")

    # 2. Review Pack & Blinding Check
    print("\n[Step 2] Verifying Milestone 25 review pack blinding and coverage...")
    pack_res = verify_review_pack_blinding_and_coverage()
    print(f"  OK: {pack_res['total_cases']} cases in template, 0 leaks, all 9 legal categories covered.")

    # 3. Review Protocol Check
    print("\n[Step 3] Verifying Milestone 25 review protocol completeness...")
    prot_res = verify_protocol_completeness()
    print(f"  OK: Protocol covers all 5 outcomes, source roles, and context request mechanism.")

    # 4. Review Status Provenance Check
    print("\n[Step 4] Auditing independent review status and provenance tracking...")
    st_res = verify_review_status_and_provenance()
    print(f"  Status:              {st_res['review_status']}")
    print(f"  External Annotations:{st_res['external_annotations_count']} (0 fabricated records)")
    print(f"  Comparison Status:   {st_res['comparison_status']}")

    # 5. Failure Analysis Check
    print("\n[Step 5] Auditing systematic failure taxonomy...")
    fail_res = verify_failure_analysis_taxonomy()
    print(f"  OK: {fail_res['total_failure_categories']} systematic failure categories cataloged.")

    # 6. Release Decision
    print("\n" + "=" * 80)
    print("RELEASE GATE DECISION: HOLD (NOT READY FOR EXTERNAL PILOT)")
    print("=" * 80)
    print("Rationale:")
    print("  1. The blinded review pack and protocol are prepared and frozen for external use.")
    print("  2. External legal panel annotations remain PENDING_EXTERNAL_REVIEW.")
    print("  3. Independent human-system comparison is marked NOT_YET_EVALUABLE.")
    print("  4. No external pilot or production deployment is permitted until genuine,")
    print("     independent legal annotations are received and reconciled.")
    print("=" * 80)


if __name__ == "__main__":
    main()
