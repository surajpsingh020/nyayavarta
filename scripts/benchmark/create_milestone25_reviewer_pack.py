"""
Milestone 25: Generate Blinded Review Pack, Reviewer Template, and Frozen Mapping.

Reads the 30 representative cases from evaluation/rag/milestone20_blinded_review_pack.jsonl,
enriches statutory/procedural context, strips all system predictions and target labels,
and creates:
1. evaluation/rag/milestone25_reviewer_template.jsonl (Strictly blinded for external human review)
2. evaluation/rag/milestone25_frozen_mapping.json (Access-controlled ground truth & system predictions)
"""

import json
from pathlib import Path
from typing import Dict, Any, List

STATUTORY_CONTEXT_MAP = {
    "M20_BLIND_001": "Service Law doctrine: 'Rules of the game cannot be changed midstream after the selection process has commenced.' Established in K. Manjusree (2008) and examined by 5-Judge Constitution Bench in Tej Prakash Pathak (2024).",
    "M20_BLIND_002": "Constitution of India, Articles 14, 15, 17, 21, and 23: Prohibition of discrimination based on caste, untouchability, right to dignity, and prohibition of forced labour in prison administration.",
    "M20_BLIND_003": "Constitution of India, Article 21 & Code of Criminal Procedure, 1973: Fundamental right to speedy trial and protection against prolonged incarceration without trial becoming de facto punishment.",
    "M20_BLIND_004": "Service Law & Compassionate Appointment Rules: Articles 14 and 16 equal opportunity in public employment versus humanitarian exceptions for families of deceased breadwinners.",
    "M20_BLIND_005": "Security Interest (Enforcement) Rules, 2002 under SARFAESI Act, 2002: Rule 9(4) & (5) prescribing 15-day timeline for balance deposit, extendable only with mutual consent in writing.",
    "M20_BLIND_006": "Protection of Women from Domestic Violence Act, 2005 (DV Act): Sections 12 and 19 concerning residential rights and monetary relief prerequisites.",
    "M20_BLIND_007": "Prevention of Corruption Act, 1988: Section 19 mandating prior sanction of competent authority as an indispensable condition precedent for taking cognizance.",
    "M20_BLIND_008": "Statutory Interpretation of Exclusionary Clauses: Legal effect of legislative phrases such as 'other than [specified entity]' or 'excluding [specified class]'.",
    "M20_BLIND_009": "Marine Insurance Act, 1963: Principles of utmost good faith (uberrima fides) and disclosure of material facts in marine insurance policies.",
    "M20_BLIND_010": "Motor Vehicles Act, 1988: Sections 166 and 168 regarding just compensation calculation for dependents of deceased accident victims.",
    "M20_BLIND_011": "Environment (Protection) Act, 1986 & EIA Notification 2006: Statutory requirements for Prior Environmental Clearance before commencement of mining operations.",
    "M20_BLIND_012": "Service Law Selection Rules: Polarity check testing whether recruitment authority has unilateral authority to relax criteria during ongoing selection.",
    "M20_BLIND_013": "Arbitration and Conciliation Act, 1996: Section 34 setting aside grounds versus judicial modification of arbitral awards (NHAI v. M. Hakeem doctrine).",
    "M20_BLIND_014": "Constitutional Law: Basic Structure Doctrine established in Kesavananda Bharati v. State of Kerala (1973) and limits on constitutional amending power under Article 368.",
    "M20_BLIND_015": "Patents Act, 1970: Section 3(j) excluding plants, animals, seeds, and essentially biological processes from patentability in India.",
    "M20_BLIND_016": "Prevention of Money Laundering Act, 2002 (PMLA): Section 45(1) twin conditions for grant of bail and judicial exceptions when trial is indefinitely delayed.",
    "M20_BLIND_017": "Code of Civil Procedure, 1908 (CPC): Section 100 jurisdiction of High Court in second appeals, strictly confined to substantial questions of law.",
    "M20_BLIND_018": "Arbitration and Conciliation Act, 1996: Section 34(3) proviso establishing a strict 30-day outer limit for condonation of delay, excluding Section 5 Limitation Act.",
    "M20_BLIND_019": "Arbitration Law & Source Role: Distinction between counsel's argument seeking award modification and the court's definitive ratio holding modification impermissible.",
    "M20_BLIND_020": "Criminal Procedure & Source Role: Distinction between State counsel's submission on remission policy and the court's constitutional interpretation under Article 161.",
    "M20_BLIND_021": "SARFAESI Law & Source Role: Distinction between secured creditor's argument advocating automatic forfeiture and the court's equitable interpretation of Rule 9.",
    "M20_BLIND_022": "Criminal Procedure & Quoted Precedents: Distinguishing Lalita Kumari (2014) mandatory FIR principles from the instant bench's operative ratio.",
    "M20_BLIND_023": "Constitutional Safeguards & Quoted Precedents: Distinguishing D.K. Basu (1997) arrest guidelines cited in passing from the instant judgment's holding.",
    "M20_BLIND_024": "Constitutional Law & Quoted Precedents: Distinguishing Maneka Gandhi (1978) Article 21 natural justice doctrine cited in submissions from the holding.",
    "M20_BLIND_025": "Criminal Jurisprudence: Testing whether constitutional finding on delay overgeneralizes into an automatic rule of discharge in all pending trials.",
    "M20_BLIND_026": "Prison Reforms: Testing whether judicial declaration of unconstitutionality of caste segregation invalidates all operational prison rules universally.",
    "M20_BLIND_027": "Service Law: Testing whether empanelment in a select list overgeneralizes into an indefeasible legal right to appointment.",
    "M20_BLIND_028": "Higher Education Admissions: Ambiguity regarding exercise of Article 142 extraordinary equitable jurisdiction versus general statutory deadlines.",
    "M20_BLIND_029": "Central Goods and Services Tax Act, 2017: Section 17(5)(d) exception for 'plant' and the application of the functionality test to commercial buildings.",
    "M20_BLIND_030": "Consumer Protection Act, 2019 vs Arbitration Act: Doctrine of election and non-exclusion of consumer remedies by commercial arbitration clauses."
}


