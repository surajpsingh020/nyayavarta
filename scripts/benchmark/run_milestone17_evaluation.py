"""Run Milestone 17 Evaluation: Unseen Claim Verification & Frozen Baseline Benchmark.

Evaluates the revised ClaimVerifier on:
1. Milestone 17 Unseen Claims Dataset (30 newly curated cases from 30 unstudied judgments).
2. Milestone 16 Frozen Regression Baseline (20 cases, demonstrating resolution of the 3 false acceptances).

Outputs:
- evaluation/rag/milestone17_unseen_claims.jsonl
- evaluation/rag/milestone17_verification_results.json
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from services.rag.models import EvidencePassage
from services.rag.claim_verifier import ClaimVerifier
from scripts.benchmark.evaluate_milestone16_review import compute_metrics


M17_UNSEEN_CASES = [
    # --- 8 SUPPORTED CLAIMS ---
    {
        "case_id": "M17_UNSEEN_001",
        "query_id": "M17_Q001",
        "category": "negotiable_instruments_presumption",
        "question": "What is the legal presumption regarding indorsements on a negotiable instrument?",
        "claim_sentence": "Under Section 118(e) of the Negotiable Instruments Act, there is a legal presumption that indorsements on a negotiable instrument were made in the order in which they appear.",
        "gold_support_label": "supported",
        "document_id": "2024_1_1083_1089",
        "case_title": "AJITSINH CHEHUJI RATHOD versus STATE OF GUJARAT & ANR.",
        "start_char": 1450,
        "end_char": 1750,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_002",
        "query_id": "M17_Q002",
        "category": "ibc_resolution_plan_withdrawal",
        "question": "Can a successful resolution applicant withdraw a resolution plan once submitted?",
        "claim_sentence": "A resolution applicant cannot withdraw or modify a resolution plan once submitted under the Insolvency and Bankruptcy Code.",
        "gold_support_label": "supported",
        "document_id": "2024_3_1044_1050",
        "case_title": "DECCAN VALUE INVESTORS L.P. & ANR. versus DINKAR VENKATASUBRAMANIAN & ANR.",
        "start_char": 937,
        "end_char": 1237,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_003",
        "query_id": "M17_Q003",
        "category": "evidence_act_section_106",
        "question": "When does the burden of proof under Section 106 of the Evidence Act shift to the accused?",
        "claim_sentence": "Section 106 of the Evidence Act applies only after the prosecution has succeeded in proving primary facts from which a reasonable inference of guilt can be drawn.",
        "gold_support_label": "supported",
        "document_id": "2024_6_164_213",
        "case_title": "ANEES versus THE STATE GOVT. OF NCT",
        "start_char": 963,
        "end_char": 1263,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_004",
        "query_id": "M17_Q004",
        "category": "revenue_entries_title",
        "question": "Do revenue mutation entries confer or extinguish ownership title in immovable property?",
        "claim_sentence": "Revenue entries are not documents of title and do not confer or extinguish title in land.",
        "gold_support_label": "supported",
        "document_id": "2024_6_1_9",
        "case_title": "RAM BALAK SINGH versus STATE OF BIHAR AND ORS.",
        "start_char": 1301,
        "end_char": 1601,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_005",
        "query_id": "M17_Q005",
        "category": "cpc_section_100_substantial_question",
        "question": "Can the High Court decide a second appeal under Section 100 CPC without formulating substantial questions of law?",
        "claim_sentence": "The High Court cannot decide a second appeal under Section 100 CPC without formulating substantial questions of law.",
        "gold_support_label": "supported",
        "document_id": "2024_7_1040_1043",
        "case_title": "NEK PAL & ORS. versus NAGAR PALIKA PARISHAD, KASHIPUR",
        "start_char": 500,
        "end_char": 800,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_006",
        "query_id": "M17_Q006",
        "category": "article_21_speedy_trial",
        "question": "Is the right to a speedy trial recognized as a fundamental right of an undertrial prisoner?",
        "claim_sentence": "An undertrial prisoner has a fundamental right to speedy trial under Article 21 of the Constitution.",
        "gold_support_label": "supported",
        "document_id": "2024_7_1054_1070",
        "case_title": "SHEIKH JAVED IQBAL @ ASHFAQ ANSARI @ JAVED ANSARI versus STATE OF U.P.",
        "start_char": 862,
        "end_char": 1162,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_007",
        "query_id": "M17_Q007",
        "category": "pmla_delay_bail_constitutional",
        "question": "Can an accused obtain bail in PMLA proceedings on the grounds of prolonged incarceration?",
        "claim_sentence": "Prolonged incarceration coupled with delay in trial may entitle an accused to bail as a constitutional remedy.",
        "gold_support_label": "supported",
        "document_id": "2024_8_1061_1085",
        "case_title": "MANISH SISODIA versus DIRECTORATE OF ENFORCEMENT",
        "start_char": 1457,
        "end_char": 1757,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_008",
        "query_id": "M17_Q008",
        "category": "motor_vehicles_owner_possession",
        "question": "Is the definition of owner under the Motor Vehicles Act restricted exclusively to the registered owner?",
        "claim_sentence": "The definition of owner under the Motor Vehicles Act is not strictly limited to the registered owner when another person has de facto possession and control.",
        "gold_support_label": "supported",
        "document_id": "2024_9_16_36",
        "case_title": "VAIBHAV JAIN versus HINDUSTAN MOTORS PVT. LTD. & ANR.",
        "start_char": 1392,
        "end_char": 1692,
        "structural_label": "headnote_holding",
    },

    # --- 8 PARTIALLY SUPPORTED CLAIMS ---
    {
        "case_id": "M17_UNSEEN_009",
        "query_id": "M17_Q009",
        "category": "sc_st_act_anticipatory_bail",
        "question": "Can anticipatory bail be granted in offences under the SC/ST Act without examining basic ingredients?",
        "claim_sentence": "Anticipatory bail can be granted in offences under the SC/ST Act without examining whether a prima facie case is made out.",
        "gold_support_label": "partially_supported",
        "document_id": "2024_8_1086_1145",
        "case_title": "SHAJAN SKARIA versus THE STATE OF KERALA AND ANR.",
        "start_char": 928,
        "end_char": 1228,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_010",
        "query_id": "M17_Q010",
        "category": "section_306_ipc_mens_rea",
        "question": "Can an accused be convicted of abetting suicide on mere domestic discord?",
        "claim_sentence": "A person can be convicted for abetting suicide whenever the victim commits suicide following domestic discord.",
        "gold_support_label": "partially_supported",
        "document_id": "2024_2_1054_1064",
        "case_title": "M. VIJAYAKUMAR versus STATE OF TAMIL NADU",
        "start_char": 916,
        "end_char": 1216,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_011",
        "query_id": "M17_Q011",
        "category": "consumer_protection_medical_negligence",
        "question": "Must a consumer forum decide medical negligence claims solely on Medical Council reports?",
        "claim_sentence": "A consumer forum must decide medical negligence cases based on the report of the Medical Council.",
        "gold_support_label": "partially_supported",
        "document_id": "2024_2_1065_1071",
        "case_title": "NAJRUL SEIKH versus DR. SUMIT BANERJEE & ANR.",
        "start_char": 941,
        "end_char": 1241,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_012",
        "query_id": "M17_Q012",
        "category": "post_disposal_modification_application",
        "question": "Can a party seek substantive review of a final Supreme Court order via a modification application?",
        "claim_sentence": "A party may file an application for modification of a final Supreme Court order to seek substantive relief.",
        "gold_support_label": "partially_supported",
        "document_id": "2024_3_1023_1043",
        "case_title": "JAIPUR VIDYUT VITRAN NIGAM LTD. & ORS. versus ADANI POWER RAJASTHAN LTD. & ANR.",
        "start_char": 685,
        "end_char": 985,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_013",
        "query_id": "M17_Q013",
        "category": "public_auction_highest_bidder_right",
        "question": "Does being the highest bidder in a public auction confer an automatic right to property allotment?",
        "claim_sentence": "The highest bidder in a public auction acquires a vested legal right to allotment of the property.",
        "gold_support_label": "partially_supported",
        "document_id": "2024_4_1_12",
        "case_title": "LEVEL 9 BIZ PVT. LTD. versus HIMACHAL PRADESH HOUSING AND URBAN DEVELOPMENT AUTHORITY & ANR.",
        "start_char": 1924,
        "end_char": 2224,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_014",
        "query_id": "M17_Q014",
        "category": "lis_pendens_execution_stage",
        "question": "Does the doctrine of lis pendens under Section 52 TPA apply only during the trial stage?",
        "claim_sentence": "The doctrine of lis pendens under Section 52 of the Transfer of Property Act applies only during the trial of the suit.",
        "gold_support_label": "partially_supported",
        "document_id": "2024_5_1148_1158",
        "case_title": "CHANDER BHAN (D) THROUGH LR SHER SINGH versus MUKHTIAR SINGH & ORS.",
        "start_char": 1364,
        "end_char": 1664,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_015",
        "query_id": "M17_Q015",
        "category": "unstamped_document_admissibility",
        "question": "Can an unstamped instrument be admitted in evidence under any circumstances?",
        "claim_sentence": "An unstamped document cannot be admitted in evidence under any circumstances.",
        "gold_support_label": "partially_supported",
        "document_id": "2024_9_166_185",
        "case_title": "SEETHARAMA SHETTY versus MONAPPA SHETTY",
        "start_char": 1721,
        "end_char": 2021,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_016",
        "query_id": "M17_Q016",
        "category": "select_list_appointment_right",
        "question": "Does placement of a candidate on a final select list confer an indefeasible right to appointment?",
        "claim_sentence": "Emplacement on a select list automatically confers an indefeasible constitutional right to appointment.",
        "gold_support_label": "partially_supported",
        "document_id": "2024_10_1344_1358",
        "case_title": "SHASHI BHUSHAN PRASAD SINGH versus THE STATE OF BIHAR AND ORS.",
        "start_char": 1952,
        "end_char": 2252,
        "structural_label": "headnote_holding",
    },

    # --- 7 UNSUPPORTED CLAIMS ---
    {
        "case_id": "M17_UNSEEN_017",
        "query_id": "M17_Q017",
        "category": "customs_confiscation_timeline",
        "question": "What is the statutory deadline for issuing a show cause notice following customs seizure?",
        "claim_sentence": "Under the Customs Act 1962, goods confiscated by the Directorate of Revenue Intelligence must be released within 60 days if no show cause notice is issued.",
        "gold_support_label": "unsupported",
        "document_id": "2024_1_1090_1099",
        "case_title": "AMIT KUMAR DAS, JOINT SECRETARY, BAITANI versus STATE OF ODISHA",
        "start_char": 1309,
        "end_char": 1609,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_018",
        "query_id": "M17_Q018",
        "category": "arbitration_unstamped_agreement",
        "question": "Can an arbitrator be appointed under Section 11 if an arbitration agreement is unstamped?",
        "claim_sentence": "Under the Arbitration and Conciliation Act, an arbitrator cannot be appointed if an arbitration agreement is not stamped.",
        "gold_support_label": "unsupported",
        "document_id": "2024_1_1100_1104",
        "case_title": "YAGWATI @ POONAM versus GHANSHYAM",
        "start_char": 1508,
        "end_char": 1808,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_019",
        "query_id": "M17_Q019",
        "category": "patents_act_section_3d",
        "question": "What is the therapeutic efficacy threshold under Section 3(d) of the Patents Act?",
        "claim_sentence": "A patent for a pharmaceutical substance can only be granted if enhanced therapeutic efficacy is demonstrated under Section 3(d) of the Patents Act.",
        "gold_support_label": "unsupported",
        "document_id": "2024_2_1072_1120",
        "case_title": "SATENDER KUMAR ANTIL versus CENTRAL BUREAU OF INVESTIGATION & ANR.",
        "start_char": 797,
        "end_char": 1097,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_020",
        "query_id": "M17_Q020",
        "category": "carriage_by_air_liability",
        "question": "What is the liability ceiling of an international airline for lost baggage under the Carriage by Air Act?",
        "claim_sentence": "Under the Carriage by Air Act, an airline is strictly liable for international baggage loss up to 1288 Special Drawing Rights.",
        "gold_support_label": "unsupported",
        "document_id": "2024_3_1014_1022",
        "case_title": "SOMNATH versus THE STATE OF MAHARASHTRA & ORS.",
        "start_char": 991,
        "end_char": 1291,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_021",
        "query_id": "M17_Q021",
        "category": "food_safety_central_license",
        "question": "What is the turnover threshold requiring a central food business license under FSSAI?",
        "claim_sentence": "Under the Food Safety and Standards Act, food business operators must obtain a central license if turnover exceeds twenty crore rupees.",
        "gold_support_label": "unsupported",
        "document_id": "2024_4_13_28",
        "case_title": "STATE OF KERALA versus UNION OF INDIA",
        "start_char": 2753,
        "end_char": 3053,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_022",
        "query_id": "M17_Q022",
        "category": "specific_relief_personal_service",
        "question": "Can contracts of personal service be specifically enforced by an order of court?",
        "claim_sentence": "Under the Specific Relief Act, a contract for personal service can be specifically enforced by an order of injunction.",
        "gold_support_label": "unsupported",
        "document_id": "2024_5_1056_1073",
        "case_title": "NATIONAL INVESTIGATION AGENCY NEW DELHI versus ZAHOOR AHMAD SHAH WATALI",
        "start_char": 1144,
        "end_char": 1444,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_023",
        "query_id": "M17_Q023",
        "category": "factories_act_weekly_hours",
        "question": "What is the maximum statutory weekly working hours for an adult worker under the Factories Act?",
        "claim_sentence": "Under the Factories Act 1948, no adult worker shall be required to work for more than 48 hours in any week.",
        "gold_support_label": "unsupported",
        "document_id": "2024_7_1044_1053",
        "case_title": "AJAY KUMAR BHALLA & ORS. versus PRAKASH KADAM & ORS.",
        "start_char": 1851,
        "end_char": 2151,
        "structural_label": "headnote_holding",
    },

    # --- 7 CONTRADICTED CLAIMS ---
    {
        "case_id": "M17_UNSEEN_024",
        "query_id": "M17_Q024",
        "category": "rule_against_bias_invalidation",
        "question": "Did the Supreme Court reject the allegation of bias against the selection committee?",
        "claim_sentence": "The Supreme Court dismissed the challenge and held that the rule against bias was not violated by the committee.",
        "gold_support_label": "contradicted",
        "document_id": "2024_4_151_233",
        "case_title": "KRISHNADATT AWASTHY versus STATE OF MADHYA PRADESH & ORS.",
        "start_char": 2075,
        "end_char": 2375,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_025",
        "query_id": "M17_Q025",
        "category": "promotion_criteria_merit_seniority",
        "question": "Can administrative circulars alter statutory promotion criteria from merit-cum-seniority to seniority-cum-merit?",
        "claim_sentence": "The Supreme Court upheld the High Court circular and ruled that seniority-cum-merit can validly replace the statutory merit-cum-seniority criteria.",
        "gold_support_label": "contradicted",
        "document_id": "2024_5_1074_1147",
        "case_title": "RAVIKUMAR DHANSUKHLAL MAHETA & ANR. versus HIGH COURT OF GUJARAT & ORS.",
        "start_char": 1082,
        "end_char": 1382,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_026",
        "query_id": "M17_Q026",
        "category": "evidence_act_section_145_contradiction",
        "question": "Is it mandatory to confront a witness with prior statements under Section 145 Evidence Act to prove contradictions?",
        "claim_sentence": "The Supreme Court affirmed the conviction and held that material contradictions need not be put to a witness under Section 145 of the Evidence Act.",
        "gold_support_label": "contradicted",
        "document_id": "2024_6_20_35",
        "case_title": "ALAUDDIN & ORS. versus THE STATE OF ASSAM",
        "start_char": 830,
        "end_char": 1130,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_027",
        "query_id": "M17_Q027",
        "category": "institutional_medical_safety_directive",
        "question": "Did the Supreme Court refuse to intervene in institutional safety protocols for medical personnel?",
        "claim_sentence": "The Supreme Court refused to intervene and ruled that hospital safety standards are exclusively within State executive discretion without any judicial oversight.",
        "gold_support_label": "contradicted",
        "document_id": "2024_8_1047_1060",
        "case_title": "IN RE: ALLEGED RAPE AND MURDER INCIDENT OF A TRAINEE DOCTOR IN R.G. KAR MEDICAL COLLEGE AND HOSPITAL, KOLKATA AND RELATED ISSUES versus",
        "start_char": 1106,
        "end_char": 1406,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_028",
        "query_id": "M17_Q028",
        "category": "collegium_recommendation_chief_justice",
        "question": "Does the Chief Justice of a High Court have unilateral authority to reject names recommended by the Supreme Court Collegium?",
        "claim_sentence": "The Chief Justice of a High Court has absolute unilateral authority to reject names recommended by the Supreme Court Collegium.",
        "gold_support_label": "contradicted",
        "document_id": "2024_9_150_165",
        "case_title": "CHIRAG BHANU SINGH & ANR. versus HIGH COURT OF HIMACHAL PRADESH & ORS.",
        "start_char": 1430,
        "end_char": 1730,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_029",
        "query_id": "M17_Q029",
        "category": "section_319_crpc_discharge_appeal",
        "question": "Did the Supreme Court uphold the summoning of the appellants under Section 319 CrPC?",
        "claim_sentence": "The Supreme Court dismissed the appeal and affirmed the order summoning the appellants to face trial for murder under Section 319 CrPC.",
        "gold_support_label": "contradicted",
        "document_id": "2024_10_1313_1343",
        "case_title": "RAMA DEVI versus THE STATE OF BIHAR AND ORS.",
        "start_char": 681,
        "end_char": 981,
        "structural_label": "headnote_holding",
    },
    {
        "case_id": "M17_UNSEEN_030",
        "query_id": "M17_Q030",
        "category": "municipal_taxation_exemption",
        "question": "Are private advertising concessionaires exempt from municipal advertisement taxes under the Patna Municipal Corporation Act?",
        "claim_sentence": "Private advertising concessionaires are exempt from payment of municipal advertising taxes under the Patna Municipal Corporation Act.",
        "gold_support_label": "contradicted",
        "document_id": "2024_10_1381_1403",
        "case_title": "THE PATNA MUNICIPAL CORPORATION & ORS. versus TRIBHUWAN KUMAR & ANR.",
        "start_char": 2252,
        "end_char": 2552,
        "structural_label": "headnote_holding",
    },
]


def run_milestone17_evaluation() -> Dict[str, Any]:
    verifier = ClaimVerifier()

    # 1. First, build and save milestone17_unseen_claims.jsonl (freezing labels)
    jsonl_records = []
    y_true_m17 = []
    y_pred_m17 = []
    m17_case_evals = []

    for c in M17_UNSEEN_CASES:
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
            "evaluation_milestone": "milestone_17",
            "is_unstudied_2024_judgment": True,
            "annotation_provenance": "developer_curated_frozen_pre_evaluation",
        }
        jsonl_records.append(record)

        y_true_m17.append(c["gold_support_label"])
        y_pred_m17.append(res.status.value)

        m17_case_evals.append({
            "case_id": c["case_id"],
            "gold": c["gold_support_label"],
            "predicted": res.status.value,
            "method": res.method,
            "match": (c["gold_support_label"] == res.status.value),
        })

    jsonl_path = Path("evaluation/rag/milestone17_unseen_claims.jsonl")
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in jsonl_records:
            f.write(json.dumps(r) + "\n")

    m17_metrics = compute_metrics(y_true_m17, y_pred_m17)

    # Check safe answer aggregation for M17
    m17_safe_violations = sum(1 for t, p in zip(y_true_m17, y_pred_m17) if p == "supported" and t != "supported")

    # 2. Evaluate the frozen M16 baseline (Regression Benchmark)
    m16_path = Path("evaluation/rag/milestone16_unseen_claims.jsonl")
    m16_records = [json.loads(l) for l in m16_path.read_text(encoding="utf-8").splitlines() if l.strip()]

    y_true_m16 = []
    y_pred_m16 = []
    m16_case_evals = []

    for item in m16_records:
        sp = item["supporting_passages"][0]
        ep = EvidencePassage(
            evidence_id=sp["evidence_id"],
            document_id=sp["document_id"],
            case_title=sp["case_title"],
            passage_text=sp["passage_text"],
            start_char=sp["start_char"],
            end_char=sp["end_char"],
            structural_label=sp["structural_label"],
        )
        res_m16 = verifier.verify_claim(item["claim_sentence"], [ep], query=item.get("question"))
        y_true_m16.append(item["gold_support_label"])
        y_pred_m16.append(res_m16.status.value)
        m16_case_evals.append({
            "case_id": item["case_id"],
            "gold": item["gold_support_label"],
            "predicted": res_m16.status.value,
            "method": res_m16.method,
            "match": (item["gold_support_label"] == res_m16.status.value),
        })

    m16_regression_metrics = compute_metrics(y_true_m16, y_pred_m16)
    m16_safe_violations = sum(1 for t, p in zip(y_true_m16, y_pred_m16) if p == "supported" and t != "supported")

    # 3. Assemble complete Milestone 17 results summary
    results_summary = {
        "milestone": "Milestone 17 - Legal Review Integration & Verifier Error Analysis",
        "independent_legal_review_status": "PENDING_EXTERNAL_REVIEW",
        "external_review_notes": "No qualified external legal reviewer completed annotations in this cycle; zero annotations fabricated.",
        "m17_unseen_evaluation": {
            "dataset_file": str(jsonl_path),
            "total_unseen_claims": len(M17_UNSEEN_CASES),
            "unstudied_judgments_used": len({c["document_id"] for c in M17_UNSEEN_CASES}),
            "provenance": "developer_curated_frozen_pre_evaluation",
            "distribution_of_gold_labels": {
                "supported": sum(1 for t in y_true_m17 if t == "supported"),
                "partially_supported": sum(1 for t in y_true_m17 if t == "partially_supported"),
                "unsupported": sum(1 for t in y_true_m17 if t == "unsupported"),
                "contradicted": sum(1 for t in y_true_m17 if t == "contradicted"),
            },
            "metrics": m17_metrics,
            "answer_level_safety": {
                "total_answers_evaluated": len(M17_UNSEEN_CASES),
                "safe_promotions_violated": m17_safe_violations,
                "safe_promotion_compliance_rate": round(1.0 - (m17_safe_violations / len(M17_UNSEEN_CASES)), 4),
            },
            "detailed_case_results": m17_case_evals,
        },
        "m16_regression_baseline_evaluation": {
            "dataset_file": str(m16_path),
            "total_claims": len(m16_records),
            "role": "frozen_regression_benchmark",
            "metrics": m16_regression_metrics,
            "answer_level_safety": {
                "total_answers_evaluated": len(m16_records),
                "safe_promotions_violated": m16_safe_violations,
                "safe_promotion_compliance_rate": round(1.0 - (m16_safe_violations / len(m16_records)), 4),
            },
            "detailed_case_results": m16_case_evals,
            "original_false_acceptances_resolved": {
                "M16_UNSEEN_007": {
                    "original_m16_prediction": "supported",
                    "revised_prediction": next(c["predicted"] for c in m16_case_evals if c["case_id"] == "M16_UNSEEN_007"),
                    "resolved": next(c["predicted"] for c in m16_case_evals if c["case_id"] == "M16_UNSEEN_007") != "supported",
                },
                "M16_UNSEEN_008": {
                    "original_m16_prediction": "supported",
                    "revised_prediction": next(c["predicted"] for c in m16_case_evals if c["case_id"] == "M16_UNSEEN_008"),
                    "resolved": next(c["predicted"] for c in m16_case_evals if c["case_id"] == "M16_UNSEEN_008") != "supported",
                },
                "M16_UNSEEN_020": {
                    "original_m16_prediction": "supported",
                    "revised_prediction": next(c["predicted"] for c in m16_case_evals if c["case_id"] == "M16_UNSEEN_020"),
                    "resolved": next(c["predicted"] for c in m16_case_evals if c["case_id"] == "M16_UNSEEN_020") != "supported",
                },
            },
        },
    }

    out_file = Path("evaluation/rag/milestone17_verification_results.json")
    out_file.write_text(json.dumps(results_summary, indent=2), encoding="utf-8")
    print(f"Milestone 17 Verification Results saved to {out_file}")

    return results_summary


if __name__ == "__main__":
    summary = run_milestone17_evaluation()
    m17 = summary["m17_unseen_evaluation"]
    print("=== MILESTONE 17 UNSEEN EVALUATION (30 CLAIMS) ===")
    print(f"Accuracy: {m17['metrics']['overall_accuracy']:.2%}")
    print(f"Supported Precision: {m17['metrics']['per_class_metrics']['supported']['precision']:.2%}")
    print(f"Supported Recall: {m17['metrics']['per_class_metrics']['supported']['recall']:.2%}")
    print(f"Overall Non-Supported FAR: {m17['metrics']['disaggregated_far']['overall_non_supported_far']:.2%}")
    print(f"Safe Promotion Violations: {m17['answer_level_safety']['safe_promotions_violated']}")
    print(f"Safe Compliance Rate: {m17['answer_level_safety']['safe_promotion_compliance_rate']:.2%}")
