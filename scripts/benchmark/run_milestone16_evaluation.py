"""Run Milestone 16 evaluation on 20 brand-new unseen claims from unstudied 2024 judgments.

Preserves the existing ClaimVerifier code without modification.
Evaluates accuracy, class-level precision/recall/F1, and disaggregated False Acceptance Rates (FAR).
Outputs:
- evaluation/rag/milestone16_unseen_claims.jsonl
- evaluation/rag/milestone16_evaluation_results.json
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.rag.models import EvidencePassage
from services.rag.claim_verifier import ClaimVerifier, ClaimVerificationStatus
from scripts.benchmark.evaluate_milestone16_review import compute_metrics


UNSEEN_CASES = [
    {
        "case_id": "M16_UNSEEN_001",
        "query_id": "M16_Q001",
        "category": "motor_vehicles_multiplier",
        "question": "How is the multiplier calculated in motor accident compensation claims?",
        "claim_sentence": "In motor accident compensation claims, the age of the deceased and not the age of the dependents must be taken into consideration for determining the multiplier.",
        "gold_support_label": "supported",
        "document_id": "2024_3_1009_1013",
        "case_title": "HARESH SHANTILAL AVLANI & ANR versus THE NEW INDIA ASSURANCE CO. LTD.",
        "start_char": 544,
        "end_char": 844,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_002",
        "query_id": "M16_Q002",
        "category": "land_acquisition_hearing",
        "question": "Is personal hearing with advance notice mandatory for objections under Section 5A of the Land Acquisition Act?",
        "claim_sentence": "A landholder submitting objections under Section 5A of the Land Acquisition Act must be given personal hearing preceded by advance notice.",
        "gold_support_label": "supported",
        "document_id": "2024_7_1001_1030",
        "case_title": "NEW OKHLA INDUSTRIAL DEVELOPMENT AUTHORITY versus DARSHAN LAL BOHRA & ORS.",
        "start_char": 1334,
        "end_char": 1634,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_003",
        "query_id": "M16_Q003",
        "category": "judicial_pension_parity",
        "question": "Can distinction be made between High Court judges based on source of recruitment for pensionary benefits?",
        "claim_sentence": "Judges of the High Court are constitutional functionaries and no distinction can be made between them regarding pensionary benefits based on their source of recruitment.",
        "gold_support_label": "supported",
        "document_id": "2024_11_1042_1063",
        "case_title": "JUSTICE SHAILENDRA SINGH & ORS. versus UNION OF INDIA & ORS.",
        "start_char": 1023,
        "end_char": 1323,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_004",
        "query_id": "M16_Q004",
        "category": "pmla_ecir_jurisdiction",
        "question": "Is an ECIR recorded at the ED Headquarters Investigation Unit restricted to a specific territory?",
        "claim_sentence": "An ECIR recorded at the Headquarters Investigation Unit of the Directorate of Enforcement is not restricted to any single territorial jurisdiction.",
        "gold_support_label": "supported",
        "document_id": "2024_9_110_134",
        "case_title": "ABHISHEK BANERJEE & ANR. versus DIRECTORATE OF ENFORCEMENT",
        "start_char": 1626,
        "end_char": 1926,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_005",
        "query_id": "M16_Q005",
        "category": "caste_scrutiny_jurisdiction",
        "question": "Which authority has jurisdiction to verify caste certificates under the Maharashtra Act XXIII of 2000?",
        "claim_sentence": "The power of verification of caste certificates is vested exclusively with the Scrutiny Committee under the Maharashtra Act XXIII of 2000.",
        "gold_support_label": "supported",
        "document_id": "2024_4_121_150",
        "case_title": "NAVNEET KAUR HARBHAJANSING KUNDLES @ NAVNEET KAUR RAVI RANA versus STATE OF MAHARASHTRA AND OTHERS",
        "start_char": 1479,
        "end_char": 1779,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_006",
        "query_id": "M16_Q006",
        "category": "section_319_crpc_threshold",
        "question": "What is the degree of satisfaction required to summon an additional accused under Section 319 CrPC?",
        "claim_sentence": "The trial court has discretion under Section 319 CrPC to summon additional accused whenever prima facie evidence exists.",
        "gold_support_label": "partially_supported",
        "document_id": "2024_6_10_19",
        "case_title": "SHANKAR versus THE STATE OF UTTAR PRADESH & ORS.",
        "start_char": 596,
        "end_char": 896,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_007",
        "query_id": "M16_Q007",
        "category": "section_306_ipc_abetment",
        "question": "What are the essential elements required to establish abetment of suicide under Section 306 IPC?",
        "claim_sentence": "A person may be convicted under Section 306 IPC for abetment of suicide without proof of active instigation if harassment is established.",
        "gold_support_label": "partially_supported",
        "document_id": "2024_7_1031_1039",
        "case_title": "ROHINI SUDARSHAN GANGURDE versus THE STATE OF MAHARASHTRA & ANR.",
        "start_char": 1587,
        "end_char": 1887,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_008",
        "query_id": "M16_Q008",
        "category": "uapa_bail_chargesheet",
        "question": "How should a court assess accusations when considering bail under Section 43D(5) of UAPA?",
        "claim_sentence": "The court considering bail under UAPA may assess whether the accusations are prima facie true without detailed analysis.",
        "gold_support_label": "partially_supported",
        "document_id": "2024_5_1011_1037",
        "case_title": "UNION OF INDIA REP. BY THE INSPECTOR OF POLICE NATIONAL INVESTIGATION AGENCY CHENNAI BRANCH versus BARAKATHULLAH ETC.",
        "start_char": 1639,
        "end_char": 1939,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_009",
        "query_id": "M16_Q009",
        "category": "tax_tds_section_194h",
        "question": "Are telecom operators required to deduct TDS under Section 194-H on SIM cards distributed to franchisees?",
        "claim_sentence": "Telecom operators selling prepaid SIM cards may deposit TDS under Section 194-H without determining principal-agent status.",
        "gold_support_label": "partially_supported",
        "document_id": "2024_2_1001_1038",
        "case_title": "BHARTI CELLULAR LIMITED (NOW BHARTI AIRTEL LIMITED) versus ASSISTANT COMMISSIONER OF INCOME TAX, CIRCLE 57, KOLKATA AND ANOTHER",
        "start_char": 1388,
        "end_char": 1688,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_010",
        "query_id": "M16_Q010",
        "category": "workman_definition_supervisory",
        "question": "Does performing supervisory duties exclude an employee from the definition of workman under Section 2(s)?",
        "claim_sentence": "An employee performing supervisory duties is unconditionally excluded from being a workman under Section 2(s) of the Industrial Disputes Act.",
        "gold_support_label": "partially_supported",
        "document_id": "2024_4_100_120",
        "case_title": "M/S BHARTI AIRTEL LIMITED versus A.S. RAGHAVENDRA",
        "start_char": 628,
        "end_char": 928,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_011",
        "query_id": "M16_Q011",
        "category": "mortgage_redemption_limitation",
        "question": "Can a mortgagor redeem mortgaged property at any time without limitation?",
        "claim_sentence": "A mortgagor under a mortgage by conditional sale may deposit the redemption money without any limitation period.",
        "gold_support_label": "partially_supported",
        "document_id": "2024_8_1002_1023",
        "case_title": "A.B. GOVARDHAN versus P. RAGOTHAMAN",
        "start_char": 1098,
        "end_char": 1398,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_012",
        "query_id": "M16_Q012",
        "category": "companies_act_directors",
        "question": "What is the liability of independent directors under the Companies Act 2013?",
        "claim_sentence": "Independent directors are exempted from liability under the Companies Act 2013 for unauthorized corporate borrowing.",
        "gold_support_label": "unsupported",
        "document_id": "2024_1_1062_1082",
        "case_title": "ADV BABASAHEB WASADE & ORS versus MANOHAR GANGADHAR MUDDESHWAR & ORS",
        "start_char": 1355,
        "end_char": 1655,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_013",
        "query_id": "M16_Q013",
        "category": "undertrial_default_bail",
        "question": "When are undertrial prisoners entitled to release under Section 436A CrPC?",
        "claim_sentence": "Under Section 436A CrPC every undertrial prisoner who served one-third maximum sentence is entitled to default bail.",
        "gold_support_label": "unsupported",
        "document_id": "2024_5_1038_1055",
        "case_title": "IN RE-INHUMAN CONDITIONS IN 1382 PRISONS versus",
        "start_char": 1097,
        "end_char": 1397,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_014",
        "query_id": "M16_Q014",
        "category": "sarfaesi_agricultural_land",
        "question": "Can secured creditors enforce security interest over agricultural land under SARFAESI?",
        "claim_sentence": "A secured creditor under the SARFAESI Act may take possession of agricultural land without approaching the Debts Recovery Tribunal.",
        "gold_support_label": "unsupported",
        "document_id": "2024_8_1024_1046",
        "case_title": "BANGALORE ELECTRICITY SUPPLY COMPANY LIMITED versus HIREHALLI SOLAR POWER PROJECT LLP & OTHERS",
        "start_char": 2369,
        "end_char": 2669,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_015",
        "query_id": "M16_Q015",
        "category": "maternity_benefit_contractual",
        "question": "Are female contractual employees entitled to paid maternity leave?",
        "claim_sentence": "A female employee on contractual appointment is entitled to 26 weeks paid maternity leave under the Maternity Benefit Act.",
        "gold_support_label": "unsupported",
        "document_id": "2024_9_135_149",
        "case_title": "ANANTDEEP SINGH versus THE HIGH COURT OF PUNJAB AND HARYANA AT CHANDIGARH & ANR.",
        "start_char": 1580,
        "end_char": 1880,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_016",
        "query_id": "M16_Q016",
        "category": "quashing_defrauding_state",
        "question": "Can criminal proceedings involving defrauding the State be quashed on the basis of a private compromise?",
        "claim_sentence": "The Court held that the High Court may order quashing of criminal proceedings under Section 482 on private compromise even if the offence involves defrauding the State.",
        "gold_support_label": "contradicted",
        "document_id": "2024_3_1004_1008",
        "case_title": "STATE OF HARYANA versus DR. RITU SINGH AND ANOTHER",
        "start_char": 862,
        "end_char": 1162,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_017",
        "query_id": "M16_Q017",
        "category": "ibc_extension_sra_deposit",
        "question": "Does the NCLAT have jurisdiction to extend the deadline for resolution deposit by the SRA?",
        "claim_sentence": "The NCLAT cannot extend the time period for payment of the resolution amount by the successful resolution applicant.",
        "gold_support_label": "contradicted",
        "document_id": "2024_1_1045_1061",
        "case_title": "STATE BANK OF INDIA AND ORS versus E CONSORTIUM OF MR MURARI LAL JALAN AND MR FLORIAN FRITSCH AND ANR",
        "start_char": 1461,
        "end_char": 1761,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_018",
        "query_id": "M16_Q018",
        "category": "criminal_appeal_reversal_acquittal",
        "question": "Did the Supreme Court affirm the acquittal based on family witness testimonies?",
        "claim_sentence": "The Supreme Court affirmed the High Court order acquitting the accused and ruled that the testimony of the family members was untrustworthy.",
        "gold_support_label": "contradicted",
        "document_id": "2024_2_1039_1053",
        "case_title": "STATE OF PUNJAB versus GURPREET SINGH & ORS.",
        "start_char": 994,
        "end_char": 1294,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_019",
        "query_id": "M16_Q019",
        "category": "matrimonial_abuse_quashing",
        "question": "Are omnibus allegations sufficient to sustain charges against a husband under Section 498A IPC?",
        "claim_sentence": "The Supreme Court dismissed the husband appeal and ruled that general allegations under Section 498A IPC are sufficient to frame charges.",
        "gold_support_label": "contradicted",
        "document_id": "2024_6_129_163",
        "case_title": "ACHIN GUPTA versus STATE OF HARYANA & ANR.",
        "start_char": 1195,
        "end_char": 1495,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M16_UNSEEN_020",
        "query_id": "M16_Q020",
        "category": "coparcenary_female_rights",
        "question": "Are female heirs barred from equal coparcenary rights if a partition occurred prior to 2005?",
        "claim_sentence": "Female heirs cannot claim equal partition rights in ancestral property if a preliminary partition occurred before 2005.",
        "gold_support_label": "contradicted",
        "document_id": "2024_11_1013_1041",
        "case_title": "RAMACHANDRAN & ORS. versus VIJAYAN & ORS.",
        "start_char": 1381,
        "end_char": 1681,
        "structural_label": "headnote_holding",
    },
]


def run_evaluation() -> Dict[str, Any]:
    verifier = ClaimVerifier()
    jsonl_records = []
    y_true = []
    y_pred = []
    evaluated_cases = []

    for c in UNSEEN_CASES:
        doc_path = Path("data/processed/aws_sc") / f"{c['document_id']}.json"
        doc_data = json.loads(doc_path.read_text(encoding="utf-8"))
        full_text = doc_data.get("full_text", "")
        passage_text = full_text[c["start_char"]:c["end_char"]]

        ep = EvidencePassage(
            evidence_id="E1",
            document_id=c["document_id"],
            case_title=c["case_title"],
            passage_text=passage_text,
            start_char=c["start_char"],
            end_char=c["end_char"],
            structural_label=c["structural_label"],
        )

        res = verifier.verify_claim(claim_text=c["claim_sentence"], cited_passages=[ep], query=c["question"])

        record = {
            "case_id": c["case_id"],
            "query_id": c["query_id"],
            "category": c["category"],
            "question": c["question"],
            "claim_sentence": c["claim_sentence"],
            "gold_support_label": c["gold_support_label"],
            "predicted_status": res.status.value,
            "verification_method": res.method,
            "verification_reason": res.reason,
            "unresolved_uncertainty": res.unresolved_uncertainty,
            "is_contradicted": res.is_contradicted,
            "omits_statutory_qualification": res.omits_statutory_qualification,
            "claim_overgeneralizes_holding": res.claim_overgeneralizes_holding,
            "cited_evidence_ids": ["E1"],
            "supporting_passages": [
                {
                    "evidence_id": "E1",
                    "document_id": c["document_id"],
                    "case_title": c["case_title"],
                    "start_char": c["start_char"],
                    "end_char": c["end_char"],
                    "structural_label": c["structural_label"],
                    "passage_text": passage_text,
                }
            ],
            "evaluation_milestone": "milestone_16",
            "is_unstudied_2024_judgment": True,
        }
        jsonl_records.append(record)

        y_true.append(c["gold_support_label"])
        y_pred.append(res.status.value)

        evaluated_cases.append({
            "case_id": c["case_id"],
            "gold": c["gold_support_label"],
            "predicted": res.status.value,
            "method": res.method,
            "match": (c["gold_support_label"] == res.status.value),
        })

    # Save JSONL
    jsonl_path = Path("evaluation/rag/milestone16_unseen_claims.jsonl")
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in jsonl_records:
            f.write(json.dumps(r) + "\n")

    # Compute metrics
    metrics = compute_metrics(y_true, y_pred)

    # Safe answer aggregation audit
    safe_violations = 0
    for t, p in zip(y_true, y_pred):
        if p == "supported" and t != "supported":
            safe_violations += 1

    summary = {
        "milestone": "Milestone 16 - Unseen Claim Verification Evaluation",
        "dataset_file": str(jsonl_path),
        "total_unseen_claims": len(UNSEEN_CASES),
        "unstudied_judgments_used": len({c["document_id"] for c in UNSEEN_CASES}),
        "distribution_of_gold_labels": {
            "supported": sum(1 for t in y_true if t == "supported"),
            "partially_supported": sum(1 for t in y_true if t == "partially_supported"),
            "unsupported": sum(1 for t in y_true if t == "unsupported"),
            "contradicted": sum(1 for t in y_true if t == "contradicted"),
            "not_evaluated": sum(1 for t in y_true if t == "not_evaluated"),
        },
        "evaluation_metrics": metrics,
        "safe_answer_aggregation": {
            "total_answers_evaluated": len(UNSEEN_CASES),
            "safe_promotions_violated": safe_violations,
            "safe_promotion_compliance_rate": round(1.0 - (safe_violations / len(UNSEEN_CASES)), 4),
            "non_supported_promoted_to_supported": safe_violations,
        },
        "evaluated_cases": evaluated_cases,
    }

    out_path = Path("evaluation/rag/milestone16_evaluation_results.json")
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return summary


if __name__ == "__main__":
    res = run_evaluation()
    print("Milestone 16 Evaluation completed successfully!")
    print(f"Total claims: {res['total_unseen_claims']}")
    print(f"Accuracy: {res['evaluation_metrics']['overall_accuracy']:.2%}")
    print(f"Supported class precision: {res['evaluation_metrics']['per_class_metrics']['supported']['precision']:.2%}")
    print(f"Supported class recall: {res['evaluation_metrics']['per_class_metrics']['supported']['recall']:.2%}")
    print(f"Non-supported false acceptances: {res['safe_answer_aggregation']['safe_promotions_violated']}")
    print(f"Overall non-supported FAR: {res['evaluation_metrics']['disaggregated_far']['overall_non_supported_far']:.2%}")
