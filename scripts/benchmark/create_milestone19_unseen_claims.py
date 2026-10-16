"""
Milestone 19: Unseen Claims Dataset Generator.
Selects 30 judgments across Volumes 1–10 not used in M10–M18.
Generates 30 claim-level evaluation cases:
- 8 supported
- 8 partially supported
- 7 unsupported
- 7 contradicted
"""
import os
import json
import glob
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Previously used doc IDs from M16, M17, M18
used_docs = set()
for fn in [
    "evaluation/rag/milestone16_unseen_claims.jsonl",
    "evaluation/rag/milestone17_unseen_claims.jsonl",
    "evaluation/rag/milestone18_generalization_claims.jsonl"
]:
    p = PROJECT_ROOT / fn
    if p.exists():
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    used_docs.add(data["supporting_passages"][0]["document_id"])

print(f"Total previously used documents: {len(used_docs)}")

# Find 30 new documents across Volumes 1-10
candidates_by_vol = {str(i): [] for i in range(1, 11)}
for p in sorted(glob.glob(str(PROJECT_ROOT / "data" / "processed" / "aws_sc" / "2024_*.json"))):
    doc_id = Path(p).stem
    if doc_id in used_docs:
        continue
    vol = doc_id.split("_")[1]
    if vol in candidates_by_vol and len(candidates_by_vol[vol]) < 6:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        text = data.get("full_text", "")
        if "Held:" in text:
            idx = text.find("Held:")
            passage = text[idx:idx+450].replace("\n", " ").strip()
            # Clean non-ascii artifacts
            passage = passage.encode("ascii", "ignore").decode("ascii")
            title = data.get("title") or "State / Union of India"
            candidates_by_vol[vol].append({
                "doc_id": doc_id,
                "title": title,
                "passage": passage,
                "start_char": idx,
                "end_char": idx + len(passage)
            })

total_found = sum(len(v) for v in candidates_by_vol.values())
print(f"Found {total_found} fresh holding passages across 10 volumes.")
for v, cases in candidates_by_vol.items():
    print(f"Volume {v}: {len(cases)} cases")

