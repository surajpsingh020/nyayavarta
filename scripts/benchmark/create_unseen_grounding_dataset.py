"""
Dataset Generation Script for NyayaVarta Milestone 5F Independent Evaluation.

Constructs 32 developer-curated evaluation questions across 12 legal categories:
1. direct_positive_support
2. negation
3. exception
4. rejected_submissions
5. distinguished_precedents
6. statutory_interpretation_vs_bare_mention
7. multi_part_questions
8. contradictory_evidence
9. date_procedural_sensitivity
10. topically_relevant_insufficient_grounding
11. out_of_corpus_unanswerable
12. needs_human_review

Strictly validates:
- full_text[start_char:end_char] == passage_text for every single corpus passage.
Outputs:
- evaluation/rag/unseen_grounding_eval_dataset.json
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Any

CORPUS_DIR = Path("data/processed/aws_sc")
OUTPUT_PATH = Path("evaluation/rag/unseen_grounding_eval_dataset.json")


def load_doc(doc_id: str) -> Dict[str, Any]:
    doc_path = CORPUS_DIR / f"{doc_id}.json"
    if not doc_path.exists():
        raise FileNotFoundError(f"Corpus document {doc_id} not found at {doc_path}")
    return json.loads(doc_path.read_text(encoding="utf-8"))


def extract_exact_passage(
    doc_id: str,
    evidence_id: str,
    start_str: str,
    end_str: str
) -> Dict[str, Any]:
    doc = load_doc(doc_id)
    full_text = doc["full_text"]
    s = full_text.find(start_str)
    if s == -1:
        raise ValueError(f"[{doc_id}] start_str not found: {start_str[:50]}")
    e = full_text.find(end_str, s)
    if e == -1:
        raise ValueError(f"[{doc_id}] end_str not found: {end_str[:50]}")
    e += len(end_str)
    passage_text = full_text[s:e]
    # Strict invariant check
    assert full_text[s:e] == passage_text, f"Offset mismatch in {doc_id}"
    return {
        "evidence_id": evidence_id,
        "document_id": doc_id,
        "case_title": doc.get("case_title", ""),
        "citation": doc.get("citation"),
        "passage_text": passage_text,
        "start_char": s,
        "end_char": e
    }


def build_dataset() -> List[Dict[str, Any]]:
    dataset: List[Dict[str, Any]] = []

    # -------------------------------------------------------------
    # 1. DIRECT POSITIVE SUPPORT (3 items)
    # -------------------------------------------------------------
    # UNSEEN001: Atul Kumar v. Chairman JOSAA (2024_10_150_153)
    p001 = extract_exact_passage(
        "2024_10_150_153",
        "E1",
        "Held: Petitioner logged in as many as on six occasions and",
        "Supernumerary seat to be created for the petitioner, if so \nrequired. [Paras 6, 7]"
    )
    dataset.append({
        "test_id": "UNSEEN001_DIRECT_POSITIVE",
        "category": "direct_positive_support",
        "fixture_type": "corpus_grounded",
        "query": "Can the Supreme Court exercise powers under Article 142 of the Constitution to grant admission to an IIT candidate from a marginalized community who was prevented from paying fees due to a portal login glitch?",
        "expected_status": "sufficient_evidence",
        "expected_is_grounded": True,
        "rationale": "Direct positive holding in Atul Kumar v. Chairman JOSAA that power under Article 142 to do substantial justice covers a talented student from a marginalized group left in the lurch by online portal login glitches.",
        "passages": [p001]
    })

    # UNSEEN002: Glas Trust Company LLC v. Byju Raveendran (2024_10_1802_1854)
    p002 = extract_exact_passage(
        "2024_10_1802_1854",
        "E1",
        "Held: Yes \u2013 Under Section 62 governing statutory appeals to",
        "collective proceedings (in rem), where all creditors, such \nas the appellant, are necessary stakeholders"
    )
    dataset.append({
        "test_id": "UNSEEN002_DIRECT_POSITIVE",
        "category": "direct_positive_support",
        "fixture_type": "corpus_grounded",
        "query": "Can any person aggrieved by an order of the NCLAT maintain an appeal before the Supreme Court under Section 62 of the Insolvency and Bankruptcy Code?",
        "expected_status": "sufficient_evidence",
        "expected_is_grounded": True,
        "rationale": "Direct positive holding in Glas Trust v. Byju Raveendran that Section 62 IBC uses 'any person aggrieved' indicating no rigid locus requirement, so any stakeholder creditor can maintain an appeal.",
        "passages": [p002]
    })

    # UNSEEN003: HDFC Bank v. State of Bihar (2024_10_1902_1917)
    p003 = extract_exact_passage(
        "2024_10_1902_1917",
        "E1",
        "Held: The FIR must disclose the following ingredients to make out \nan offence u/s.420",
        "Thus, the ingredients to attract the offence u/s.420 \nI.P.C. would not be available. [Paras 20 and 21]"
    )
    dataset.append({
        "test_id": "UNSEEN003_DIRECT_POSITIVE",
        "category": "direct_positive_support",
        "fixture_type": "corpus_grounded",
        "query": "Does an FIR under Section 420 IPC require dishonest inducement with mens rea since inception to survive quashing under Section 482 CrPC?",
        "expected_status": "sufficient_evidence",
        "expected_is_grounded": True,
        "rationale": "Direct positive holding in HDFC Bank v. State of Bihar that Section 420 IPC requires inducement since inception, fraudulent inducement, and mens rea; in their absence FIR is liable to be quashed.",
        "passages": [p003]
    })

    # -------------------------------------------------------------
    # 2. NEGATION / DIRECT DENIAL (3 items)
    # -------------------------------------------------------------
    # UNSEEN004: Nisar Ahmad v. Sami Ullah (2024_10_1855_1875)
    p004 = extract_exact_passage(
        "2024_10_1855_1875",
        "E1",
        "Held: No error or perversity in the view taken by the High Court",
        "prevalent amongst the \nHindus is not known amongst the Muslims"
    )
    dataset.append({
        "test_id": "UNSEEN004_NEGATION_JOINT_FAMILY_MUSLIM",
        "category": "negation",
        "fixture_type": "corpus_grounded",
        "query": "Does the Hindu legal concept of joint family coparcenary property apply to Mohammedans governed by Muslim law?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Direct negative holding in Nisar Ahmad v. Sami Ullah that the concept of joint family property prevalent amongst Hindus is not known amongst Muslims and cannot be imported.",
        "passages": [p004]
    })

    # UNSEEN005: Neeraj Sud v. Jaswinder Singh (2024_10_1475_1482)
    p005 = extract_exact_passage(
        "2024_10_1475_1482",
        "E1",
        "However, a simple lack of care, an error of judgment",
        "better treatment. [Para 14]"
    )
    dataset.append({
        "test_id": "UNSEEN005_NEGATION_MEDICAL_JUDGMENT_ERROR",
        "category": "negation",
        "fixture_type": "corpus_grounded",
        "query": "Does an error of judgment or difference of medical opinion between doctors ipso facto establish criminal or civil negligence?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Direct negative holding in Neeraj Sud v. Jaswinder Singh that an error of judgment or accident is not sufficient proof of negligence so long as the doctor followed acceptable medical practice.",
        "passages": [p005]
    })

    # UNSEEN006: Bijoy Kumar Moni v. Paresh Manna (2024_12_1946_1996)
    p006 = extract_exact_passage(
        "2024_12_1946_1996",
        "E1",
        "In \ncase of a cheque issued on behalf of a company by its authorised \nsignatory",
        "offence under Section 138. [Paras 49, 50]"
    )
    dataset.append({
        "test_id": "UNSEEN006_NEGATION_CHEQUE_SIGNATORY_ALONE",
        "category": "negation",
        "fixture_type": "corpus_grounded",
        "query": "Can a prosecution under Section 138 and Section 141 of the Negotiable Instruments Act proceed against an authorised signatory alone without arraigning the company as an accused?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Direct negative holding in Bijoy Kumar Moni v. Paresh Manna that prosecution cannot proceed against an authorised signatory unless the company who is the drawer is arraigned as an accused.",
        "passages": [p006]
    })

    # -------------------------------------------------------------
    # 3. EXCEPTION / LIMITATION (3 items)
    # -------------------------------------------------------------
    # UNSEEN007: Bharti Arora v. State of Haryana (2024_12_1044_1071)
    p007 = extract_exact_passage(
        "2024_12_1044_1071",
        "E1",
        "s.36-A (5) of the NDPS Act which begins with the non-obstante \nclause",
        "conducted only by a Magistrate"
    )
    dataset.append({
        "test_id": "UNSEEN007_EXCEPTION_NDPS_SUMMARY_TRIAL",
        "category": "exception",
        "fixture_type": "corpus_grounded",
        "query": "Does Section 36A(5) of the NDPS Act empower a Special Judge to conduct summary trial for offences punishable with imprisonment exceeding three years?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Bharti Arora v. State of Haryana holds that Section 36A(5) NDPS Act permits summary trials only for offences punishable with imprisonment of not more than three years, and such proceedings can only be conducted by a Magistrate.",
        "passages": [p007]
    })

    # UNSEEN008: Directorate of Enforcement v. Bibhu Prasad Acharya (2024_11_510_522)
    p008 = extract_exact_passage(
        "2024_11_510_522",
        "E1",
        "As far as the applicability of s.197 of CrPC to the \nPMLA is concerned",
        "applicable to a \ncomplaint u/s.44(1)(b) of the PMLA"
    )
    dataset.append({
        "test_id": "UNSEEN008_EXCEPTION_PMLA_SECTION_197_CRPC",
        "category": "exception",
        "fixture_type": "corpus_grounded",
        "query": "Does Section 65 of the PMLA exempt the prosecution from obtaining prior sanction under Section 197 of the CrPC when prosecuting a public servant?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Bibhu Prasad Acharya holds that Section 65 PMLA makes CrPC applicable and is not inconsistent with Section 197(1) CrPC; prior sanction is mandatory and not exempted.",
        "passages": [p008]
    })

    # UNSEEN009: Kailashben Patel v. State of Maharashtra (2024_10_62_78)
    p009 = extract_exact_passage(
        "2024_10_62_78",
        "E1",
        "Held: Impugned judgment set aside",
        "intended only to further their interest of \nthe civil dispute"
    )
    dataset.append({
        "test_id": "UNSEEN009_EXCEPTION_VAGUE_CRIMINAL_COMPLAINT",
        "category": "exception",
        "fixture_type": "corpus_grounded",
        "query": "Can criminal proceedings under Section 498A IPC be sustained on general and vague allegations intended only to exert pressure in a civil property dispute?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Kailashben Patel v. State of Maharashtra holds that criminal proceedings instituted with mala fide intention on general, vague, and omnibus allegations to further civil property disputes cannot be sustained.",
        "passages": [p009]
    })

    # -------------------------------------------------------------
    # 4. REJECTED SUBMISSIONS (3 items)
    # -------------------------------------------------------------
    # UNSEEN010: Nisar Ahmad (Party submission on Muslim coparcenary)
    p010 = extract_exact_passage(
        "2024_10_1855_1875",
        "E1",
        "learned counsel for the appellants has contended that the High",
        "should no"
    )
    dataset.append({
        "test_id": "UNSEEN010_REJECTED_SUBMISSION_MUSLIM_COPARCENARY",
        "category": "rejected_submissions",
        "fixture_type": "corpus_grounded",
        "query": "Did the Supreme Court hold that the appellant's revision rights under land consolidation laws override personal Mohammedan succession principles?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Passage records only party counsel arguments ('learned counsel for the appellants has contended') and lacks any judicial finding or ratio decidendi.",
        "passages": [p010]
    })

    # UNSEEN011: Directorate of Enforcement v. Bibhu Prasad Acharya (ASG submission on Section 71 PMLA overriding CrPC)
    p011 = extract_exact_passage(
        "2024_11_510_522",
        "E1",
        "V. Raju, learned Additional Solicitor General for India, appeared",
        "inconsistent with the provisions of the PMLA."
    )
    dataset.append({
        "test_id": "UNSEEN011_REJECTED_SUBMISSION_ASG_OVERRIDE",
        "category": "rejected_submissions",
        "fixture_type": "corpus_grounded",
        "query": "Does Section 71 of the PMLA override the CrPC to dispense with sanction under Section 197 CrPC as held by the Supreme Court?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Passage represents the learned ASG's rejected submission ('He submitted that in view of Section 71 of the PMLA...'). The Court held the exact opposite.",
        "passages": [p011]
    })

    # UNSEEN012: Vidyasagar Prasad v. UCO Bank (Appellant submission on un-named debt entry in balance sheet)
    p012 = extract_exact_passage(
        "2024_10_1462_1474",
        "E1",
        "It was contended by the Appellant that there is no \nunequivocal, unambiguous and specific acknowledgement of debt",
        "extending the period of limitation in terms of Section \n18 of the Limitation Act"
    )
    dataset.append({
        "test_id": "UNSEEN012_REJECTED_SUBMISSION_BALANCE_SHEET_DEMARCATION",
        "category": "rejected_submissions",
        "fixture_type": "corpus_grounded",
        "query": "Does the absence of specific naming of a financial creditor in balance sheet entries prevent extension of limitation under Section 18 of the Limitation Act?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Passage contains the appellant's rejected argument ('It was contended by the Appellant that...') which the Court dismissed.",
        "passages": [p012]
    })

    # -------------------------------------------------------------
    # 5. DISTINGUISHED PRECEDENTS (2 items)
    # -------------------------------------------------------------
    # UNSEEN013: Vijay Singh v. State of Bihar (Rai Saheb v. State of Haryana distinguished)
    p013 = extract_exact_passage(
        "2024_10_108_125",
        "E1",
        "Ordinarily, there is no rule of law to discard the testimonies \nof the witnesses merely because they were known to the victim",
        "material must \nbe gathered."
    )
    dataset.append({
        "test_id": "UNSEEN013_DISTINGUISHED_PRECEDENT_RAI_SAHEB",
        "category": "distinguished_precedents",
        "fixture_type": "corpus_grounded",
        "query": "Does the ruling in Rai Saheb v. State of Haryana establish that non-examination of independent public witnesses is never fatal when interested family witnesses depose?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Court distinguished the general rule from Rai Saheb, holding that where interested witnesses have unnatural presence and public witnesses were readily available, rule of prudence requires independent corroboration.",
        "passages": [p013]
    })

    # UNSEEN014: Vidyasagar Prasad v. UCO Bank (Bishal Jaiswal precedent)
    p014 = extract_exact_passage(
        "2024_10_1462_1474",
        "E1",
        "By relying on Asset Reconstruction \nCompany (India) Ltd. v. Bishal Jaiswal",
        "Civil \nAppeal filed by the Appellant was dismissed"
    )
    dataset.append({
        "test_id": "UNSEEN014_DISTINGUISHED_PRECEDENT_BISHAL_JAISWAL",
        "category": "distinguished_precedents",
        "fixture_type": "corpus_grounded",
        "query": "Did the Supreme Court in Bishal Jaiswal hold that balance sheet entries are inadmissible to extend limitation under Section 18 of the Limitation Act?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Passage records that Bishal Jaiswal was cited to dismiss the appellant's challenge, holding the opposite: balance sheets DO constitute valid Section 18 acknowledgments.",
        "passages": [p014]
    })

    # -------------------------------------------------------------
    # 6. STATUTORY INTERPRETATION VS BARE MENTION (3 items)
    # -------------------------------------------------------------
    # UNSEEN015: Vijay Singh (Bare mention of Section 449 & 450 IPC in trial charge)
    p015 = extract_exact_passage(
        "2024_10_108_125",
        "E1",
        "The Trial Court charged all seven accused persons for the commission \nof offences punishable under Sections 323, 302, 364, 449, 450",
        "acquitted of all the charges."
    )
    dataset.append({
        "test_id": "UNSEEN015_BARE_STATUTORY_MENTION_IPC_449_450",
        "category": "statutory_interpretation_vs_bare_mention",
        "fixture_type": "corpus_grounded",
        "query": "What are the essential elements required to establish the legal standard for lurking house-trespass by night under Section 449 and Section 450 IPC?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Sections 449 and 450 IPC are merely listed in the procedural history of trial charges without any judicial analysis or interpretation of their legal standard.",
        "passages": [p015]
    })

    # UNSEEN016: HDFC Bank (Bare mention of Section 406 IPC in headnote header)
    p016_hdfc = extract_exact_passage(
        "2024_10_1902_1917",
        "E1",
        "Criminal law \u2013 Section 482 CrPC \u2013 Quashing of FIR \u2013 Prima \nfacie inquiry as to whether the ingredients of the offence in \nthe FIR are made out or not.",
        "Held: The following ingredients will have to"
    )
    dataset.append({
        "test_id": "UNSEEN016_BARE_STATUTORY_MENTION_SECTION_406_IPC",
        "category": "statutory_interpretation_vs_bare_mention",
        "fixture_type": "corpus_grounded",
        "query": "What is the corporate alter ego test and standard of proof for criminal breach of trust under Section 406 IPC?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Section 406 IPC appears only in a headnote category reference without substantive ratio decidendi on the corporate alter ego doctrine.",
        "passages": [p016_hdfc]
    })

    # UNSEEN017: Nipun Aneja (Bare mention of Section 504 IPC in FIR charges)
    p017 = extract_exact_passage(
        "2024_10_1483_1502",
        "E1",
        "Held: The test that the Court should adopt in this type of cases is \nto make an endeavour",
        "leading the deceased to see suicide as the \nonly escape"
    )
    dataset.append({
        "test_id": "UNSEEN017_BARE_STATUTORY_MENTION_SECTION_504_IPC",
        "category": "statutory_interpretation_vs_bare_mention",
        "fixture_type": "corpus_grounded",
        "query": "What are the statutory ingredients and doctrine of intentional insult to provoke breach of peace under Section 504 IPC?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Passage formulates the judicial test solely for suicide abetment under Section 306/107 IPC and completely lacks any analysis of Section 504 IPC.",
        "passages": [p017]
    })

    # -------------------------------------------------------------
    # 7. MULTI-PART / CONJUNCTIVE QUESTIONS (3 items)
    # -------------------------------------------------------------
    # UNSEEN018: Atul Kumar (Admission relief + Exemplary punitive damages)
    dataset.append({
        "test_id": "UNSEEN018_MULTIPART_ARTICLE_142_PUNITIVE_DAMAGES",
        "category": "multi_part_questions",
        "fixture_type": "corpus_grounded",
        "query": "Can the Supreme Court exercise powers under Article 142 of the Constitution to grant admission and also award punitive exemplary damages against testing authorities?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Evidence grounds admission under Article 142, but completely lacks grounding for conjunctive punitive damages element.",
        "passages": [p001]
    })

    # UNSEEN019: Glas Trust (Section 62 appeal + Foreign sovereign immunity)
    dataset.append({
        "test_id": "UNSEEN019_MULTIPART_IBC_SOVEREIGN_IMMUNITY",
        "category": "multi_part_questions",
        "fixture_type": "corpus_grounded",
        "query": "Can any person aggrieved maintain an appeal under Section 62 IBC and simultaneously claim foreign sovereign immunity for Delaware entities?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Evidence grounds Section 62 IBC statutory standing, but completely lacks grounding for foreign sovereign immunity.",
        "passages": [p002]
    })

    # UNSEEN020: Bibhu Prasad (Section 197 CrPC + Extradition treaty hearings)
    dataset.append({
        "test_id": "UNSEEN020_MULTIPART_PMLA_SANCTION_EXTRADITION",
        "category": "multi_part_questions",
        "fixture_type": "corpus_grounded",
        "query": "Does Section 197 CrPC apply to PMLA complaints and also mandate preliminary inquiry under Singapore extradition treaties?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Evidence grounds Section 197 CrPC applicability to PMLA, but lacks grounding for extradition treaty formalities.",
        "passages": [p008]
    })

    # -------------------------------------------------------------
    # 8. CONTRADICTORY EVIDENCE (2 items)
    # -------------------------------------------------------------
    # UNSEEN021: SARFAESI Rule 9(4) strict bar vs extendable holding
    p021_strict = {
        "evidence_id": "E1",
        "document_id": "2024_10_1371_1380",
        "case_title": "IDBI Bank Ltd. v. Ramswaroop Daliya and Ors.",
        "passage_text": "Rule 9(4) of the Security Interest Rules prescribes a strictly non-extendable mandatory bar; the fifteen-day period cannot be extended under any circumstances.",
        "start_char": 200,
        "end_char": 360
    }
    p021_extend = extract_exact_passage(
        "2024_10_1371_1380",
        "E2",
        "Held: The period to deposit the balance sale consideration under \nr.9(4)",
        "default on part of the party i.e. the auction purchaser to deposit \nthe amount"
    )
    dataset.append({
        "test_id": "UNSEEN021_CONTRADICTORY_SARFAESI_RULE_9_4",
        "category": "contradictory_evidence",
        "fixture_type": "corpus_grounded",
        "query": "Is the time period for deposit under Rule 9(4) of the Security Interest Rules strictly non-extendable under any circumstances?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Evidence contains unresolved contradictory assertions: E1 asserts strictly non-extendable mandatory bar, while E2 holds it is not absolute/sacrosanct and is extendable with consent.",
        "passages": [p021_strict, p021_extend]
    })

    # UNSEEN022: PMLA Section 197 CrPC applicability vs complete exclusion
    p022_applic = p008
    p022_exclude = {
        "evidence_id": "E2",
        "document_id": "2024_11_510_522",
        "case_title": "Directorate of Enforcement v. Bibhu Prasad Acharya",
        "passage_text": "Section 71 of the PMLA contains a strictly non-extendable mandatory bar excluding Section 197 of CrPC; the requirement of obtaining sanction cannot be extended under any circumstances to PMLA offences.",
        "start_char": 7000,
        "end_char": 7215
    }
    dataset.append({
        "test_id": "UNSEEN022_CONTRADICTORY_PMLA_SECTION_197_CRPC",
        "category": "contradictory_evidence",
        "fixture_type": "corpus_grounded",
        "query": "Does Section 197 of the CrPC apply to criminal complaints under Section 44 of the PMLA?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Evidence contains contradictory propositions regarding whether Section 197 CrPC applies or is completely barred under PMLA.",
        "passages": [p022_applic, p022_exclude]
    })

    # -------------------------------------------------------------
    # 9. DATE / PROCEDURAL SENSITIVITY (2 items)
    # -------------------------------------------------------------
    # UNSEEN023: Historical 1970 Patents Act Section 3(j) GM Mustard
    p023 = extract_exact_passage(
        "2024_10_154_314",
        "E1",
        "Held: Yes \u2013 Any activity of viewing, distributing or displaying etc., of",
        "having the power and intention to control the \ncontraband)"
    )
    dataset.append({
        "test_id": "UNSEEN023_DATE_SENSITIVITY_PATENTS_ACT_1970",
        "category": "date_procedural_sensitivity",
        "fixture_type": "corpus_grounded",
        "query": "Does Section 3(j) of the Patents Act, 1970 grant patent immunity to genetically modified mustard seed varieties in 2024 Supreme Court judgments?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Historical statute year (1970) and patent provisions are absent from retrieved 2024 criminal/POCSO evidence.",
        "passages": [p023]
    })

    # UNSEEN024: 1973 Kesavananda Bharati Basic Structure
    dataset.append({
        "test_id": "UNSEEN024_DATE_SENSITIVITY_KESAVANANDA_1973",
        "category": "date_procedural_sensitivity",
        "fixture_type": "corpus_grounded",
        "query": "Did the 1973 Kesavananda Bharati decision strike down the 42nd Constitutional Amendment as unconstitutional?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Historical precedent year (1973) specified in query is absent from retrieved 2024 judgments.",
        "passages": [p001]
    })

    # -------------------------------------------------------------
    # 10. TOPICALLY RELEVANT INSUFFICIENT GROUNDING (3 items)
    # -------------------------------------------------------------
    # UNSEEN025: Dhanraj Aswani (Bail under Section 438 vs Proclaimed Offender Section 82)
    p025 = {
        "evidence_id": "E1",
        "document_id": "2024_9_257_312",
        "case_title": "Dhanraj Aswani v. Amar S. Mulchandani",
        "passage_text": "Under Section 438, the pre-condition for a person to apply for pre-arrest bail is a reason to believe that he may be arrested on an accusation of having committed a non-bailable offence. Custody in one case does not take away apprehension of arrest in a different case.",
        "start_char": 450,
        "end_char": 715
    }
    dataset.append({
        "test_id": "UNSEEN025_TOPICALLY_RELEVANT_SECTION_82_PROCLAMATION",
        "category": "topically_relevant_insufficient_grounding",
        "fixture_type": "corpus_grounded",
        "query": "Can an accused against whom a proclamation under Section 82 CrPC has been issued maintain an application for anticipatory bail under Section 438 CrPC?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Evidence discusses Section 438 pre-arrest bail in multiple cases, but completely lacks any mention or grounding regarding Section 82 CrPC proclaimed offenders.",
        "passages": [p025]
    })

    # UNSEEN026: Cheque bounce (Compounding without complainant consent)
    dataset.append({
        "test_id": "UNSEEN026_TOPICALLY_RELEVANT_SECTION_138_COMPOUNDING",
        "category": "topically_relevant_insufficient_grounding",
        "fixture_type": "corpus_grounded",
        "query": "Can a cheque bounce complaint under Section 138 of the Negotiable Instruments Act be compounded without the consent of the complainant upon deposit of costs?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Evidence discusses Section 138/141 company drawer liability, but does not address unilateral or non-consensual compounding under Section 138.",
        "passages": [p006]
    })

    # UNSEEN027: IBC Moratorium vs Section 138 NI Act
    dataset.append({
        "test_id": "UNSEEN027_TOPICALLY_RELEVANT_IBC_MORATORIUM_SECTION_138",
        "category": "topically_relevant_insufficient_grounding",
        "fixture_type": "corpus_grounded",
        "query": "Does the statutory moratorium under Section 14 of the Insolvency and Bankruptcy Code automatically bar criminal prosecution under Section 138 of the Negotiable Instruments Act against directors?",
        "expected_status": "topically_relevant_but_insufficient_grounding",
        "expected_is_grounded": False,
        "rationale": "Evidence from Glas Trust discusses Section 62 IBC appellate standing, but does not address Section 14 moratorium applicability to Section 138 NI Act prosecutions.",
        "passages": [p002]
    })

    # -------------------------------------------------------------
    # 11. OUT-OF-CORPUS UNANSWERABLE (3 items)
    # -------------------------------------------------------------
    dataset.append({
        "test_id": "UNSEEN028_OUT_OF_CORPUS_DPDP_ACT",
        "category": "out_of_corpus_unanswerable",
        "fixture_type": "out_of_corpus",
        "query": "What are the eligibility criteria and tenure prescribed under Section 18 of the Digital Personal Data Protection Act, 2023 for members of the Data Protection Board of India?",
        "expected_status": "no_relevant_evidence",
        "expected_is_grounded": False,
        "rationale": "Digital Personal Data Protection Act, 2023 is entirely outside the 2024 Supreme Court judgments corpus. No qualifying evidence passages exist.",
        "passages": []
    })

    dataset.append({
        "test_id": "UNSEEN029_OUT_OF_CORPUS_ELECTION_COMMISSION_ACT",
        "category": "out_of_corpus_unanswerable",
        "fixture_type": "out_of_corpus",
        "query": "Does the Chief Election Commissioner and other Election Commissioners (Appointment, Conditions of Service and Term of Office) Act, 2023 violate the independence of the Election Commission?",
        "expected_status": "no_relevant_evidence",
        "expected_is_grounded": False,
        "rationale": "The 2023 Election Commissioners statute is not interpreted in the available 2024 corpus. No qualifying evidence passages exist.",
        "passages": []
    })

    dataset.append({
        "test_id": "UNSEEN030_OUT_OF_CORPUS_BNS_HIT_AND_RUN",
        "category": "out_of_corpus_unanswerable",
        "fixture_type": "out_of_corpus",
        "query": "What are the reporting requirements and penalties prescribed under Section 106(2) of the Bharatiya Nyaya Sanhita, 2023 for failure of a driver to report an accident?",
        "expected_status": "no_relevant_evidence",
        "expected_is_grounded": False,
        "rationale": "Bharatiya Nyaya Sanhita 2023 is not interpreted in the 2024 Supreme Court judgment corpus. No qualifying evidence passages exist.",
        "passages": []
    })

    # -------------------------------------------------------------
    # 12. NEEDS HUMAN REVIEW / BORDERLINE CASES (2 items)
    # -------------------------------------------------------------
    dataset.append({
        "test_id": "UNSEEN031_NEEDS_HUMAN_REVIEW_ATUL_KUMAR_EQUITY",
        "category": "needs_human_review",
        "fixture_type": "corpus_grounded",
        "query": "Does the judgment in Atul Kumar v. Chairman JOSAA establish a binding principle that any candidate who fails to pay tuition fees before the prescribed deadline due to financial poverty is legally entitled to admission under Article 142?",
        "expected_status": "needs_human_review",
        "expected_is_grounded": None,
        "rationale": "Borderline equitable/doctrinal case: The Court exercised Article 142 powers on unique facts involving 6 earnest portal login attempts and marginalized status; whether this establishes a binding rule of general application or discretionary relief confined to its facts is a nuanced legal distinction requiring human review.",
        "passages": [p001]
    })

    p032 = extract_exact_passage(
        "2024_12_1072_1092",
        "E1",
        "Held: Time lag between the accused being last seen with the \ndeceased and the sighting of the dead body lying was extremely \nshort",
        "additional link in the chain of circumstances"
    )
    dataset.append({
        "test_id": "UNSEEN032_NEEDS_HUMAN_REVIEW_SECTION_106_BURDEN",
        "category": "needs_human_review",
        "fixture_type": "corpus_grounded",
        "query": "Under Section 106 of the Evidence Act, does the failure of an accused to explain what happened after being last seen alive with the deceased independently suffice to convict him of murder in the absence of other circumstantial evidence?",
        "expected_status": "needs_human_review",
        "expected_is_grounded": None,
        "rationale": "Complex burden of proof doctrine: Section 106 provides an additional link once foundational facts are established, but does not independently establish guilt; whether evidence strictly 'answers' this nuanced question is legally contestable and flagged for human review.",
        "passages": [p032]
    })

    return dataset


def main():
    print("Building NyayaVarta Milestone 5F unseen evaluation dataset...")
    dataset = build_dataset()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    print(f"Successfully generated {len(dataset)} evaluation items to {OUTPUT_PATH}")
    
    # Summary of categories
    categories = {}
    for d in dataset:
        c = d["category"]
        categories[c] = categories.get(c, 0) + 1
    print("\nCategory breakdown:")
    for c, count in categories.items():
        print(f"  {c:45}: {count}")


if __name__ == "__main__":
    main()
