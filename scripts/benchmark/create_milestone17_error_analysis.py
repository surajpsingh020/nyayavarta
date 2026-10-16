"""Generate Milestone 17 Error Analysis and Frozen Baseline Artifact.

Frozen baseline containing:
- Original claim text and source passages from Milestone 16 unseen evaluation.
- Gold labels and provenance.
- System predictions under frozen Milestone 16 ClaimVerifier.
- Detailed root-cause diagnosis of the 3 false acceptances (M16_UNSEEN_007, 008, 020).
- Documentation of the 5 correctly identified supported claims (M16_UNSEEN_001-005).
- Documentation of the 7 preserved-uncertainty cases (not_evaluated).
- Exact verifier version, causative rules, and remediation strategy.
"""

import json
from pathlib import Path

DIAGNOSIS_DATA = {
    "M16_UNSEEN_007": {
        "failure_mode": "omitted_essential_statutory_element_masked_by_lexical_overlap",
        "material_unsupported_or_contradicted_component": (
            "Claim asserts conviction under Section 306 IPC is permissible 'without proof of active instigation if harassment is established'. "
            "In direct contrast, Section 107/306 requires positive active instigation proximate in time; mere harassment is insufficient."
        ),
        "causative_rule": (
            "direct_holding_entailment: len(overlap) >= 3 fired on headnote_holding. "
            "Tokens '306', 'ipc', 'abetment', 'suicide', 'instigation' overlapped, while RE_NEGATIVE_CONDITION_WAIVER did not catch "
            "'without proof of' and RE_AFFIRMATIVE_MODALS did not catch 'may be convicted'."
        ),
        "doctrinal_reality": (
            "The Supreme Court held that Section 306 requires positive acts proximate to the suicide and active instigation under Section 107. "
            "The claim directly reverses this prerequisite."
        ),
        "evidence_sufficiency": "Cited headnote holding contains sufficient text to detect that instigation is mandatory, but lexical verifier had no semantic entailment check.",
        "remediation_strategy": (
            "Do not allow len(overlap) >= 3 to declare SUPPORTED when the claim contains conditional or negative waiver terms ('without', 'may be', 'if') "
            "that lack affirmative substantiation. Fall back to NOT_EVALUATED or flag as PARTIALLY_SUPPORTED."
        ),
    },
    "M16_UNSEEN_008": {
        "failure_mode": "omitted_statutory_threshold_masked_by_lexical_overlap",
        "material_unsupported_or_contradicted_component": (
            "Claim asserts court considering UAPA bail may assess accusations 'without detailed analysis'. "
            "While chargesheet need not contain detailed evidence, Section 43D(5) strictly mandates satisfaction of the twin conditions "
            "(reasonable grounds for believing accusation is prima facie true) before bail can be granted."
        ),
        "causative_rule": (
            "direct_holding_entailment: len(overlap) >= 3 fired on headnote_holding because 'court', 'considering', 'bail', 'uapa', "
            "'assess', 'accusations', 'prima', 'facie', 'true', 'detailed', 'analysis' matched passage tokens."
        ),
        "doctrinal_reality": (
            "The Court held that the chargesheet need not contain detailed evidence analysis, but the bail court must strictly apply "
            "Section 43D(5) prima facie threshold."
        ),
        "evidence_sufficiency": "Passage text explicitly references Section 43D(5), but rule-based verifier treated keyword overlap as ratio proof.",
        "remediation_strategy": (
            "Enforce strict token coverage threshold (>= 75% non-generic tokens) and require absence of unverified qualification phrases. "
            "When high confidence is absent, preserve uncertainty with NOT_EVALUATED."
        ),
    },
    "M16_UNSEEN_020": {
        "failure_mode": "holding_inversion_with_negative_polarity_in_claim",
        "material_unsupported_or_contradicted_component": (
            "Claim asserts female heirs 'cannot claim equal partition rights in ancestral property if a preliminary partition occurred before 2005'. "
            "The Supreme Court held the exact opposite: rejecting male coparceners' exclusion claim and confirming female rights."
        ),
        "causative_rule": (
            "direct_holding_entailment: Polarity negation regex was searching for negation in the passage (RE_JUDICIAL_NEGATION), "
            "not in the claim. The claim contained 'cannot claim', which bypassed RE_AFFIRMATIVE_MODALS, allowing len(overlap) >= 3 to fire."
        ),
        "doctrinal_reality": (
            "The Court held that female coparcenary rights cannot be excluded by preliminary partition unless completely finalized before the statutory cutoff."
        ),
        "evidence_sufficiency": "Cited passage records that the claim to exclude sisters was rejected, refuting the claim.",
        "remediation_strategy": (
            "Check negative polarity assertions in claims ('cannot claim', 'barred from', 'cannot be granted'). "
            "If claim asserts a legal prohibition that does not match passage ratio, do not promote to SUPPORTED; classify as CONTRADICTED or NOT_EVALUATED."
        ),
    },
}


def build_error_analysis():
    m16_path = Path("evaluation/rag/milestone16_unseen_claims.jsonl")
    lines = [json.loads(line) for line in m16_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    records = []
    for item in lines:
        cid = item["case_id"]
        gold = item["gold_support_label"]
        pred = item["predicted_status"]

        is_false_accept = (pred == "supported" and gold != "supported")
        is_correct_supp = (pred == "supported" and gold == "supported")
        is_preserved_unc = (pred == "not_evaluated")

        rec = {
            "case_id": cid,
            "query_id": item.get("query_id"),
            "category": item.get("category"),
            "question": item.get("question"),
            "claim_sentence": item.get("claim_sentence"),
            "gold_support_label": gold,
            "m16_predicted_status": pred,
            "verification_method": item.get("verification_method"),
            "verification_reason": item.get("verification_reason"),
            "is_false_acceptance": is_false_accept,
            "is_correctly_identified_supported": is_correct_supp,
            "is_preserved_uncertainty": is_preserved_unc,
            "supporting_passages": item.get("supporting_passages", []),
            "baseline_provenance": {
                "evaluation_milestone": "milestone_16",
                "evaluation_script": "scripts/benchmark/run_milestone16_evaluation.py",
                "verifier_module": "services/rag/claim_verifier.py (M15-M16 version)",
                "corpus": "782 Supreme Court Judgments (2024 SCR)",
                "corpus_volume": item["supporting_passages"][0]["document_id"].split("_")[1] if item.get("supporting_passages") else None,
            },
        }

        if cid in DIAGNOSIS_DATA:
            rec["error_diagnosis"] = DIAGNOSIS_DATA[cid]
        elif is_correct_supp:
            rec["correct_support_analysis"] = {
                "ratio_alignment": "Core legal principle in claim directly reproduces ratio in headnote holding.",
                "caveats": "No omitted conditions or contradictory polarity present.",
            }
        elif is_preserved_unc:
            rec["preserved_uncertainty_analysis"] = {
                "rationale": "Claim lacked matching deterministic patterns; verifier safely demoted to not_evaluated, preserving answer safety.",
            }

        records.append(rec)

    out_path = Path("evaluation/rag/milestone17_error_analysis.jsonl")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    print(f"Milestone 17 Error Analysis generated: {out_path} ({len(records)} records)")


if __name__ == "__main__":
    build_error_analysis()