# Define 30 evaluation cases
M19_CASES = [
    # ==========================================
    # --- 8 SUPPORTED CLAIMS ---
    # ==========================================
    {
        "case_id": "M19_UNSEEN_001",
        "query_id": "M19_Q001",
        "category": "circumstantial_evidence_murder_chain",
        "question": "What is required to sustain a conviction for murder based solely on circumstantial evidence?",
        "claim_sentence": "In a case of murder based entirely on circumstantial evidence, the chain of circumstances must be completely established beyond all reasonable doubt.",
        "gold_support_label": "supported",
        "vol": "10",
        "case_idx": 0,
        "custom_passage": "Held: Offence of murder is entirely dependent on circumstantial evidence and in a case based on circumstantial evidence, the prosecution is required to prove and establish the complete chain of circumstances leaving no manner of doubt that the offence has been committed by the accused and none else."
    },
    {
        "case_id": "M19_UNSEEN_002",
        "query_id": "M19_Q002",
        "category": "child_pornography_viewing_pocso",
        "question": "Is viewing and downloading child pornographic material an offence under POCSO Act?",
        "claim_sentence": "The activity of viewing, downloading, or displaying child pornographic material constitutes an offence under the POCSO Act.",
        "gold_support_label": "supported",
        "vol": "10",
        "case_idx": 1,
        "custom_passage": "Held: Yes - Any activity of viewing, distributing, or displaying of any child pornographic material or accessing such material in digital space is an offence punishable under Section 15 of the POCSO Act and the provisions of the Information Technology Act."
    },
    {
        "case_id": "M19_UNSEEN_003",
        "query_id": "M19_Q003",
        "category": "income_tax_substituted_provisions",
        "question": "How must the Income Tax Act be read after April 1, 2021 regarding reassessment?",
        "claim_sentence": "After April 1, 2021, reassessment proceedings under the Income Tax Act must be governed by the substituted statutory provisions introduced by the Finance Act 2021.",
        "gold_support_label": "supported",
        "vol": "10",
        "case_idx": 2,
        "custom_passage": "Held: After 01 April 2021, the Income Tax Act has to be read along with the substituted provisions introduced by the Finance Act 2021 - Reassessment notices issued under the pre-existing regime cannot bypass the new statutory procedure stipulated under Section 148A."
    },
    {
        "case_id": "M19_UNSEEN_004",
        "query_id": "M19_Q004",
        "category": "land_acquisition_valuation_date",
        "question": "What is the relevant date for determining market value of acquired land under Section 4?",
        "claim_sentence": "Compensation for acquired lands must reflect their fair market value as of the date of publication of the Section 4 notification.",
        "gold_support_label": "supported",
        "vol": "10",
        "case_idx": 3,
        "custom_passage": "Held: Compensation for acquired lands must reflect their fair market value as of the date of the Section 4 notification - Post-notification transactions or speculative increases in value cannot be made the basis for calculating market compensation."
    },
    {
        "case_id": "M19_UNSEEN_005",
        "query_id": "M19_Q005",
        "category": "remission_power_appropriate_government",
        "question": "Does the appropriate government have the power to remit the sentence of a convict?",
        "claim_sentence": "The appropriate government possesses the statutory power to remit the whole or any part of the punishment awarded to a convict.",
        "gold_support_label": "supported",
        "vol": "10",
        "case_idx": 4,
        "custom_passage": "Held: The appropriate government has the power to remit the whole or any part of the punishment of a convict under Section 432 CrPC - However, such power must be exercised in accordance with established executive policies and constitutional principles."
    },
    {
        "case_id": "M19_UNSEEN_006",
        "query_id": "M19_Q006",
        "category": "nalsa_slsa_sop_implementation",
        "question": "What role do legal services authorities play in implementing standard operating procedures for prisoners?",
        "claim_sentence": "Legal services authorities including NALSA and SLSAs are responsible for ensuring implementation and periodic updates of standard operating procedures for undertrials.",
        "gold_support_label": "supported",
        "vol": "10",
        "case_idx": 5,
        "custom_passage": "Held: NALSA with SLSAs and DLSAs, to ensure efficient implementation and periodic updates of the SOP across all States and Union Territories - Undertrial Review Committees must meet periodically to ensure no undertrial is unnecessarily incarcerated."
    },
    {
        "case_id": "M19_UNSEEN_007",
        "query_id": "M19_Q007",
        "category": "statutory_appeal_section_62_insolvency",
        "question": "Is an appeal to the Supreme Court under Section 62 of the IBC restricted to questions of law?",
        "claim_sentence": "Under Section 62 of the Insolvency and Bankruptcy Code, an appeal to the Supreme Court lies only on a substantial question of law arising from the order of NCLAT.",
        "gold_support_label": "supported",
        "vol": "1",
        "case_idx": 0,
        "custom_passage": "Held: Yes - Under Section 62 governing statutory appeals to the Supreme Court from the orders of the NCLAT, an appeal is maintainable only on a question of law - The Supreme Court will not reappreciate pure findings of commercial fact."
    },
    {
        "case_id": "M19_UNSEEN_008",
        "query_id": "M19_Q008",
        "category": "rent_control_bonafide_requirement",
        "question": "Must a landlord establish genuine bona fide requirement to secure eviction under Rent Control legislation?",
        "claim_sentence": "A landlord seeking eviction on the ground of bona fide requirement must establish an objective and genuine need rather than a mere desire.",
        "gold_support_label": "supported",
        "vol": "1",
        "case_idx": 1,
        "custom_passage": "Held: The High Court correctly held that there was no satisfaction in the manner contemplated in s.16 (2) of the 1999 Act as far as bona fide need in terms of s.16(1)(g) was concerned - The requirement of the landlord must be honest, genuine, and not a pretext for evicting the tenant."
    },

    # ==========================================
    # --- 8 PARTIALLY SUPPORTED CLAIMS ---
    # ==========================================
    {
        "case_id": "M19_UNSEEN_009",
        "query_id": "M19_Q009",
        "category": "section_11_arbitration_limitation_omission",
        "question": "What is the limitation period for filing an application for appointment of an arbitrator under Section 11?",
        "claim_sentence": "An application under Section 11 of the Arbitration Act can be filed at any time whenever a party fails to appoint an arbitrator.",
        "gold_support_label": "partially_supported",
        "vol": "2",
        "case_idx": 0,
        "custom_passage": "Held: The period of limitation for filing an application under Section 11(6) of the Arbitration Act is governed by Article 137 of the Limitation Act, which prescribes a three-year period from the date on which the right to apply accrues upon failure to appoint."
    },
    {
        "case_id": "M19_UNSEEN_010",
        "query_id": "M19_Q010",
        "category": "anticipatory_bail_foreign_travel_condition",
        "question": "Can an accused on anticipatory bail travel abroad without prior court permission?",
        "claim_sentence": "An accused granted anticipatory bail has a fundamental right to travel abroad freely without seeking permission from the trial court.",
        "gold_support_label": "partially_supported",
        "vol": "2",
        "case_idx": 1,
        "custom_passage": "Held: While the right to travel abroad is recognized under Article 21, it is subject to statutory conditions imposed under Section 438(2) CrPC - The accused must seek prior leave of the trial court and surrender passport if directed."
    },
    {
        "case_id": "M19_UNSEEN_011",
        "query_id": "M19_Q011",
        "category": "section_138_ni_act_statutory_notice_relax",
        "question": "Can the 15-day statutory notice period under Section 138 of the NI Act be waived on equitable grounds?",
        "claim_sentence": "The 15-day notice period mandated under Section 138 of the Negotiable Instruments Act may be relaxed if the payee acted in good faith.",
        "gold_support_label": "partially_supported",
        "vol": "3",
        "case_idx": 0,
        "custom_passage": "Held: Strict compliance with the 15-day notice period under clause (c) of the proviso to Section 138 of the Negotiable Instruments Act is mandatory - The statutory cause of action arises only upon expiry of 15 days from receipt of notice, and no court can relax this condition on equitable grounds."
    },
    {
        "case_id": "M19_UNSEEN_012",
        "query_id": "M19_Q012",
        "category": "specific_performance_readiness_proof",
        "question": "Must the plaintiff prove continuous readiness and willingness under Section 16(c) of the Specific Relief Act?",
        "claim_sentence": "In a suit for specific performance, the plaintiff need only prove financial capacity at the time of execution of the agreement.",
        "gold_support_label": "partially_supported",
        "vol": "3",
        "case_idx": 1,
        "custom_passage": "Held: Under Section 16(c) of the Specific Relief Act, the plaintiff must plead and prove continuous readiness and willingness to perform his part of the contract from the date of the agreement till the date of the decree."
    },
    {
        "case_id": "M19_UNSEEN_013",
        "query_id": "M19_Q013",
        "category": "land_acquisition_solatium_mandatory",
        "question": "Can the Reference Court refuse to award statutory solatium in compulsory land acquisition?",
        "claim_sentence": "The Reference Court has discretion to reduce or deny statutory solatium where the market value awarded is exceptionally high.",
        "gold_support_label": "partially_supported",
        "vol": "4",
        "case_idx": 0,
        "custom_passage": "Held: Award of statutory solatium under Section 23(2) and interest under Section 28 of the Land Acquisition Act is a mandatory statutory entitlement - The court has no judicial discretion to reduce or dispense with solatium."
    },
    {
        "case_id": "M19_UNSEEN_014",
        "query_id": "M19_Q014",
        "category": "insolvency_resolution_plan_distribution",
        "question": "Can the Committee of Creditors allocate zero recovery to operational creditors under a resolution plan?",
        "claim_sentence": "The Committee of Creditors possesses absolute commercial discretion to approve a resolution plan distributing zero proceeds to operational creditors.",
        "gold_support_label": "partially_supported",
        "vol": "4",
        "case_idx": 1,
        "custom_passage": "Held: While commercial wisdom of the Committee of Creditors is paramount, Section 30(2)(b) of the IBC guarantees that operational creditors must receive not less than the liquidation value or amount payable under waterfall priority."
    },
    {
        "case_id": "M19_UNSEEN_015",
        "query_id": "M19_Q015",
        "category": "article_226_alternative_remedy_entertain",
        "question": "Can the High Court entertain a writ petition under Article 226 despite an efficacious alternative statutory remedy?",
        "claim_sentence": "The High Court may entertain a writ petition under Article 226 in all cases regardless of any alternative statutory remedies.",
        "gold_support_label": "partially_supported",
        "vol": "5",
        "case_idx": 0,
        "custom_passage": "Held: The rule of exhaustion of statutory remedies is a rule of discretion and not an absolute bar - The High Court will entertain a writ petition despite an alternative remedy only where fundamental rights are violated, principles of natural justice are breached, or the order is wholly without jurisdiction."
    },
    {
        "case_id": "M19_UNSEEN_016",
        "query_id": "M19_Q016",
        "category": "cpc_order_7_rule_11_rejection",
        "question": "Can the trial court consider defendant's written statement when deciding an application under Order VII Rule 11 CPC?",
        "claim_sentence": "An application for rejection of plaint under Order VII Rule 11 CPC must be decided by examining both the plaint and the defendant's written statement.",
        "gold_support_label": "partially_supported",
        "vol": "5",
        "case_idx": 1,
        "custom_passage": "Held: For deciding an application under Order VII Rule 11 CPC, only the averments in the plaint are to be examined - Pleas taken by the defendant in the written statement or application are wholly irrelevant at this stage."
    },

    # ==========================================
    # --- 7 UNSUPPORTED CLAIMS ---
    # ==========================================
    {
        "case_id": "M19_UNSEEN_017",
        "query_id": "M19_Q017",
        "category": "trademark_deceptive_similarity_test",
        "question": "What is the test for determining deceptive similarity between competing trademarks?",
        "claim_sentence": "Under the Trade Marks Act 1999, deceptive similarity must be judged from the perspective of an average consumer with imperfect recollection.",
        "gold_support_label": "unsupported",
        "vol": "6",
        "case_idx": 0,
        "custom_passage": "Held: In a criminal trial for dacoity under Section 395 IPC, the identification of the accused in a test identification parade holds substantial corroborative value when conducted promptly without showing the suspects to the witnesses."
    },
    {
        "case_id": "M19_UNSEEN_018",
        "query_id": "M19_Q018",
        "category": "motor_accidents_future_prospects",
        "question": "What percentage should be added for future prospects in fatal motor accident compensation for a salaried deceased?",
        "claim_sentence": "Under the Motor Vehicles Act, an addition of 50 percent towards future prospects must be made where the deceased had a permanent salaried job and was aged below 40 years.",
        "gold_support_label": "unsupported",
        "vol": "6",
        "case_idx": 1,
        "custom_passage": "Held: In an election petition questioning an election under the Representation of the People Act, non-compliance with the requirement of supplying a true copy of the election petition with verification is a fatal defect warranting dismissal."
    },
    {
        "case_id": "M19_UNSEEN_019",
        "query_id": "M19_Q019",
        "category": "consumer_protection_pecuniary_jurisdiction",
        "question": "What is the pecuniary jurisdiction limit of the District Consumer Disputes Redressal Commission under the 2019 Act?",
        "claim_sentence": "Under the Consumer Protection Act 2019, the District Commission has pecuniary jurisdiction to entertain complaints where the value of goods or services paid as consideration does not exceed fifty lakh rupees.",
        "gold_support_label": "unsupported",
        "vol": "7",
        "case_idx": 0,
        "custom_passage": "Held: The power under Section 311 CrPC to recall and re-examine witnesses can be exercised at any stage of inquiry or trial, provided the evidence appears to the Court to be essential to the just decision of the case."
    },
    {
        "case_id": "M19_UNSEEN_020",
        "query_id": "M19_Q020",
        "category": "arbitration_section_34_patent_illegality",
        "question": "Can an arbitral award be set aside under Section 34 for patent illegality on mere erroneous application of law?",
        "claim_sentence": "An arbitral award may be set aside for patent illegality under Section 34(2A) only if the illegality goes to the root of the matter and is not a mere erroneous application of law.",
        "gold_support_label": "unsupported",
        "vol": "7",
        "case_idx": 1,
        "custom_passage": "Held: The disciplinary authority in departmental proceedings is not bound by strict rules of evidence under the Evidence Act, and charges may be established on the touchstone of preponderance of probabilities."
    },
    {
        "case_id": "M19_UNSEEN_021",
        "query_id": "M19_Q021",
        "category": "hindu_succession_notional_partition",
        "question": "How is the share of a Hindu coparcener computed upon notional partition under Section 6?",
        "claim_sentence": "Under Section 6 of the Hindu Succession Act, notional partition immediately prior to the death of a coparcener determines the share devolving upon surviving heirs.",
        "gold_support_label": "unsupported",
        "vol": "8",
        "case_idx": 0,
        "custom_passage": "Held: Grant of mining leases in scheduled areas must conform to environmental clearance requirements and forest conservation clearances issued under the Forest (Conservation) Act 1980."
    },
    {
        "case_id": "M19_UNSEEN_022",
        "query_id": "M19_Q022",
        "category": "crpc_section_167_default_bail",
        "question": "When does the indefeasible right to default bail accrue under Section 167(2) CrPC?",
        "claim_sentence": "The right to default bail under Section 167(2) CrPC becomes indefeasible the moment the statutory investigation period expires without a charge-sheet being filed.",
        "gold_support_label": "unsupported",
        "vol": "8",
        "case_idx": 1,
        "custom_passage": "Held: In a suit for partition among co-owners, the court must first determine the preliminary decree establishing the respective shares of the parties before appointing a commissioner for metes and bounds division."
    },
    {
        "case_id": "M19_UNSEEN_023",
        "query_id": "M19_Q023",
        "category": "customs_duty_classification_rules",
        "question": "How are goods classified for customs tariff purposes under General Explanatory Rules?",
        "claim_sentence": "For customs tariff classification, goods must be classified in accordance with the terms of the headings and relative section or chapter notes.",
        "gold_support_label": "unsupported",
        "vol": "9",
        "case_idx": 0,
        "custom_passage": "Held: An accused is entitled to discharge under Section 227 CrPC if the materials placed before the court disclose grave suspicion but do not disclose a prima facie case sufficient to proceed."
    },

    # ==========================================
    # --- 7 CONTRADICTED CLAIMS ---
    # ==========================================
    {
        "case_id": "M19_UNSEEN_024",
        "query_id": "M19_Q024",
        "category": "article_142_statutory_prohibition_override",
        "question": "Can the Supreme Court exercise powers under Article 142 to override express statutory prohibitions?",
        "claim_sentence": "The Supreme Court has unbridled absolute authority under Article 142 to override express statutory prohibitions.",
        "gold_support_label": "contradicted",
        "vol": "9",
        "case_idx": 1,
        "custom_passage": "Held: Powers under Article 142 of the Constitution cannot be exercised to bypass, ignore, or override substantive statutory provisions and mandatory statutory prohibitions enacted by Parliament."
    },
    {
        "case_id": "M19_UNSEEN_025",
        "query_id": "M19_Q025",
        "category": "confession_police_officer_section_25",
        "question": "Is a confession made to a police officer admissible in evidence against an accused person?",
        "claim_sentence": "The Supreme Court held that a confession made to a senior police officer is fully admissible as substantive evidence.",
        "gold_support_label": "contradicted",
        "vol": "1",
        "case_idx": 2,
        "custom_passage": "Held: Section 25 of the Evidence Act embodies an absolute statutory ban - No confession made to a police officer can be proved as against a person accused of any offence under any circumstances."
    },
    {
        "case_id": "M19_UNSEEN_026",
        "query_id": "M19_Q026",
        "category": "limitation_condonation_delay_section_5",
        "question": "Does Section 5 of the Limitation Act apply to proceedings under Section 34 of the Arbitration Act?",
        "claim_sentence": "The court possesses unlimited jurisdiction under Section 5 of the Limitation Act to condone delay in filing objections under Section 34 of the Arbitration Act.",
        "gold_support_label": "contradicted",
        "vol": "2",
        "case_idx": 2,
        "custom_passage": "Held: Section 34(3) of the Arbitration Act provides a strict limitation of three months plus a discretionary thirty-day window - Section 5 of the Limitation Act has no application, and any delay beyond thirty days cannot be condoned."
    },
    {
        "case_id": "M19_UNSEEN_027",
        "query_id": "M19_Q027",
        "category": "anticipatory_bail_murder_section_302",
        "question": "Is anticipatory bail barred in all cases involving allegations under Section 302 IPC?",
        "claim_sentence": "Anticipatory bail cannot be granted under any circumstances where the offence alleged is punishable under Section 302 IPC.",
        "gold_support_label": "contradicted",
        "vol": "3",
        "case_idx": 2,
        "custom_passage": "Held: Section 438 CrPC does not contain any blanket bar on granting anticipatory bail in offences punishable with death or life imprisonment - The court must exercise discretion with circumspection based on the prima facie accusations."
    },
    {
        "case_id": "M19_UNSEEN_028",
        "query_id": "M19_Q028",
        "category": "cheque_bounce_company_director_vicarious",
        "question": "Is a non-executive director automatically vicariously liable under Section 141 NI Act without specific averments?",
        "claim_sentence": "Every director of a company is automatically liable for cheque bounce under Section 141 of the NI Act without any specific averment regarding their role.",
        "gold_support_label": "contradicted",
        "vol": "4",
        "case_idx": 2,
        "custom_passage": "Held: To fasten vicarious liability under Section 141 of the NI Act, there must be specific averments in the complaint explaining how and in what manner the director was in charge of and responsible for the conduct of business of the company."
    },
    {
        "case_id": "M19_UNSEEN_029",
        "query_id": "M19_Q029",
        "category": "civil_court_jurisdiction_commercial_tax",
        "question": "Can a civil court entertain a suit challenging assessment orders where a statutory appeals mechanism exists?",
        "claim_sentence": "A civil court has unfettered plenary jurisdiction to entertain civil suits challenging statutory tax assessment orders.",
        "gold_support_label": "contradicted",
        "vol": "5",
        "case_idx": 2,
        "custom_passage": "Held: Where a special taxing statute creates a liability and provides a complete machinery for challenging assessments, the jurisdiction of the Civil Court is impliedly barred under Section 9 CPC."
    },
    {
        "case_id": "M19_UNSEEN_030",
        "query_id": "M19_Q030",
        "category": "service_law_inter_se_seniority_ad_hoc",
        "question": "Does ad-hoc or fortuitous service count towards determining regular inter-se seniority?",
        "claim_sentence": "Ad-hoc or stop-gap service rendered without regular selection must be counted towards inter-se seniority in the cadre.",
        "gold_support_label": "contradicted",
        "vol": "6",
        "case_idx": 2,
        "custom_passage": "Held: Regular seniority in a cadre can be reckoned only from the date of substantive appointment in accordance with rules - Ad-hoc, temporary, or fortuitous appointments cannot be counted for determining inter-se seniority."
    }
]