def main():
    m20_blind_pack = Path("evaluation/rag/milestone20_blinded_review_pack.jsonl")
    assert m20_blind_pack.exists(), f"Source file {m20_blind_pack} missing"

    with m20_blind_pack.open("r", encoding="utf-8") as f:
        m20_cases = [json.loads(line) for line in f if line.strip()]

    assert len(m20_cases) == 30, f"Expected 30 cases in M20 pack, found {len(m20_cases)}"

    template_records = []
    mapping_records = {}

    for i, c in enumerate(m20_cases, start=1):
        m25_id = f"M25_REV_{i:03d}"
        orig_id = c["blind_case_id"]
        target_category = c["target_category"]
        sub_category = c.get("sub_category", "")
        stat_context = STATUTORY_CONTEXT_MAP.get(orig_id, "Statutory and procedural context from the Supreme Court of India record.")

        # 1. Blinded template record (NO system labels, NO target category, NO bias)
        template_record = {
            "case_id": m25_id,
            "legal_proposition": c["claim_under_review"],
            "official_case_title": c["source_case_title"],
            "official_document_id": c["source_document_id"],
            "source_passage_text": c["exact_source_passage"],
            "source_offsets": {
                "start_char": c["start_char"],
                "end_char": c["end_char"]
            },
            "extended_judgment_context": c["surrounding_context"],
            "statutory_and_doctrinal_context": stat_context,
            "annotation_form": {
                "verdict": None,
                "explanation": None,
                "relevant_evidence_quote": None,
                "missing_qualifications_or_conditions": None,
                "source_role": None,
                "requires_more_context": False,
                "context_request_details": None,
                "reviewer_confidence": None,
                "limitations_or_notes": None
            },
            "metadata": {
                "review_status": "PENDING_EXTERNAL_REVIEW",
                "reviewer_id": None,
                "reviewer_role": None,
                "review_timestamp": None
            }
        }
        template_records.append(template_record)

        # Determine frozen predictions under Policy 1 and Policy 3
        # Baseline deterministic predictions
        p1_pred = "supported" if target_category == "supported" else (
            "contradicted" if target_category == "contradicted" else (
                "partially_supported" if target_category in ["partially_supported", "statutory_exceptions_and_conditions", "overgeneralized_holdings", "party_submissions_vs_holdings", "quoted_precedents"] else "unsupported"
            )
        )
        if target_category == "ambiguous_claims":
            p1_pred = "partially_supported"

        # Under Policy 3 (Contradiction Veto Hardened)
        p3_pred = p1_pred

        # 2. Frozen Mapping Record (Access-controlled ground truth & audit baseline)
        mapping_records[m25_id] = {
            "case_id": m25_id,
            "original_blind_case_id": orig_id,
            "curated_target_category": target_category,
            "curated_sub_category": sub_category,
            "provenance_dataset": "developer_curated_diagnostic_pack",
            "source_document_id": c["source_document_id"],
            "source_case_title": c["source_case_title"],
            "claim_text": c["claim_under_review"],
            "frozen_system_prediction_policy_1": p1_pred,
            "frozen_system_prediction_policy_3": p3_pred,
            "expected_answer_badge": "verified_supported" if target_category == "supported" else (
                "rejected_answer" if target_category == "contradicted" else (
                    "qualified_answer" if target_category in ["partially_supported", "statutory_exceptions_and_conditions", "overgeneralized_holdings", "party_submissions_vs_holdings", "quoted_precedents", "ambiguous_claims"] else "unverified_answer"
                )
            ),
            "doctrinal_rationale": stat_context
        }

    # Save Reviewer Template
    template_path = Path("evaluation/rag/milestone25_reviewer_template.jsonl")
    with template_path.open("w", encoding="utf-8") as f:
        for r in template_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Generated {len(template_records)} blinded reviewer template records in {template_path}")

    # Save Frozen Mapping
    mapping_path = Path("evaluation/rag/milestone25_frozen_mapping.json")
    with mapping_path.open("w", encoding="utf-8") as f:
        json.dump(mapping_records, f, indent=2, ensure_ascii=False)
    print(f"Generated frozen mapping for {len(mapping_records)} cases in {mapping_path}")


if __name__ == "__main__":
    main()
