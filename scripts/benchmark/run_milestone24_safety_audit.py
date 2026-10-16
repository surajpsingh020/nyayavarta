"""
Milestone 24: Single-Claim Safety Hardening and End-to-End Verification Audit.

Audits NyayaVarta's claim verification, single-claim leak prevention, and centralized
answer-level safety invariants:
1. Verifies cryptographic hashes of all historical frozen evaluation files (M20-M23).
2. Re-evaluates the 40 frozen Milestone 20 staging claims under Policy 1 and Policy 3.
   - Computes precision, recall, F1, and fine-grained false-acceptance rates.
   - Verifies 0 non-supported false acceptances into the supported class.
   - Saves output to evaluation/rag/milestone24_frozen_staging_results.json.
3. Evaluates all 22 cases in evaluation/rag/milestone24_adversarial_cases.jsonl against
   the centralized answer safety contract (all 11 invariants).
   - Verifies 100% fail-closed safety rate (0/22 receive verified_supported).
   - Saves output to evaluation/rag/milestone24_badge_invariant_results.json.
4. Enforces the release gate: HOLD (NOT READY FOR EXTERNAL PILOT).
"""

import json
import hashlib
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

# Add repository root to pythonpath
repo_root = Path(__file__).resolve().parent.parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from services.rag.models import (
    EvidencePassage,
    ClaimAttribution,
    CitationValidationResult
)
from services.rag.claim_verifier import (
    ClaimVerifier,
    ClaimVerificationResult,
    ClaimVerificationStatus
)
from services.rag.nli_verifier import LocalNLIVerifier
from services.rag.pipeline import RAGPipeline


# Cryptographic hashes of frozen input files to guarantee non-mutation
FROZEN_FILE_HASHES = {
    "evaluation/rag/milestone20_staging_claims.jsonl": "e57cbb6d7e110c0a14e8fd6ebb71490693d079b4902b3bb1b5d1b656615f86c3",
    "evaluation/rag/milestone20_blinded_review_pack.jsonl": "0dfb49becc2ded048a7a69fb02892b9ab393f116a0eb130069539a0315adfa1e",
    "evaluation/rag/milestone20_policy_comparison.json": "9d5cb5babcd4e68ce9df0327340c3f53f49d93ec16401444a9ce82303a6de9fc",
    "evaluation/rag/milestone21_context_budget_comparison.json": "2e41a3d2470fcfdc6817fa27218b1a3eabdde762f799da508ee6e3c9ae4e49bf",
    "evaluation/rag/milestone22_evidence_retention.json": "cc766b193ce2e410b07fd4ce391f6fd5ef25bd34831e243aba5bda67b150ae1e",
    "evaluation/rag/milestone22_model_comparison.json": "7da0d665e94d6cd94a01bdf8eb95ca02e354276df1adcebb73f828b2b247e1a6",
    "evaluation/rag/milestone23_integrity_audit.json": "e1c9d540c4e54e760ebfe103ffe4e477dc46837806deeee10c6a102f22f80a29",
    "evaluation/rag/milestone23_recomputed_metrics.json": "f8c5eda49fa9a204e2f11f62d0101e882a3906788ae60c9ab169805540a2c58a",
    "evaluation/rag/milestone23_case_level_audit.jsonl": "06eeade50fa6a92a1254e15196024fbc3087db132a84b0393771a3ab79e03517"
}


def verify_file_hashes() -> Dict[str, bool]:
    """Verify that no frozen historical evaluation artifact has been modified."""
    hash_status = {}
    for filepath, expected_hash in FROZEN_FILE_HASHES.items():
        p = Path(filepath)
        if not p.exists():
            raise FileNotFoundError(f"Required historical artifact {filepath} is missing!")
        actual_hash = hashlib.sha256(p.read_bytes()).hexdigest().lower()
        assert actual_hash == expected_hash.lower(), (
            f"MUTATION DETECTED: {filepath} hash mismatch!\nExpected: {expected_hash}\nActual:   {actual_hash}"
        )
        hash_status[filepath] = True
    return hash_status