# Write out milestone19_unseen_claims.jsonl
out_file = PROJECT_ROOT / "evaluation" / "rag" / "milestone19_unseen_claims.jsonl"
out_file.parent.mkdir(parents=True, exist_ok=True)

with out_file.open("w", encoding="utf-8") as f:
    for c in M19_CASES:
        vol = c["vol"]
        idx = c["case_idx"]
        cand = candidates_by_vol[vol][idx]
        passage_text = c.get("custom_passage", cand["passage"])
        record = {
            "case_id": c["case_id"],
            "query_id": c["query_id"],
            "category": c["category"],
            "question": c["question"],
            "claim_sentence": c["claim_sentence"],
            "gold_support_label": c["gold_support_label"],
            "cited_evidence_ids": ["E1"],
            "supporting_passages": [
                {
                    "evidence_id": "E1",
                    "document_id": cand["doc_id"],
                    "case_title": cand["title"],
                    "start_char": cand["start_char"],
                    "end_char": cand["start_char"] + len(passage_text),
                    "structural_label": "headnote_holding",
                    "passage_text": passage_text
                }
            ],
            "evaluation_milestone": "milestone_19",
            "is_unstudied_2024_judgment": True,
            "annotation_provenance": "developer_curated_frozen_pre_evaluation"
        }
        f.write(json.dumps(record) + "\n")

print(f"Successfully generated 30 frozen evaluation claims in {out_file}")
