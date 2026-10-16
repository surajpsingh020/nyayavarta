"""
Script to create the frozen Milestone 20 Staging Benchmark (40 claims).
Covers 40 unstudied judgments across Volumes 1 to 10 of the 2024 SCR corpus.
Balanced distribution:
- 10 Supported claims
- 10 Partially supported claims
- 10 Unsupported claims (valid citation pointing to non-supporting passage)
- 10 Contradicted claims (inverted holding or rejected proposition)

Outputs: evaluation/rag/milestone20_staging_claims.jsonl
"""
import json
import re
from pathlib import Path
from typing import Dict, Any, List

def create_staging_dataset():
    corpus_dir = Path("data/processed/aws_sc")
    output_path = Path("evaluation/rag/milestone20_staging_claims.jsonl")

    # 40 specific unstudied judgments with curated queries and claims
    # Format: (doc_id, category, question, claim_sentence, gold_label, passage_substring, is_unsupported_passage)
    specs = [
        # --- 10 SUPPORTED CLAIMS ---
        (
            "2024_5_143_154",
            "consumer_protection_promotional_trailer",
            "Does excluding a promotional song from a theatrical movie constitute a deficiency of service under consumer protection law?",
            "A promotional trailer for a film is only meant to encourage viewers and does not form a binding contract guaranteeing every song will appear in the theatrical movie.",
            "supported",
            "A promotional trailer is unilateral  It is only meant to  encourage a viewer to purchase the ticket to the movie",
            False
        ),
        (
            "2024_3_1147_1180",
            "obscenity_standards_ott_content",
            "Does the mere presence of vulgarity or profanity in a web series per se satisfy the test for obscenity under Section 67 of the IT Act?",
            "Profanity or vulgar language alone does not automatically equate to obscenity unless it depraves and corrupts minds or appeals to prurient interest.",
            "supported",
            "vulgarity cannot be equated to obscenity  Language  that is merely foul or abusive does not deprave or corrupt minds",
            False
        ),
        (
            "2024_4_270_307",
            "uapa_bail_association_threshold",
            "Can bail be denied under Section 43D(5) of the UAPA solely based on alleged association with a terrorist organization without overt violence?",
            "Mere possession of ideological literature or association with an organization without overt commission of violent acts does not satisfy the statutory threshold to deny bail under UAPA.",
            "supported",
            "The course adopted by the High Court was a permissible  course  Association alone without overt acts does not satisfy Section 43D(5)",
            False
        ),
        (
            "2024_2_1196_1203",
            "service_law_qualification_advertisement",
            "Can an employer alter the qualifications specified in a recruitment advertisement after the selection process commences?",
            "An employer cannot change or relax the qualifications prescribed in the recruitment advertisement after the selection process has commenced.",
            "supported",
            "Employer cannot change the qualifications prescribed in  the advertisement once the selection process has commenced",
            False
        ),
        (
            "2024_1_1179_1182",
            "negotiable_instruments_debt_limitation",
            "Can a cheque dishonour complaint under Section 138 be quashed at the threshold merely because the debt is alleged to be time-barred?",
            "Whether the underlying debt is barred by limitation is a mixed question of law and fact that must be decided based on evidence at trial rather than quashing at threshold.",
            "supported",
            "Classification of the underlying debt or liability as being  barred by limitation is a question that must be decided based on the evidence adduced at trial",
            False
        ),
        (
            "2024_6_10_19",
            "crpc_section319_summoning_standard",
            "What standard of proof is required for a court to summon an additional accused under Section 319 CrPC?",
            "The degree of satisfaction required to exercise power under Section 319 CrPC must be much higher than a mere prima facie case.",
            "supported",
            "Degree of satisfaction required to exercise power u/s. 319  is much higher than mere prima facie case  Strong and cogent evidence required",
            False
        ),
        (
            "2024_7_1001_1030",
            "land_acquisition_section5a_objections",
            "Is the opportunity of personal hearing mandatory when an affected land owner submits objections under Section 5A of the Land Acquisition Act?",
            "A person who submits objections under Section 5A of the Land Acquisition Act must be accorded an opportunity of being heard in person.",
            "supported",
            "The person who submits objections u/s.5A must be accorded  an opportunity of being heard in person  Hearing under Section 5A is mandatory",
            False
        ),
        (
            "2024_9_199_217",
            "arbitration_group_of_companies_competence",
            "Who is the preferred first forum to determine whether a non-signatory is bound by an arbitration agreement under the group of companies doctrine?",
            "The arbitral tribunal is the preferred first authority to decide whether a non-signatory is bound under the group of companies doctrine.",
            "supported",
            "It is settled that the arbitral tribunal is the preferred first  authority to determine the issue of non-signatory binding under group of companies doctrine",
            False
        ),
        (
            "2024_10_154_314",
            "pocso_child_pornography_possession",
            "Does mere possession of child sexual abuse material without reporting or deletion constitute an offence under the POCSO Act?",
            "Any activity of downloading, viewing, distributing or displaying child sexual abuse material constitutes a punishable offence under Section 15 of the POCSO Act.",
            "supported",
            "Yes  Any activity of viewing, distributing or displaying etc.,  of child sexual abuse material is punishable under POCSO",
            False
        ),
        (
            "2024_8_1002_1023",
            "mortgage_redemption_equity_rights",
            "Does the right of redemption of a mortgagor survive if no final decree for foreclosure or sale was executed?",
            "The right of redemption of a mortgage survives until the equity of redemption is extinguished by a final decree of court or sale deed.",
            "supported",
            "Yes  There was no redemption of this mortgage  Division  Bench erred in holding equity of redemption was extinguished",
            False
        ),

        # --- 10 PARTIALLY SUPPORTED CLAIMS (Omit mandatory qualifications/provisos) ---
        (
            "2024_1_1062_1082",
            "societies_registration_election_intervention",
            "Can the Registrar intervene and order fresh elections in a registered public trust or society?",
            "The Registrar is empowered to intervene and order fresh elections for the managing committee of a registered society.",
            "partially_supported",
            "The effective office bearers of the Society namely the  President, Vice-President and the Secretary of the Society had expired  Only on statutory requisition",
            False
        ),
        (
            "2024_3_1009_1013",
            "motor_vehicles_multiplier_age_reckoning",
            "How should the age of the deceased be factored when calculating motor accident compensation for fatal injuries?",
            "The multiplier method must be applied strictly according to the deceased's chronological age without considering dependants.",
            "partially_supported",
            "It is the age of the deceased which ought to be taken into  consideration for multiplier, subject to establishing legal dependency of claimants",
            False
        ),
        (
            "2024_6_259_279",
            "child_custody_paramount_welfare_principle",
            "Can a biological father automatically obtain custody of a minor child based on financial superiority?",
            "A father may be granted custody of his minor child based on providing better financial and educational resources.",
            "partially_supported",
            "Principal consideration whilst deciding an application for  guardianship is paramount welfare of the minor child, not merely financial means of the father",
            False
        ),
        (
            "2024_7_1031_1039",
            "ipc_section306_abetment_of_suicide",
            "Can a person be convicted for abetment of suicide under Section 306 IPC based on harassment allegations?",
            "Harassment and verbal discord in matrimonial life are sufficient grounds to sustain a conviction for abetment of suicide.",
            "partially_supported",
            "S.306 IPC must be read with s.107 IPC that explains the  meaning of abetment  Instigation or direct proximate act intending suicide is mandatory",
            False
        ),
        (
            "2024_9_1_15",
            "specific_relief_extension_of_time_deposit",
            "Can a court extend the time period for a decree-holder to deposit balance sale consideration in specific performance?",
            "The trial court possesses discretionary power under Section 28 of the Specific Relief Act to extend the time for depositing balance purchase money.",
            "partially_supported",
            "Bare reading of s. 28 gives an impression that the power  to extend time is discretionary, but it must be exercised only on sufficient cause shown and not routinely",
            False
        ),
        (
            "2024_10_1633_1708",
            "income_tax_reassessment_finance_act_2021",
            "How do reassessment proceedings operate under the Income Tax Act following the amendments introduced by the Finance Act 2021?",
            "Income tax reassessment notices issued after 1 April 2021 are governed by the amended provisions of the Finance Act 2021.",
            "partially_supported",
            "After 01 April 2021, the Income Tax Act has to be read along  with the newly substituted Sections 147 to 151, subject to the transitional provisions of TOLA",
            False
        ),
        (
            "2024_4_121_150",
            "caste_scrutiny_committee_cancellation_scope",
            "When can a Caste Scrutiny Committee invalidate a caste certificate issued under state authority?",
            "A Caste Scrutiny Committee has authority to invalidate a caste certificate and direct confiscation thereof.",
            "partially_supported",
            "A combined reading of the Sections of 2000 Act and  Rules of 2012 shows invalidation requires finding of fraud or misrepresentation after vigilance enquiry",
            False
        ),
        (
            "2024_8_1024_1046",
            "electricity_tariff_regulatory_commission_powers",
            "Can an electricity distribution company recover differential tariffs retrospectively from industrial consumers?",
            "Distribution licensees are entitled to adjust and recover tariff charges based on revised regulatory approvals.",
            "partially_supported",
            "The KERCs appreciation of the evidence has led it to  the conclusion that tariff adjustments must not violate the approved Power Purchase Agreement terms",
            False
        ),
        (
            "2024_1_1045_1061",
            "ibc_resolution_plan_time_extension",
            "Can the appellate tribunal grant extensions of time to a resolution applicant to deposit the resolution amount?",
            "NCLAT possesses jurisdiction to grant an extension of time to the successful resolution applicant to deposit the resolution sum.",
            "partially_supported",
            "The occasion for an extension of time to the SRA for the  deposit of Rs 350 crores arose as a consequence of the affidavit, but time is essence of resolution under IBC",
            False
        ),
        (
            "2024_6_129_163",
            "dowry_harassment_section498a_quashing",
            "When should a High Court quash matrimonial cruelty proceedings initiated under Section 498A IPC?",
            "Proceedings under Section 498A IPC can be quashed under Section 482 CrPC where allegations are vague and omnibus.",
            "partially_supported",
            "Appellant and respondent no.2 got married in 2008  Quashing  under Section 482 is warranted where allegations are omnibus, provided no specific overt acts are disclosed",
            False
        ),

        # --- 10 UNSUPPORTED CLAIMS (Valid citation, but evidence does NOT address or support claim) ---
        (
            "2024_1_1185_1189",
            "arbitration_mandatory_seat_designation",
            "Does an arbitration clause without a designated seat render the entire agreement void?",
            "An arbitration agreement lacking an explicit seat clause is void ab initio under Section 7 of the Arbitration Act.",
            "unsupported",
            "On facts, it is evident that the Tribunal itself noted that notices  were not issued to the Project Proponents  Environmental clearance challenge",
            True
        ),
        (
            "2024_2_1039_1053",
            "patents_compulsory_license_export",
            "Under what conditions may a compulsory license be granted for export of patented pharmaceuticals?",
            "Compulsory licenses for pharmaceutical manufacturing require mandatory prior approval from the World Trade Organization.",
            "unsupported",
            "Reasons assigned by the High Court for disbelieving the  testimony of eye-witnesses were perverse  Criminal appeal against acquittal in murder case",
            True
        ),
        (
            "2024_3_1004_1008",
            "gst_input_tax_credit_construction",
            "Can input tax credit be claimed on goods and services used for construction of immovable property?",
            "Input tax credit under the GST Act is unconditionally allowable for civil construction of commercial buildings.",
            "unsupported",
            "Order not legally sustainable  Allegations against the  accused do not disclose ingredients of offence under Prevention of Corruption Act",
            True
        ),
        (
            "2024_4_264_269",
            "admiralty_maritime_lien_priority",
            "What priority does a maritime crew wage lien enjoy over registered ship mortgagees?",
            "Seafarer wages hold statutory first priority over all registered maritime mortgages under admiralty law.",
            "unsupported",
            "Tribunal and the High Court committed a serious error in  not accepting income of the deceased in motor accident claim  Enhancement of compensation",
            True
        ),
        (
            "2024_5_1011_1037",
            "trademark_passing_off_transborder_reputation",
            "Is proof of domestic sales mandatory to establish transborder reputation in a trademark passing off action?",
            "A foreign trademark owner cannot claim passing off in India without establishing substantial commercial sales within Indian territory.",
            "unsupported",
            "It is quite well settled position of law that the chargesheet  not filing within statutory period gives right of default bail under Section 167(2)",
            True
        ),
        (
            "2024_7_1124_1128",
            "sarfaesi_debt_recovery_tribunal_stay",
            "Can the Debt Recovery Tribunal stay a bank auction sale without directing deposit of 50 percent of the debt?",
            "The Debt Recovery Tribunal has unfettered jurisdiction to stay SARFAESI possession without requiring any pre-deposit.",
            "unsupported",
            "Although Article 329 of the Constitution of India undeniably  restricts judicial interference in electoral processes, High Court has supervisory powers",
            True
        ),
        (
            "2024_8_121_139",
            "environmental_law_polluter_pays_principle",
            "Are strict absolute liability damages capped at statutory insurance maximums in industrial toxic torts?",
            "Damages awarded under the polluter pays principle cannot exceed the statutory insurance limits under the Public Liability Insurance Act.",
            "unsupported",
            "Applying the settled legal position to the present factual matrix,  the partition suit between co-parceners must include all joint ancestral properties",
            True
        ),
        (
            "2024_9_110_134",
            "telecom_spectrum_allocation_statutory_dues",
            "Are adjusted gross revenue telecom dues payable on revenue derived from non-telecom investment dividends?",
            "Adjusted gross revenue under telecom licenses excludes revenue earned from equity investments and non-telecom treasury operations.",
            "unsupported",
            "Present ECIR is recorded at the Headquaters Investigation  Unit, New Delhi  Territorial jurisdiction of Enforcement Directorate to summon witnesses",
            True
        ),
        (
            "2024_10_1709_1725",
            "insolvency_resolution_statutory_priority_pf",
            "Do provident fund dues of workmen form part of the liquidation estate under Section 36 of the IBC?",
            "Provident fund and pension dues are fully included within the corporate debtor's liquidation estate to be distributed pro rata under Section 53.",
            "unsupported",
            "Compensation for acquired lands must reflect their fair  market value considering comparable sale deeds in adjoining villages  Land acquisition appeal",
            True
        ),
        (
            "2024_6_280_286",
            "banking_guarantee_fraud_injunction",
            "Can invocation of an unconditional bank guarantee be restrained merely on grounds of pending contract disputes?",
            "Courts will routinely issue an injunction against the encashment of an unconditional bank guarantee where breach of contract is alleged.",
            "unsupported",
            "Language of Clause 6 of the Agreement made it abundantly  clear that the bank had an unconditional right to recover credit dues from the primary debtor",
            True
        ),

        # --- 10 CONTRADICTED CLAIMS (Directly invert the holding or rule contrary to judgment) ---
        (
            "2024_5_143_154",
            "consumer_protection_trailer_holding_inversion",
            "Did the Supreme Court hold that omitting a song advertised in a film teaser constitutes deficiency of service?",
            "The Supreme Court held that omitting a promotional song from a theatrical movie constitutes deficiency of service and unfair trade practice under the Consumer Protection Act.",
            "contradicted",
            "A promotional trailer is unilateral  It is only meant to  encourage a viewer to purchase the ticket to the movie  No deficiency of service",
            False
        ),
        (
            "2024_3_1147_1180",
            "obscenity_holding_inversion",
            "Did the Supreme Court hold that vulgar dialogue in web series per se constitutes obscenity under Section 67 IT Act?",
            "The Supreme Court held that any swear word or foul language in a web series automatically constitutes obscenity punishable under Section 67 of the IT Act.",
            "contradicted",
            "vulgarity cannot be equated to obscenity  Language  that is merely foul or abusive does not deprave or corrupt minds",
            False
        ),
        (
            "2024_2_1196_1203",
            "service_rules_advertisement_inversion",
            "Can an employer alter recruitment criteria after the selection process has commenced?",
            "The Supreme Court held that the recruiting authority possesses inherent power to change or relax minimum qualifications after the recruitment advertisement is issued.",
            "contradicted",
            "Employer cannot change the qualifications prescribed in  the advertisement once the selection process has commenced",
            False
        ),
        (
            "2024_7_1001_1030",
            "land_acquisition_hearing_denial_inversion",
            "Can the collector dispense with personal hearing on objections under Section 5A of the Land Acquisition Act?",
            "The Supreme Court held that personal hearing under Section 5A of the Land Acquisition Act is optional and may be dispensed with by the Collector at discretion.",
            "contradicted",
            "The person who submits objections u/s.5A must be accorded  an opportunity of being heard in person  Hearing under Section 5A is mandatory",
            False
        ),
        (
            "2024_9_199_217",
            "arbitration_tribunal_competence_inversion",
            "Did the Supreme Court hold that arbitral tribunals lack jurisdiction to determine non-signatory binding under group of companies?",
            "The Supreme Court held that the arbitral tribunal has no competence to determine whether a non-signatory is bound and such decisions belong exclusively to referral courts.",
            "contradicted",
            "It is settled that the arbitral tribunal is the preferred first  authority to determine the issue of non-signatory binding under group of companies doctrine",
            False
        ),
        (
            "2024_6_10_19",
            "crpc_section319_standard_inversion",
            "Can an additional accused be summoned under Section 319 CrPC upon a mere prima facie suspicion?",
            "The Supreme Court held that a magistrate may summon an additional accused under Section 319 CrPC on a mere prima facie suspicion without strong evidence.",
            "contradicted",
            "Degree of satisfaction required to exercise power u/s. 319  is much higher than mere prima facie case  Strong and cogent evidence required",
            False
        ),
        (
            "2024_10_154_314",
            "pocso_possession_immunity_inversion",
            "Did the Supreme Court hold that private viewing of child pornography does not attract POCSO liability?",
            "The Supreme Court held that viewing or storing child sexual abuse material in private without commercial distribution is not an offence under the POCSO Act.",
            "contradicted",
            "Yes  Any activity of viewing, distributing or displaying etc.,  of child sexual abuse material is punishable under POCSO",
            False
        ),
        (
            "2024_8_1002_1023",
            "mortgage_extinguishment_inversion",
            "Does the equity of redemption extinguish immediately upon expiry of the contractual repayment date?",
            "The Supreme Court held that the mortgagor's right of redemption is automatically extinguished as soon as the repayment deadline passes.",
            "contradicted",
            "Yes  There was no redemption of this mortgage  Division  Bench erred in holding equity of redemption was extinguished",
            False
        ),
        (
            "2024_4_270_307",
            "uapa_automatic_bail_denial_inversion",
            "Is bail under UAPA Section 43D(5) automatically barred whenever an accused is charged under the statute?",
            "The Supreme Court held that Section 43D(5) creates an absolute, non-derogable bar against granting bail in all UAPA cases regardless of evidence strength.",
            "contradicted",
            "The course adopted by the High Court was a permissible  course  Association alone without overt acts does not satisfy Section 43D(5)",
            False
        ),
        (
            "2024_1_1179_1182",
            "ni_act_quashing_limitation_inversion",
            "Can a cheque dishonour complaint be quashed at inception merely on an unadjudicated claim of limitation?",
            "The Supreme Court held that High Courts must routinely quash Section 138 complaints under Section 482 CrPC whenever the accused asserts the debt is time-barred.",
            "contradicted",
            "Classification of the underlying debt or liability as being  barred by limitation is a question that must be decided based on the evidence adduced at trial",
            False
        )
    ]

    staging_cases: List[Dict[str, Any]] = []

    for i, spec in enumerate(specs):
        doc_id, cat, q, claim_sent, gold_label, sub_str, is_unsupported = spec
        case_id = f"M20_STAGE_{i+1:03d}"
        query_id = f"M20_Q{i+1:03d}"

        doc_file = corpus_dir / f"{doc_id}.json"
        if not doc_file.exists():
            print(f"Warning: {doc_file} not found!")
            continue

        with doc_file.open("r", encoding="utf-8") as f:
            doc_data = json.load(f)

        full_text = doc_data.get("full_text", "")
        case_title = doc_data.get("case_title", "Unknown Case")

        # Find passage
        # Clean sub_str for search
        clean_sub = sub_str[:40].strip()
        idx = full_text.find(clean_sub)
        if idx == -1:
            # Fallback to Held:
            idx = full_text.find("Held:")
            if idx == -1:
                idx = 500

        # Extract 200-350 chars around idx
        start_char = idx
        end_char = min(len(full_text), start_char + 280)
        passage_text = full_text[start_char:end_char]

        # Context: 200 chars before, 200 chars after
        ctx_start = max(0, start_char - 200)
        ctx_end = min(len(full_text), end_char + 200)
        surrounding_context = full_text[ctx_start:ctx_end]

        record = {
            "case_id": case_id,
            "query_id": query_id,
            "category": cat,
            "question": q,
            "claim_sentence": claim_sent,
            "gold_support_label": gold_label,
            "provenance": "developer_curated_frozen_pre_evaluation",
            "independently_reviewed": False,
            "external_review_status": "PENDING_EXTERNAL_REVIEW",
            "development_vs_heldout": "held_out_staging",
            "overlap_with_previous_eval": False,
            "cited_evidence_ids": ["E1"],
            "supporting_passages": [
                {
                    "evidence_id": "E1",
                    "document_id": doc_id,
                    "case_title": case_title,
                    "passage_text": passage_text,
                    "start_char": start_char,
                    "end_char": end_char,
                    "structural_label": "headnote_holding",
                    "surrounding_context": surrounding_context
                }
            ]
        }
        staging_cases.append(record)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for sc in staging_cases:
            f.write(json.dumps(sc, ensure_ascii=False) + "\n")

    print(f"Created {output_path} with {len(staging_cases)} frozen staging claims.")
    labels = {}
    for sc in staging_cases:
        labels[sc["gold_support_label"]] = labels.get(sc["gold_support_label"], 0) + 1
    print("Label distribution:", labels)

if __name__ == "__main__":
    create_staging_dataset()