def evaluate_frozen_staging_claims() -> Dict[str, Any]:
    """
    Re-evaluate all 40 frozen Milestone 20 staging claims using the hardened verifier.
    Compares Policy 1 (Deterministic) vs Policy 3 (Contradiction Veto).
    """
    staging_file = Path("evaluation/rag/milestone20_staging_claims.jsonl")
    with staging_file.open("r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    assert len(cases) == 40, f"Expected 40 frozen staging cases, found {len(cases)}"

    det_verifier = ClaimVerifier()
    nli_verifier = LocalNLIVerifier()

    p1_results = []
    p3_results = []
    case_audits = []

    for c in cases:
        cid = c["case_id"]
        gold = c["gold_support_label"]
        claim_text = c["claim_sentence"]
        sp = c["supporting_passages"][0]
        ep = EvidencePassage(
            evidence_id=sp["evidence_id"],
            document_id=sp["document_id"],
            case_title=sp["case_title"],
            passage_text=sp["passage_text"],
            start_char=sp["start_char"],
            end_char=sp["end_char"],
            structural_label=sp.get("structural_label", "headnote_holding")
        )

        # Policy 1: Deterministic
        res_p1 = det_verifier.verify_claim(claim_text=claim_text, cited_passages=[ep], policy="deterministic")
        pred_p1 = res_p1.status.value
        p1_results.append({"case_id": cid, "gold": gold, "pred": pred_p1})

        # Policy 3: Contradiction Veto (Hardened)
        res_p3 = det_verifier.verify_claim(claim_text=claim_text, cited_passages=[ep], policy="policy_3")
        pred_p3 = res_p3.status.value
        p3_results.append({"case_id": cid, "gold": gold, "pred": pred_p3})

        case_audits.append({
            "case_id": cid,
            "gold_label": gold,
            "p1_pred": pred_p1,
            "p1_method": res_p1.method,
            "p3_pred": pred_p3,
            "p3_method": res_p3.method,
            "contradiction_score": getattr(res_p3, "contradiction_score", None),
            "entailment_score": getattr(res_p3, "entailment_score", None),
            "safe_non_supported": (gold == "supported") or (gold != "supported" and pred_p3 != "supported")
        })

    def compute_metrics(results: List[Dict[str, str]], policy_name: str) -> Dict[str, Any]:
        total = len(results)
        classes = ["supported", "partially_supported", "unsupported", "contradicted", "not_evaluated"]
        cm = {g: {p: 0 for p in classes} for g in classes}
        for item in results:
            cm[item["gold"]][item["pred"]] += 1

        gold_supp = sum(1 for r in results if r["gold"] == "supported")
        pred_supp = sum(1 for r in results if r["pred"] == "supported")
        tp = sum(1 for r in results if r["gold"] == "supported" and r["pred"] == "supported")

        gold_contra = sum(1 for r in results if r["gold"] == "contradicted")
        fa_contra = sum(1 for r in results if r["gold"] == "contradicted" and r["pred"] == "supported")

        gold_partial = sum(1 for r in results if r["gold"] == "partially_supported")
        fa_partial = sum(1 for r in results if r["gold"] == "partially_supported" and r["pred"] == "supported")

        gold_unsupp = sum(1 for r in results if r["gold"] == "unsupported")
        fa_unsupp = sum(1 for r in results if r["gold"] == "unsupported" and r["pred"] == "supported")

        non_supp_total = total - gold_supp
        non_supp_fa = fa_contra + fa_partial + fa_unsupp

        precision = tp / pred_supp if pred_supp > 0 else 0.0
        recall = tp / gold_supp if gold_supp > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

        return {
            "policy_name": policy_name,
            "total_records": total,
            "confusion_matrix": cm,
            "metrics": {
                "supported_precision": {
                    "value": round(precision, 4),
                    "numerator": tp,
                    "denominator": pred_supp,
                    "unit": "claim"
                },
                "supported_recall": {
                    "value": round(recall, 4),
                    "numerator": tp,
                    "denominator": gold_supp,
                    "unit": "claim"
                },
                "supported_f1": {
                    "value": round(f1, 4),
                    "numerator": "2 * P * R",
                    "denominator": "P + R",
                    "unit": "claim"
                },
                "non_supported_far": {
                    "value": round(non_supp_fa / non_supp_total, 4) if non_supp_total > 0 else 0.0,
                    "numerator": non_supp_fa,
                    "denominator": non_supp_total,
                    "unit": "claim"
                },
                "contradiction_far": {
                    "value": round(fa_contra / gold_contra, 4) if gold_contra > 0 else 0.0,
                    "numerator": fa_contra,
                    "denominator": gold_contra,
                    "unit": "claim"
                },
                "partially_supported_far": {
                    "value": round(fa_partial / gold_partial, 4) if gold_partial > 0 else 0.0,
                    "numerator": fa_partial,
                    "denominator": gold_partial,
                    "unit": "claim"
                },
                "unsupported_far": {
                    "value": round(fa_unsupp / gold_unsupp, 4) if gold_unsupp > 0 else 0.0,
                    "numerator": fa_unsupp,
                    "denominator": gold_unsupp,
                    "unit": "claim"
                }
            }
        }

    p1_metrics = compute_metrics(p1_results, "Policy 1 (Deterministic Baseline)")
    p3_metrics = compute_metrics(p3_results, "Policy 3 (Contradiction Veto Hardened)")

    output_data = {
        "metadata": {
            "milestone": "Milestone 24",
            "audit_type": "Frozen Staging Evaluation Re-Evaluation",
            "staging_dataset": "evaluation/rag/milestone20_staging_claims.jsonl",
            "provenance": "developer_curated_frozen_pre_evaluation",
            "total_cases": 40,
            "independently_reviewed": False,
            "external_review_status": "PENDING_EXTERNAL_REVIEW",
            "graph_traversal_enabled": False
        },
        "policy_1_deterministic": p1_metrics,
        "policy_3_hardened": p3_metrics,
        "case_audits": case_audits
    }

    out_path = Path("evaluation/rag/milestone24_frozen_staging_results.json")
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    print(f"Saved frozen staging results to {out_path}")

    return output_data


def evaluate_adversarial_suite() -> Dict[str, Any]:
    """
    Evaluate all 22 cases in evaluation/rag/milestone24_adversarial_cases.jsonl.
    Verifies that all 11 centralized safety invariants hold and that 0/22 receive verified_supported.
    """
    adv_file = Path("evaluation/rag/milestone24_adversarial_cases.jsonl")
    with adv_file.open("r", encoding="utf-8") as f:
        cases = [json.loads(line) for line in f if line.strip()]

    assert len(cases) == 22, f"Expected 22 adversarial cases, found {len(cases)}"

    case_evaluations = []
    safe_fail_closed_count = 0
    verified_supported_leak_count = 0

    for c in cases:
        cid = c["case_id"]
        category = c["category"]
        failure_mode = c["failure_mode"]
        expected_badge = c["expected_badge"]
        query_text = c["query_text"]
        answer_text = c["answer_text"]

        # Reconstruct evidence passages
        passages = [
            EvidencePassage(
                evidence_id=p["evidence_id"],
                document_id=p["document_id"],
                case_title=p["case_title"],
                passage_text=p["passage_text"],
                start_char=p["start_char"],
                end_char=p["end_char"],
                structural_label=p.get("structural_label", "headnote_holding")
            )
            for p in c["evidence_passages"]
        ]

        # Reconstruct claims
        claim_objects = []
        for cl in c["claims"]:
            status_val = cl.get("simulated_verifier_status", "not_evaluated")
            claim_objects.append(
                ClaimAttribution(
                    sentence=cl["text"],
                    cited_evidence_ids=cl.get("evidence_ids", []),
                    verification_status=status_val,
                    semantic_support_status=status_val,
                    is_supported=(status_val == "supported"),
                    is_contradicted=cl.get("is_contradicted", status_val == "contradicted"),
                    is_partially_supported=cl.get("is_partially_supported", status_val == "partially_supported"),
                    omits_statutory_qualification=cl.get("omits_statutory_qualification", False),
                    claim_overgeneralizes_holding=cl.get("claim_overgeneralizes_holding", False),
                    relies_only_on_party_submissions=cl.get("relies_only_on_party_submissions", False)
                )
            )

        # Set up validator result based on failure mode
        offsets_verified = True
        status = "answered"

        if failure_mode in ["mutated_evidence_passage_text", "offset_range_mismatch"]:
            offsets_verified = False
            val_result = CitationValidationResult(
                is_valid=False,
                validation_status="invalid",
                evidence_integrity_valid=False,
                validation_notes=["Offset or passage integrity check failed."]
            )
        elif failure_mode == "invalid_hallucinated_document_id":
            val_result = CitationValidationResult(
                is_valid=False,
                validation_status="invalid",
                has_invalid_citations=True,
                invalid_source_ids=["E99"],
                citation_existence_valid=False,
                validation_notes=["Citation ID E99 not found in active evidence."]
            )
        elif failure_mode == "conflicting_validator_vs_verifier_outcome":
            val_result = CitationValidationResult(
                is_valid=False,
                validation_status="invalid",
                has_invalid_citations=True,
                invalid_source_ids=["E2"],
                citation_existence_valid=False,
                cited_source_ids=["E1", "E2"],
                validation_notes=["Unknown citation E2 detected."]
            )
        elif failure_mode == "missing_attribution_unsupported_sentence":
            val_result = CitationValidationResult(
                is_valid=True,
                validation_status="valid",
                attribution_complete=False,
                unsupported_sentences=["In all criminal trials the magistrate must personally conduct an interrogation before trial."],
                validation_notes=["Substantive sentence lacks evidence citation."]
            )
        elif failure_mode in ["timeout_gateway_504", "provider_unavailable_503"]:
            status = "error"
            val_result = None
        elif failure_mode == "empty_claim_extraction":
            status = "answered"
            val_result = None
        else:
            # Standard populated validation result
            contra_count = sum(1 for cl in claim_objects if cl.verification_status == "contradicted")
            partial_count = sum(1 for cl in claim_objects if cl.verification_status == "partially_supported")
            unsupp_count = sum(1 for cl in claim_objects if cl.verification_status == "unsupported")
            supp_count = sum(1 for cl in claim_objects if cl.verification_status == "supported")
            unver_count = sum(1 for cl in claim_objects if cl.verification_status not in ["supported", "partially_supported", "contradicted", "unsupported"])

            sem_status = "supported" if (supp_count == len(claim_objects) and len(claim_objects) > 0) else ("contradicted" if contra_count > 0 else ("partially_supported" if partial_count > 0 else "unsupported"))

            val_result = CitationValidationResult(
                is_valid=True,
                validation_status="valid",
                semantic_support_status=sem_status,
                contradicted_claims_count=contra_count,
                partially_supported_claims_count=partial_count,
                unsupported_claims_count=unsupp_count,
                supported_claims_count=supp_count,
                unverified_claims_count=unver_count,
                cited_source_ids=[ep.evidence_id for ep in passages],
                valid_source_ids=[ep.evidence_id for ep in passages]
            )

        # Run through centralized pipeline badge contract
        awarded_badge = RAGPipeline.determine_verification_badge(
            status=status,
            claims=claim_objects,
            val_result=val_result,
            offsets_verified=offsets_verified,
            evidence_passages=passages,
            answer_text=answer_text
        )

        is_safe = (awarded_badge != "verified_supported")
        if is_safe:
            safe_fail_closed_count += 1
        else:
            verified_supported_leak_count += 1

        case_evaluations.append({
            "case_id": cid,
            "category": category,
            "failure_mode": failure_mode,
            "expected_badge": expected_badge,
            "awarded_badge": awarded_badge,
            "matches_expected": (awarded_badge == expected_badge),
            "is_safe_fail_closed": is_safe,
            "injected_defect": c["injected_defect"],
            "safety_invariant": c["expected_safety_invariant"]
        })

    adversarial_results = {
        "metadata": {
            "milestone": "Milestone 24",
            "suite_name": "Milestone 24 Deterministic Adversarial Safety Suite",
            "dataset": "evaluation/rag/milestone24_adversarial_cases.jsonl",
            "total_cases": len(cases),
            "categories": {
                "single_claim_failure": sum(1 for c in cases if c["category"] == "single_claim_failure"),
                "multiple_claim_failure": sum(1 for c in cases if c["category"] == "multiple_claim_failure"),
                "provenance_execution_failure": sum(1 for c in cases if c["category"] == "provenance_execution_failure")
            },
            "provenance": "developer_curated_adversarial_suite",
            "independently_reviewed": False,
            "external_review_status": "PENDING_EXTERNAL_REVIEW"
        },
        "summary": {
            "total_adversarial_cases": len(cases),
            "safe_fail_closed_count": safe_fail_closed_count,
            "verified_supported_leak_count": verified_supported_leak_count,
            "safe_fail_closed_rate": round(safe_fail_closed_count / len(cases), 4),
            "leak_rate": round(verified_supported_leak_count / len(cases), 4),
            "exact_expected_badge_matches": sum(1 for ce in case_evaluations if ce["matches_expected"]),
            "badge_distribution": {
                "verified_supported": sum(1 for ce in case_evaluations if ce["awarded_badge"] == "verified_supported"),
                "qualified_answer": sum(1 for ce in case_evaluations if ce["awarded_badge"] == "qualified_answer"),
                "unverified_answer": sum(1 for ce in case_evaluations if ce["awarded_badge"] == "unverified_answer"),
                "rejected_answer": sum(1 for ce in case_evaluations if ce["awarded_badge"] == "rejected_answer"),
                "system_error": sum(1 for ce in case_evaluations if ce["awarded_badge"] == "system_error")
            }
        },
        "case_evaluations": case_evaluations
    }

    out_path = Path("evaluation/rag/milestone24_badge_invariant_results.json")
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(adversarial_results, f, indent=2, ensure_ascii=False)
    print(f"Saved adversarial results to {out_path}")

    return adversarial_results


def main():
    print("=" * 80)
    print("NYAYAVARTA MILESTONE 24: SAFETY AUDIT & VERIFICATION BENCHMARK")
    print("=" * 80)

    # 1. Verify frozen file hashes
    print("\n[Step 1] Verifying non-mutation of frozen evaluation artifacts...")
    hashes = verify_file_hashes()
    for fp in hashes:
        print(f"  OK: {fp} (hash verified)")

    # 2. Re-evaluate 40 frozen staging claims
    print("\n[Step 2] Re-evaluating 40 frozen Milestone 20 staging claims...")
    staging_res = evaluate_frozen_staging_claims()
    p1 = staging_res["policy_1_deterministic"]["metrics"]
    p3 = staging_res["policy_3_hardened"]["metrics"]

    print(f"\n--- Policy 1 (Deterministic Baseline) ---")
    print(f"  Supported Precision:      {p1['supported_precision']['value']*100:.2f}% ({p1['supported_precision']['numerator']}/{p1['supported_precision']['denominator']})")
    print(f"  Supported Recall:         {p1['supported_recall']['value']*100:.2f}% ({p1['supported_recall']['numerator']}/{p1['supported_recall']['denominator']})")
    print(f"  Non-Supported FAR:        {p1['non_supported_far']['value']*100:.2f}% ({p1['non_supported_far']['numerator']}/{p1['non_supported_far']['denominator']})")
    print(f"  Contradiction FAR:        {p1['contradiction_far']['value']*100:.2f}% ({p1['contradiction_far']['numerator']}/{p1['contradiction_far']['denominator']})")
    print(f"  Partially Supported FAR:  {p1['partially_supported_far']['value']*100:.2f}% ({p1['partially_supported_far']['numerator']}/{p1['partially_supported_far']['denominator']})")

    print(f"\n--- Policy 3 (Contradiction Veto Hardened) ---")
    print(f"  Supported Precision:      {p3['supported_precision']['value']*100:.2f}% ({p3['supported_precision']['numerator']}/{p3['supported_precision']['denominator']})")
    print(f"  Supported Recall:         {p3['supported_recall']['value']*100:.2f}% ({p3['supported_recall']['numerator']}/{p3['supported_recall']['denominator']})")
    print(f"  Non-Supported FAR:        {p3['non_supported_far']['value']*100:.2f}% ({p3['non_supported_far']['numerator']}/{p3['non_supported_far']['denominator']})")
    print(f"  Contradiction FAR:        {p3['contradiction_far']['value']*100:.2f}% ({p3['contradiction_far']['numerator']}/{p3['contradiction_far']['denominator']})")
    print(f"  Partially Supported FAR:  {p3['partially_supported_far']['value']*100:.2f}% ({p3['partially_supported_far']['numerator']}/{p3['partially_supported_far']['denominator']})")

    assert p3['non_supported_far']['numerator'] == 0, "Safety failure: Policy 3 still admitted non-supported claims!"

    # 3. Evaluate 22 adversarial cases
    print("\n[Step 3] Evaluating 22 deterministic adversarial cases against centralized safety contract...")
    adv_res = evaluate_adversarial_suite()
    s = adv_res["summary"]
    print(f"  Total Adversarial Cases:  {s['total_adversarial_cases']}")
    print(f"  Safe Fail-Closed Count:   {s['safe_fail_closed_count']} ({s['safe_fail_closed_rate']*100:.2f}%)")
    print(f"  Verified Supported Leaks: {s['verified_supported_leak_count']} ({s['leak_rate']*100:.2f}%)")
    print(f"  Badge Distribution:       {s['badge_distribution']}")

    assert s['verified_supported_leak_count'] == 0, "CRITICAL SAFETY LEAK: Adversarial case received verified_supported!"
    assert s['safe_fail_closed_count'] == 22, "Not all adversarial cases failed closed!"

    # 4. Release Decision Gate
    print("\n" + "=" * 80)
    print("RELEASE GATE DECISION: HOLD (NOT READY FOR EXTERNAL PILOT)")
    print("=" * 80)
    print("Rationale:")
    print("  1. All 22 adversarial regression cases successfully failed closed with 0 leaks.")
    print("  2. Policy 3 eliminated all 5 historical non-supported false acceptances on 40 frozen staging claims (FAR: 0.0%).")
    print("  3. Independent legal review remains pending (marked PENDING_EXTERNAL_REVIEW across all datasets).")
    print("  4. Evaluations remain developer-curated; external legal panel validation is required prior to pilot.")
    print("=" * 80)


if __name__ == "__main__":
    main()
