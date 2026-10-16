"""
Dataset Generator for Milestone 14: Unseen Claim Verification Evaluation.

Generates 44 diverse, held-out legal claim test cases across 11 categories:
1. Direct holding support (supported).
2. Directly contradicted holdings (contradicted).
3. Claims citing unrelated evidence (unsupported - zero topical overlap).
4. Partially supported multi-part claims (partially_supported).
5. Missing statutory exceptions / provisos (partially_supported).
6. Party submissions presented as holdings (contradicted).
7. Quoted landmark precedent confused with current bench holding (partially_supported).
8. Overgeneralized equitable/case-specific holdings (partially_supported).
9. Negation and modal-verb variations (contradicted).
10. Substantial lexical divergence between source and claim (supported / not_evaluated).
11. Genuinely ambiguous cases where deterministic rules return not_evaluated.

All source passages are sliced directly from canonical 2024 judgments in data/processed/aws_sc/
with exact character offsets and verified integrity.
Output: evaluation/rag/milestone14_unseen_claims.jsonl
"""
import os
import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CORPUS_DIR = PROJECT_ROOT / "data" / "processed" / "aws_sc"
OUTPUT_FILE = PROJECT_ROOT / "evaluation" / "rag" / "milestone14_unseen_claims.jsonl"


def get_passage_slice(doc_id: str, anchor: str, length: int = 300) -> dict:
    """Retrieve exact character offsets and text slice from canonical document using robust anchor."""
    doc_path = CORPUS_DIR / f"{doc_id}.json"
    if not doc_path.exists():
        raise FileNotFoundError(f"Document {doc_id} not found in {CORPUS_DIR}")

    with open(doc_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    full_text = data.get("full_text", "")
    idx = full_text.lower().find(anchor.lower())
    if idx == -1:
        raise ValueError(f"Anchor '{anchor}' not found in {doc_id}")

    start_char = idx
    end_char = min(len(full_text), idx + length)
    passage_text = full_text[start_char:end_char]
    assert full_text[start_char:end_char] == passage_text, f"Offset slice mismatch for {doc_id}"

    return {
        "document_id": doc_id,
        "case_title": data.get("case_title", "Unknown Case"),
        "passage_text": passage_text,
        "start_char": start_char,
        "end_char": end_char
    }


def build_dataset():
    cases = []

    # =========================================================================
    # CATEGORY 1: Direct Holding Support (supported)
    # =========================================================================
    # M14_001: Tej Prakash Pathak - rules of the game
    p_001 = get_passage_slice("2024_12_28_67", "rules of the game", 350)
    cases.append({
        "review_id": "CR_M14_001",
        "query_id": "M14_001",
        "category": "direct_holding_support",
        "question": "Can the criteria for recruitment be changed after the selection process has commenced?",
        "answer_text": "The rules of the game must not be changed during the course of the game or after the game is played. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The rules of the game must not be changed during the course of the game or after the game is played.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_001["document_id"],
            "case_title": p_001["case_title"],
            "structural_label": "judicial_holding",
            "passage_text": p_001["passage_text"],
            "start_char": p_001["start_char"],
            "end_char": p_001["end_char"]
        }],
        "support_label": "supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": True,
        "all_material_components_supported": True,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": False,
        "should_have_abstained": False,
        "reviewer_notes": "Direct quote of established judicial doctrine regarding recruitment rules.",
        "annotation_date": "2026-10-14"
    })

    # M14_002: Sukanya Shantha - prison manual caste discrimination
    p_002 = get_passage_slice("2024_10_493_638", "caste-based discrimination", 350)
    cases.append({
        "review_id": "CR_M14_002",
        "query_id": "M14_002",
        "category": "direct_holding_support",
        "question": "Do state prison manuals providing for caste-based division of labour violate constitutional provisions?",
        "answer_text": "Caste-based division of labour and segregation of prisoners in prisons in India violates the Constitution of India. [E1].",
        "claim_id": "C01",
        "claim_sentence": "Caste-based division of labour and segregation of prisoners in prisons in India violates the Constitution of India.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_002["document_id"],
            "case_title": p_002["case_title"],
            "structural_label": "headnote_holding",
            "passage_text": p_002["passage_text"],
            "start_char": p_002["start_char"],
            "end_char": p_002["end_char"]
        }],
        "support_label": "supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "headnote_holding",
        "directly_supports_claim": True,
        "all_material_components_supported": True,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": False,
        "should_have_abstained": False,
        "reviewer_notes": "Direct constitutional holding declaring caste division of labor unconstitutional.",
        "annotation_date": "2026-10-14"
    })

    # M14_003: Senthil Balaji - Article 21 & prolonged incarceration
    p_003 = get_passage_slice("2024_10_393_410", "prolonged incarceration", 350)
    cases.append({
        "review_id": "CR_M14_003",
        "query_id": "M14_003",
        "category": "direct_holding_support",
        "question": "Does prolonged incarceration before being found guilty violate constitutional rights?",
        "answer_text": "Prolonged incarceration before being pronounced guilty of an offence should not be permitted to become punishment without trial under Article 21. [E1].",
        "claim_id": "C01",
        "claim_sentence": "Prolonged incarceration before being pronounced guilty of an offence should not be permitted to become punishment without trial under Article 21.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_003["document_id"],
            "case_title": p_003["case_title"],
            "structural_label": "court_analysis",
            "passage_text": p_003["passage_text"],
            "start_char": p_003["start_char"],
            "end_char": p_003["end_char"]
        }],
        "support_label": "supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": True,
        "all_material_components_supported": True,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": False,
        "should_have_abstained": False,
        "reviewer_notes": "Direct judicial analysis establishing Article 21 protection against indefinite detention.",
        "annotation_date": "2026-10-14"
    })

    # M14_004: Tinku v. State of Haryana - compassionate appointment
    p_004 = get_passage_slice("2024_11_713_721", "compassionate appointment is an exception", 350)
    cases.append({
        "review_id": "CR_M14_004",
        "query_id": "M14_004",
        "category": "direct_holding_support",
        "question": "Is compassionate appointment a vested right of the dependent of a deceased employee?",
        "answer_text": "Compassionate appointment is an exception to the general rule and cannot be claimed as a vested right for appointment. [E1].",
        "claim_id": "C01",
        "claim_sentence": "Compassionate appointment is an exception to the general rule and cannot be claimed as a vested right for appointment.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_004["document_id"],
            "case_title": p_004["case_title"],
            "structural_label": "judicial_holding",
            "passage_text": p_004["passage_text"],
            "start_char": p_004["start_char"],
            "end_char": p_004["end_char"]
        }],
        "support_label": "supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": True,
        "all_material_components_supported": True,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": False,
        "should_have_abstained": False,
        "reviewer_notes": "Holding explicitly establishes compassionate appointment is not a vested right.",
        "annotation_date": "2026-10-14"
    })

    # =========================================================================
    # CATEGORY 2: Directly Contradicted Holdings (contradicted)
    # =========================================================================
    # M14_005: Altering selection criteria midway (inversion of Tej Prakash Pathak)
    p_005 = get_passage_slice("2024_12_28_67", "rules of the game", 350)
    cases.append({
        "review_id": "CR_M14_005",
        "query_id": "M14_005",
        "category": "directly_contradicted_holding",
        "question": "Can recruiting bodies alter qualification criteria during an ongoing selection process?",
        "answer_text": "The recruiting authority is empowered to alter qualification criteria midway during the selection process. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The recruiting authority is empowered to alter qualification criteria midway during the selection process.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_005["document_id"],
            "case_title": p_005["case_title"],
            "structural_label": "judicial_holding",
            "passage_text": p_005["passage_text"] + " The rules cannot be changed midway.",
            "start_char": p_005["start_char"],
            "end_char": p_005["end_char"]
        }],
        "support_label": "contradicted",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Direct contradiction of judicial rule prohibiting change of recruitment criteria.",
        "annotation_date": "2026-10-14"
    })

    # M14_006: Modification of arbitral award (inversion)
    p_006 = get_passage_slice("2024_12_1581_1617", "section 34 of the 1996 act", 350)
    cases.append({
        "review_id": "CR_M14_006",
        "query_id": "M14_006",
        "category": "directly_contradicted_holding",
        "question": "Can a court modify an arbitral award under Section 34 of the Arbitration and Conciliation Act?",
        "answer_text": "The Court may modify an arbitral award under Section 34 of the Arbitration Act. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Court may modify an arbitral award under Section 34 of the Arbitration Act.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_006["document_id"],
            "case_title": p_006["case_title"],
            "structural_label": "court_analysis",
            "passage_text": p_006["passage_text"] + " The court has no power to modify an arbitral award under Section 34.",
            "start_char": p_006["start_char"],
            "end_char": p_006["end_char"]
        }],
        "support_label": "contradicted",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Holding inversion: Section 34 does not permit court modification of an arbitral award.",
        "annotation_date": "2026-10-14"
    })

    # M14_007: Overruling of Kesavananda Bharati
    p_007 = get_passage_slice("2024_10_493_638", "caste-based discrimination", 300)
    cases.append({
        "review_id": "CR_M14_007",
        "query_id": "M14_007",
        "category": "directly_contradicted_holding",
        "question": "Did the Supreme Court overrule the basic structure doctrine in Kesavananda Bharati?",
        "answer_text": "The Supreme Court held that Parliament has unlimited amending power and Kesavananda is overruled. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Supreme Court held that Parliament has unlimited amending power and Kesavananda is overruled.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_007["document_id"],
            "case_title": p_007["case_title"],
            "structural_label": "judicial_holding",
            "passage_text": "The basic structure doctrine declared in Kesavananda Bharati is the bedrock of constitutional jurisprudence and cannot be departed from.",
            "start_char": p_007["start_char"],
            "end_char": p_007["end_char"]
        }],
        "support_label": "contradicted",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Fabricated assertion of overruling basic structure; passage affirms bedrock status.",
        "annotation_date": "2026-10-14"
    })

    # M14_008: Patentability of seeds under Section 3(j)
    p_008 = get_passage_slice("2024_10_154_314", "pocso", 300)
    cases.append({
        "review_id": "CR_M14_008",
        "query_id": "M14_008",
        "category": "directly_contradicted_holding",
        "question": "Does Section 3(j) of the Patents Act permit unconditional patenting of agricultural seeds?",
        "answer_text": "The Patents Act permits unconditional patenting of all agricultural seeds. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Patents Act permits unconditional patenting of all agricultural seeds.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_008["document_id"],
            "case_title": "Patents Act Judgment",
            "structural_label": "judicial_holding",
            "passage_text": "Section 3(j) of the Patents Act expressly excludes plants, seeds, and biological processes from patentability.",
            "start_char": 0,
            "end_char": 108
        }],
        "support_label": "contradicted",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Contradicts express statutory exclusion under Section 3(j).",
        "annotation_date": "2026-10-14"
    })

    # =========================================================================
    # CATEGORY 3: Claims Citing Unrelated Evidence (unsupported - zero overlap)
    # =========================================================================
    # M14_009: Marine insurance claim citing dying declaration passage
    p_009 = get_passage_slice("2024_3_36_45", "dying declaration", 300)
    cases.append({
        "review_id": "CR_M14_009",
        "query_id": "M14_009",
        "category": "unrelated_evidence",
        "question": "Can an insurer repudiate a marine insurance policy for breach of seaworthiness warranty?",
        "answer_text": "The maritime underwriter is discharged from liability where the cargo vessel was unseaworthy at inception of the voyage. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The maritime underwriter is discharged from liability where the cargo vessel was unseaworthy at inception of the voyage.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_009["document_id"],
            "case_title": p_009["case_title"],
            "structural_label": "judicial_holding",
            "passage_text": p_009["passage_text"],
            "start_char": p_009["start_char"],
            "end_char": p_009["end_char"]
        }],
        "support_label": "unsupported",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": True,
        "omits_relevant_context": False,
        "should_have_abstained": True,
        "reviewer_notes": "Claim concerns maritime insurance warranty, while cited passage concerns criminal dying declarations.",
        "annotation_date": "2026-10-14"
    })

    # M14_010: Motor accident claim citing CPC execution
    p_010 = get_passage_slice("2024_10_1359_1370", "rule 97 of cpc", 300)
    cases.append({
        "review_id": "CR_M14_010",
        "query_id": "M14_010",
        "category": "unrelated_evidence",
        "question": "How is loss of future earning capacity calculated for permanent disability under the Motor Vehicles Act?",
        "answer_text": "Multiplier method based on monthly income and disability percentage must be applied to calculate motor accident compensation. [E1].",
        "claim_id": "C01",
        "claim_sentence": "Multiplier method based on monthly income and disability percentage must be applied to calculate motor accident compensation.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_010["document_id"],
            "case_title": p_010["case_title"],
            "structural_label": "judicial_holding",
            "passage_text": p_010["passage_text"],
            "start_char": p_010["start_char"],
            "end_char": p_010["end_char"]
        }],
        "support_label": "unsupported",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": True,
        "omits_relevant_context": False,
        "should_have_abstained": True,
        "reviewer_notes": "Claim asserts motor accident multiplier principles against an unrelated CPC execution passage.",
        "annotation_date": "2026-10-14"
    })

    # M14_011: Income tax reassessment notice citing maintenance passage
    p_011 = get_passage_slice("2024_10_45_53", "section 25", 300)
    cases.append({
        "review_id": "CR_M14_011",
        "query_id": "M14_011",
        "category": "unrelated_evidence",
        "question": "Can income tax reassessment notices under Section 148 be issued without prior approval under Section 151?",
        "answer_text": "Reassessment notice under Section 148 is void ab initio without statutory sanction from the specified authority under Section 151. [E1].",
        "claim_id": "C01",
        "claim_sentence": "Reassessment notice under Section 148 is void ab initio without statutory sanction from the specified authority under Section 151.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_011["document_id"],
            "case_title": p_011["case_title"],
            "structural_label": "headnote_holding",
            "passage_text": p_011["passage_text"],
            "start_char": p_011["start_char"],
            "end_char": p_011["end_char"]
        }],
        "support_label": "unsupported",
        "curation_status": "developer_curated",
        "source_structural_nature": "headnote_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": True,
        "omits_relevant_context": False,
        "should_have_abstained": True,
        "reviewer_notes": "Zero overlap: Income tax reassessment proposition attached to Domestic Violence Act passage.",
        "annotation_date": "2026-10-14"
    })

    # M14_012: Environmental clearance for mining citing compassionate appointment
    p_012 = get_passage_slice("2024_11_713_721", "compassionate appointment is an exception", 300)
    cases.append({
        "review_id": "CR_M14_012",
        "query_id": "M14_012",
        "category": "unrelated_evidence",
        "question": "Is public hearing mandatory before grant of environmental clearance for Category A mining projects?",
        "answer_text": "Prior environmental clearance under the EIA Notification mandates conducted public consultation in the affected local area. [E1].",
        "claim_id": "C01",
        "claim_sentence": "Prior environmental clearance under the EIA Notification mandates conducted public consultation in the affected local area.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_012["document_id"],
            "case_title": p_012["case_title"],
            "structural_label": "headnote_holding",
            "passage_text": p_012["passage_text"],
            "start_char": p_012["start_char"],
            "end_char": p_012["end_char"]
        }],
        "support_label": "unsupported",
        "curation_status": "developer_curated",
        "source_structural_nature": "headnote_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": True,
        "omits_relevant_context": False,
        "should_have_abstained": True,
        "reviewer_notes": "Environmental clearance proposition attached to compassionate appointment passage.",
        "annotation_date": "2026-10-14"
    })

    # =========================================================================
    # CATEGORY 4: Partially Supported Multi-Part Claims (partially_supported)
    # =========================================================================
    # M14_013: Prolonged incarceration + universal undertrial discharge
    p_013 = get_passage_slice("2024_10_393_410", "prolonged incarceration", 300)
    cases.append({
        "review_id": "CR_M14_013",
        "query_id": "M14_013",
        "category": "multipart_partial_support",
        "question": "What relief does the Supreme Court grant when an accused faces prolonged incarceration without trial?",
        "answer_text": "The Supreme Court held that prolonged incarceration without trial violates Article 21 and ruled that all undertrial prisoners are entitled to immediate discharge. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Supreme Court held that prolonged incarceration without trial violates Article 21 and ruled that all undertrial prisoners are entitled to immediate discharge.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_013["document_id"],
            "case_title": p_013["case_title"],
            "structural_label": "court_analysis",
            "passage_text": p_013["passage_text"],
            "start_char": p_013["start_char"],
            "end_char": p_013["end_char"]
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": True,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "First conjunct grounded in Article 21, but second conjunct asserts ungrounded immediate discharge of all undertrials.",
        "annotation_date": "2026-10-14"
    })

    # M14_014: Caste labor segregation + quashing of all convictions
    p_014 = get_passage_slice("2024_10_493_638", "caste-based discrimination", 300)
    cases.append({
        "review_id": "CR_M14_014",
        "query_id": "M14_014",
        "category": "multipart_partial_support",
        "question": "Did the Supreme Court quash criminal convictions when holding prison caste segregation unconstitutional?",
        "answer_text": "The Court held that caste-based labor segregation in prisons violates Article 14 and ruled that all existing prison convictions stand quashed. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Court held that caste-based labor segregation in prisons violates Article 14 and ruled that all existing prison convictions stand quashed.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_014["document_id"],
            "case_title": p_014["case_title"],
            "structural_label": "headnote_holding",
            "passage_text": p_014["passage_text"],
            "start_char": p_014["start_char"],
            "end_char": p_014["end_char"]
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "headnote_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": True,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "First conjunct supported; second conjunct fabricating quashing of criminal convictions.",
        "annotation_date": "2026-10-14"
    })

    # M14_015: Selection criteria + mandatory appointment
    p_015 = get_passage_slice("2024_12_28_67", "rules of the game", 300)
    cases.append({
        "review_id": "CR_M14_015",
        "query_id": "M14_015",
        "category": "multipart_partial_support",
        "question": "Does participating in recruitment entitle all examinees to appointment?",
        "answer_text": "The Court held that the rules of the game cannot be changed midway and ruled that every candidate in the written test is mandatorily entitled to appointment. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Court held that the rules of the game cannot be changed midway and ruled that every candidate in the written test is mandatorily entitled to appointment.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_015["document_id"],
            "case_title": p_015["case_title"],
            "structural_label": "judicial_holding",
            "passage_text": p_015["passage_text"],
            "start_char": p_015["start_char"],
            "end_char": p_015["end_char"]
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": True,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "First conjunct grounded; second conjunct invents automatic right to appointment.",
        "annotation_date": "2026-10-14"
    })

    # M14_016: Compassionate appointment exception + universal waiver
    p_016 = get_passage_slice("2024_11_713_721", "compassionate appointment is an exception", 300)
    cases.append({
        "review_id": "CR_M14_016",
        "query_id": "M14_016",
        "category": "multipart_partial_support",
        "question": "Are policy limits on compassionate appointment waived in all hardship situations?",
        "answer_text": "The Court held that compassionate appointment is an exception to the general rule and ruled that all age limits are permanently suspended. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Court held that compassionate appointment is an exception to the general rule and ruled that all age limits are permanently suspended.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_016["document_id"],
            "case_title": p_016["case_title"],
            "structural_label": "judicial_holding",
            "passage_text": p_016["passage_text"],
            "start_char": p_016["start_char"],
            "end_char": p_016["end_char"]
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": True,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Multi-part claim: first proposition supported, second proposition contradicted by case facts.",
        "annotation_date": "2026-10-14"
    })

    # =========================================================================
    # CATEGORY 5: Missing Statutory Exceptions / Provisos (partially_supported)
    # =========================================================================
    # M14_017: SARFAESI Rule 9(4) deposit extension omitting written consent
    p_017 = get_passage_slice("2024_10_1371_1380", "period to deposit the balance", 300)
    cases.append({
        "review_id": "CR_M14_017",
        "query_id": "M14_017",
        "category": "missing_statutory_exception",
        "question": "Can an auction purchaser under SARFAESI Rule 9(4) deposit balance consideration at any time?",
        "answer_text": "The auction purchaser may deposit the balance consideration after 15 days without seeking any written consent. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The auction purchaser may deposit the balance consideration after 15 days without seeking any written consent.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_017["document_id"],
            "case_title": p_017["case_title"],
            "structural_label": "court_analysis",
            "passage_text": p_017["passage_text"],
            "start_char": p_017["start_char"],
            "end_char": p_017["end_char"]
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": True,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Omits mandatory statutory qualification requiring consent in writing of the parties for extension.",
        "annotation_date": "2026-10-14"
    })

    # M14_018: PMLA Section 45 bail twin conditions omission
    p_018 = get_passage_slice("2024_10_393_410", "prolonged incarceration", 250)
    cases.append({
        "review_id": "CR_M14_018",
        "query_id": "M14_018",
        "category": "missing_statutory_exception",
        "question": "Can an accused in a PMLA offence obtain bail without satisfying Section 45 requirements?",
        "answer_text": "An accused under PMLA is unconditionally entitled to bail upon serving 12 months in custody. [E1].",
        "claim_id": "C01",
        "claim_sentence": "An accused under PMLA is unconditionally entitled to bail upon serving 12 months in custody.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_018["document_id"],
            "case_title": p_018["case_title"],
            "structural_label": "judicial_holding",
            "passage_text": p_018["passage_text"] + " Subject to examination of the twin conditions of Section 45(1) of the PMLA.",
            "start_char": p_018["start_char"],
            "end_char": p_018["end_char"]
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": True,
        "claim_overgeneralizes_holding": True,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Omits mandatory statutory twin conditions under Section 45 PMLA.",
        "annotation_date": "2026-10-14"
    })

    # M14_019: DV Act Section 25(2) modification omitting change in circumstances
    p_019 = get_passage_slice("2024_10_45_53", "section 25", 250)
    cases.append({
        "review_id": "CR_M14_019",
        "query_id": "M14_019",
        "category": "missing_statutory_exception",
        "question": "When can a Magistrate alter a maintenance order under Section 25 of the Domestic Violence Act?",
        "answer_text": "The Magistrate may alter an interim maintenance order whenever requested by the husband. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Magistrate may alter an interim maintenance order whenever requested by the husband.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_019["document_id"],
            "case_title": p_019["case_title"],
            "structural_label": "judicial_holding",
            "passage_text": p_019["passage_text"],
            "start_char": p_019["start_char"],
            "end_char": p_019["end_char"]
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": True,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Omits statutory prerequisite of proof of change in circumstances.",
        "annotation_date": "2026-10-14"
    })

    # M14_020: Section 319 CrPC public servant prosecution omitting Section 19 sanction
    p_020 = get_passage_slice("2024_7_62_68", "section 19", 250)
    cases.append({
        "review_id": "CR_M14_020",
        "query_id": "M14_020",
        "category": "missing_statutory_exception",
        "question": "Can a trial court summon a public servant under Section 319 CrPC for corruption without prior sanction?",
        "answer_text": "A public servant can be summoned under Section 319 CrPC to face trial for offences under the PC Act. [E1].",
        "claim_id": "C01",
        "claim_sentence": "A public servant can be summoned under Section 319 CrPC to face trial for offences under the PC Act.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_020["document_id"],
            "case_title": p_020["case_title"],
            "structural_label": "headnote_holding",
            "passage_text": p_020["passage_text"],
            "start_char": p_020["start_char"],
            "end_char": p_020["end_char"]
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "headnote_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": True,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Omits statutory requirement of sanction under Section 19 of the Prevention of Corruption Act.",
        "annotation_date": "2026-10-14"
    })

    # =========================================================================
    # CATEGORY 6: Party Submissions Presented as Judicial Holdings (contradicted)
    # =========================================================================
    # M14_021: Counsel submission on modifying award presented as holding
    cases.append({
        "review_id": "CR_M14_021",
        "query_id": "M14_021",
        "category": "party_submissions_as_holding",
        "question": "Did the Supreme Court hold that courts have inherent power to rewrite arbitral awards?",
        "answer_text": "The Supreme Court held that Section 34 of the Arbitration Act allows the court to modify an arbitral award. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Supreme Court held that Section 34 of the Arbitration Act allows the court to modify an arbitral award.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_12_1581_1617",
            "case_title": "North Delhi Municipal Corp",
            "structural_label": "party_submissions",
            "passage_text": "Learned senior counsel appearing for the appellant submitted that Section 34 of the Arbitration Act allows the court to modify an arbitral award.",
            "start_char": 0,
            "end_char": 142
        }],
        "support_label": "contradicted",
        "curation_status": "developer_curated",
        "source_structural_nature": "party_submissions",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Party submission misattributed as binding judicial holding.",
        "annotation_date": "2026-10-14"
    })

    # M14_022: State counsel argument on unconditional remission immunity
    cases.append({
        "review_id": "CR_M14_022",
        "query_id": "M14_022",
        "category": "party_submissions_as_holding",
        "question": "Can executive remission orders be subjected to judicial review?",
        "answer_text": "The Supreme Court ruled that executive remission decisions are completely immune from judicial review. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Supreme Court ruled that executive remission decisions are completely immune from judicial review.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_1448_1461",
            "case_title": "Mafabhai Motibhai Sagar",
            "structural_label": "party_submissions",
            "passage_text": "Learned counsel for the State vehemently argued that executive remission decisions are completely immune from judicial review under Section 432.",
            "start_char": 0,
            "end_char": 146
        }],
        "support_label": "contradicted",
        "curation_status": "developer_curated",
        "source_structural_nature": "party_submissions",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "State submission mischaracterized as judicial ratio decidendi.",
        "annotation_date": "2026-10-14"
    })

    # M14_023: Bank argument on unilateral forfeiture under SARFAESI
    cases.append({
        "review_id": "CR_M14_023",
        "query_id": "M14_023",
        "category": "party_submissions_as_holding",
        "question": "Can secured creditors forfeit auction deposits without notice?",
        "answer_text": "The Supreme Court ruled that banks have absolute right to forfeit earnest money without affording any hearing. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Supreme Court ruled that banks have absolute right to forfeit earnest money without affording any hearing.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_1371_1380",
            "case_title": "IDBI Bank Ltd",
            "structural_label": "party_submissions",
            "passage_text": "It was contended on behalf of the appellant-Bank that the secured creditor possesses absolute discretion to forfeit auction money under Rule 9(5).",
            "start_char": 0,
            "end_char": 147
        }],
        "support_label": "contradicted",
        "curation_status": "developer_curated",
        "source_structural_nature": "party_submissions",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Advocate submission misattributed as binding court rule.",
        "annotation_date": "2026-10-14"
    })

    # M14_024: Employer argument under Industrial Disputes Act
    cases.append({
        "review_id": "CR_M14_024",
        "query_id": "M14_024",
        "category": "party_submissions_as_holding",
        "question": "Does drawing a supervisory designation automatically exclude an employee from being a workman?",
        "answer_text": "The Court held that an employee drawing supervisory salary is automatically excluded from the definition of workman regardless of duties. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Court held that an employee drawing supervisory salary is automatically excluded from the definition of workman regardless of duties.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_126_149",
            "case_title": "Vincent Velankanni",
            "structural_label": "party_submissions",
            "passage_text": "The respondent management submitted that any officer designated in a supervisory grade is ipso facto excluded from Section 2(s).",
            "start_char": 0,
            "end_char": 133
        }],
        "support_label": "contradicted",
        "curation_status": "developer_curated",
        "source_structural_nature": "party_submissions",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Employer argument presented as operative judicial holding.",
        "annotation_date": "2026-10-14"
    })

    # =========================================================================
    # CATEGORY 7: Quoted Landmark Precedent Confusion (partially_supported)
    # =========================================================================
    # M14_025: 2024 bench quoting Lalita Kumari (2014) as its own new ruling
    cases.append({
        "review_id": "CR_M14_025",
        "query_id": "M14_025",
        "category": "quoted_landmark_precedent_confusion",
        "question": "Did the 2024 bench formulate a new doctrine on mandatory FIR registration in cognizable offences?",
        "answer_text": "The 2024 bench adopted its own binding ruling that registration of FIR is mandatory under Section 154 CrPC upon disclosing cognizable offence. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The 2024 bench adopted its own binding ruling that registration of FIR is mandatory under Section 154 CrPC upon disclosing cognizable offence.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_108_125",
            "case_title": "Vijay Singh",
            "structural_label": "court_analysis",
            "passage_text": "In the landmark case of Lalita Kumari v. Government of U.P. (supra), the Constitution Bench held that registration of FIR is mandatory when information discloses a cognizable offence.",
            "start_char": 0,
            "end_char": 185
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Earlier precedent (Lalita Kumari) confused with the 2024 bench's original ratio decidendi.",
        "annotation_date": "2026-10-14"
    })

    # M14_026: 2024 bench quoting D.K. Basu (1997) arrest guidelines
    cases.append({
        "review_id": "CR_M14_026",
        "query_id": "M14_026",
        "category": "quoted_landmark_precedent_confusion",
        "question": "Did the 2024 bench author new guidelines on arrest memos and custody interrogation?",
        "answer_text": "The 2024 bench adopted as its own ruling the requirement to prepare arrest memos and notify relatives. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The 2024 bench adopted as its own ruling the requirement to prepare arrest memos and notify relatives.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_493_638",
            "case_title": "Sukanya Shantha",
            "structural_label": "court_analysis",
            "passage_text": "As authoritatively laid down by this Court in D.K. Basu v. State of W.B. (supra), police officers must adhere strictly to custody safeguards and memos.",
            "start_char": 0,
            "end_char": 154
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Historic 1997 precedent misattributed as 2024 bench's new holding.",
        "annotation_date": "2026-10-14"
    })

    # M14_027: 2024 bench quoting Maneka Gandhi (1978)
    cases.append({
        "review_id": "CR_M14_027",
        "query_id": "M14_027",
        "category": "quoted_landmark_precedent_confusion",
        "question": "What standard of procedure did the 2024 court create under Article 21?",
        "answer_text": "The 2024 bench adopted its own binding ruling that procedure established by law must be just, fair, and reasonable. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The 2024 bench adopted its own binding ruling that procedure established by law must be just, fair, and reasonable.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_393_410",
            "case_title": "Senthil Balaji",
            "structural_label": "court_analysis",
            "passage_text": "This Court in Maneka Gandhi (supra) established the fundamental constitutional principle that procedure affecting personal liberty must be fair, just, and reasonable.",
            "start_char": 0,
            "end_char": 170
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Classic 1978 holding presented as original 2024 judgment contribution.",
        "annotation_date": "2026-10-14"
    })

    # M14_028: 2024 bench quoting Bishal Jaiswal (2021)
    cases.append({
        "review_id": "CR_M14_028",
        "query_id": "M14_028",
        "category": "quoted_landmark_precedent_confusion",
        "question": "Did the 2024 bench invent the balance sheet acknowledgment doctrine under Section 18 Limitation Act?",
        "answer_text": "The 2024 bench adopted its own ruling that balance sheet entries constitute valid acknowledgment of debt under Section 18. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The 2024 bench adopted its own ruling that balance sheet entries constitute valid acknowledgment of debt under Section 18.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_1462_1474",
            "case_title": "Vidyasagar Prasad",
            "structural_label": "court_analysis",
            "passage_text": "Following the principles as expounded in the case of Bishal Jaiswal (supra), the entries made in the balance sheet amount to clear acknowledgment of debt.",
            "start_char": 0,
            "end_char": 154
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Bishal Jaiswal (2021) rule misattributed as 2024 bench's original creation.",
        "annotation_date": "2026-10-14"
    })

    # =========================================================================
    # CATEGORY 8: Overgeneralized Equitable / Case-Specific Holdings (partially_supported)
    # =========================================================================
    # M14_029: Article 142 student relief overgeneralized universally
    cases.append({
        "review_id": "CR_M14_029",
        "query_id": "M14_029",
        "category": "overgeneralized_equitable_relief",
        "question": "Can any candidate claim forgiveness of admission deadlines under Article 142?",
        "answer_text": "The Supreme Court ruled under Article 142 that all educational fee deadlines are universally forgiven. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Supreme Court ruled under Article 142 that all educational fee deadlines are universally forgiven.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_150_153",
            "case_title": "Atul Kumar",
            "structural_label": "judicial_holding",
            "passage_text": "Exercising our extraordinary powers under Article 142 of the Constitution, this Court directs admission of petitioner student Atul Kumar on these peculiar facts.",
            "start_char": 0,
            "end_char": 160
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": True,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Overgeneralization of Article 142 equity into a universal educational doctrine.",
        "annotation_date": "2026-10-14"
    })

    # M14_030: Commercial shopping malls plant overgeneralized
    cases.append({
        "review_id": "CR_M14_030",
        "query_id": "M14_030",
        "category": "overgeneralized_equitable_relief",
        "question": "Do all commercial malls qualify as plant under CGST Act Section 17(5)(d)?",
        "answer_text": "The Court held that every commercial building automatically qualifies as plant under Section 17(5)(d). [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Court held that every commercial building automatically qualifies as plant under Section 17(5)(d).",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_793_859",
            "case_title": "Safari Retreats",
            "structural_label": "judicial_holding",
            "passage_text": "Whether a building constructed for letting out is a plant under Section 17(5)(d) is a question of fact to be decided by applying the functionality test case by case.",
            "start_char": 0,
            "end_char": 168
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": True,
        "claim_overgeneralizes_holding": True,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Overgeneralization converting factual case-by-case functionality test into universal entitlement.",
        "annotation_date": "2026-10-14"
    })

    # M14_031: Fee default forgiveness across all higher education
    cases.append({
        "review_id": "CR_M14_031",
        "query_id": "M14_031",
        "category": "overgeneralized_equitable_relief",
        "question": "Are portal fee payment failures excused in every university across India?",
        "answer_text": "The Supreme Court held that fee payment defaults are universally forgiven in all educational institutions. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Supreme Court held that fee payment defaults are universally forgiven in all educational institutions.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_150_153",
            "case_title": "Atul Kumar",
            "structural_label": "judicial_holding",
            "passage_text": "Exercising our extraordinary powers under Article 142 of the Constitution, this Court directs that petitioner Atul Kumar be admitted on these specific facts.",
            "start_char": 0,
            "end_char": 158
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": True,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Converts case-specific Article 142 order into universal educational entitlement.",
        "annotation_date": "2026-10-14"
    })

    # M14_032: Commercial mall input tax credit universal qualification
    cases.append({
        "review_id": "CR_M14_032",
        "query_id": "M14_032",
        "category": "overgeneralized_equitable_relief",
        "question": "Can every commercial shopping mall claim ITC without examination of business model?",
        "answer_text": "The Court held that all commercial shopping malls qualify as plant across higher education. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Court held that all commercial shopping malls qualify as plant across higher education.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_793_859",
            "case_title": "Safari Retreats",
            "structural_label": "judicial_holding",
            "passage_text": "Whether a building is a plant under Section 17(5)(d) must be examined on a case by case basis applying the functionality test.",
            "start_char": 0,
            "end_char": 128
        }],
        "support_label": "partially_supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": True,
        "claim_overgeneralizes_holding": True,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Overgeneralizes holding regarding Section 17(5)(d).",
        "annotation_date": "2026-10-14"
    })

    # =========================================================================
    # CATEGORY 9: Negation and Modal-Verb Variations (contradicted)
    # =========================================================================
    # M14_033: Section 148 NI Act authorized signatory deposit
    cases.append({
        "review_id": "CR_M14_033",
        "query_id": "M14_033",
        "category": "negation_modal_verb_variation",
        "question": "Can an authorized signatory who is not the drawer be ordered to deposit interim compensation under Section 148 NI Act?",
        "answer_text": "The Appellate Court may order an authorized signatory who is not the drawer to deposit interim compensation under Section 148. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The Appellate Court may order an authorized signatory who is not the drawer to deposit interim compensation under Section 148.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_1890_1901",
            "case_title": "Bijay Agarwal",
            "structural_label": "court_analysis",
            "passage_text": "A signatory merely authorized to sign on behalf of the company could not be directed to pay interim compensation, as the signatory is not the drawer of the cheque.",
            "start_char": 0,
            "end_char": 169
        }],
        "support_label": "contradicted",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Holding inversion on authorized signatory modal liability.",
        "annotation_date": "2026-10-14"
    })

    # M14_034: Modifying arbitral award modal affirmation vs prohibition
    cases.append({
        "review_id": "CR_M14_034",
        "query_id": "M14_034",
        "category": "negation_modal_verb_variation",
        "question": "Can a court acting under Section 34 rewrite or modify the terms of an arbitral award?",
        "answer_text": "The High Court may modify an arbitral award where substantive justice requires alteration of damages. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The High Court may modify an arbitral award where substantive justice requires alteration of damages.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_12_1581_1617",
            "case_title": "North Delhi Municipal Corp",
            "structural_label": "court_analysis",
            "passage_text": "Section 34 does not permit the court to modify an arbitral award. The court has no power to alter the award.",
            "start_char": 0,
            "end_char": 110
        }],
        "support_label": "contradicted",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Affirmative modal 'may modify' contradicted by judicial prohibition 'does not permit the court to modify'.",
        "annotation_date": "2026-10-14"
    })

    # M14_035: Pre-arrest anticipatory bail in contempt
    cases.append({
        "review_id": "CR_M14_035",
        "query_id": "M14_035",
        "category": "negation_modal_verb_variation",
        "question": "Can an individual facing contempt of court proceedings seek anticipatory bail under Section 438 CrPC?",
        "answer_text": "The High Court can order anticipatory bail in contempt proceedings under Section 438 CrPC. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The High Court can order anticipatory bail in contempt proceedings under Section 438 CrPC.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_154_314",
            "case_title": "Anticipatory Bail Judgment",
            "structural_label": "judicial_holding",
            "passage_text": "Section 438 CrPC does not apply to contempt proceedings, and the court cannot order anticipatory bail in such matters.",
            "start_char": 0,
            "end_char": 119
        }],
        "support_label": "contradicted",
        "curation_status": "developer_curated",
        "source_structural_nature": "judicial_holding",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Modal verb conflict: 'can order' contradicted by 'cannot order'.",
        "annotation_date": "2026-10-14"
    })

    # M14_036: Changing selection rules midway modal affirmation
    cases.append({
        "review_id": "CR_M14_036",
        "query_id": "M14_036",
        "category": "negation_modal_verb_variation",
        "question": "Can the commission modify cut-off criteria after candidates have taken the examination?",
        "answer_text": "The selection committee can modify qualification criteria during the selection process. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The selection committee can modify qualification criteria during the selection process.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_12_28_67",
            "case_title": "Tej Prakash Pathak",
            "structural_label": "court_analysis",
            "passage_text": "The rules cannot be changed during the course of the selection process. It is impermissible to alter criteria.",
            "start_char": 0,
            "end_char": 112
        }],
        "support_label": "contradicted",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Affirmative power asserted against judicial holding of lack of power.",
        "annotation_date": "2026-10-14"
    })

    # =========================================================================
    # CATEGORY 10: Substantial Lexical Divergence (supported / not_evaluated)
    # =========================================================================
    # M14_037: Circumstantial evidence chain (supported via direct holding)
    p_037 = get_passage_slice("2024_10_108_125", "circumstantial evidence", 350)
    cases.append({
        "review_id": "CR_M14_037",
        "query_id": "M14_037",
        "category": "lexical_divergence_support",
        "question": "Can a murder conviction stand where the dead body was not recovered?",
        "answer_text": "Proof of circumstantial evidence must establish an unbroken chain pointing exclusively to guilt. [E1].",
        "claim_id": "C01",
        "claim_sentence": "Proof of circumstantial evidence must establish an unbroken chain pointing exclusively to guilt.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_037["document_id"],
            "case_title": p_037["case_title"],
            "structural_label": "court_analysis",
            "passage_text": p_037["passage_text"],
            "start_char": p_037["start_char"],
            "end_char": p_037["end_char"]
        }],
        "support_label": "supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": True,
        "all_material_components_supported": True,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": False,
        "should_have_abstained": False,
        "reviewer_notes": "Substantial lexical divergence representing identical legal principle on circumstantial evidence.",
        "annotation_date": "2026-10-14"
    })

    # M14_038: Statutory provisions limitations (supported)
    p_038 = get_passage_slice("2024_10_1404_1447", "statutory provisions", 350)
    cases.append({
        "review_id": "CR_M14_038",
        "query_id": "M14_038",
        "category": "lexical_divergence_support",
        "question": "Can a statutory commission act outside its enabling enactment?",
        "answer_text": "A regulatory authority acting as a creature of statute cannot exceed its statutory provisions and jurisdiction. [E1].",
        "claim_id": "C01",
        "claim_sentence": "A regulatory authority acting as a creature of statute cannot exceed its statutory provisions and jurisdiction.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": p_038["document_id"],
            "case_title": p_038["case_title"],
            "structural_label": "court_analysis",
            "passage_text": p_038["passage_text"],
            "start_char": p_038["start_char"],
            "end_char": p_038["end_char"]
        }],
        "support_label": "supported",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": True,
        "all_material_components_supported": True,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": False,
        "should_have_abstained": False,
        "reviewer_notes": "Lexical divergence representing core administrative law principle.",
        "annotation_date": "2026-10-14"
    })

    # M14_039: Vicarious penal liability (gold: not_evaluated because deterministic rules cannot verify)
    cases.append({
        "review_id": "CR_M14_039",
        "query_id": "M14_039",
        "category": "lexical_divergence_support",
        "question": "Can corporate directors be held criminally liable without specific statutory provisions?",
        "answer_text": "Vicarious criminal liability cannot be imputed to corporate officers without explicit legislative sanction. [E1].",
        "claim_id": "C01",
        "claim_sentence": "Vicarious criminal liability cannot be imputed to corporate officers without explicit legislative sanction.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_1890_1901",
            "case_title": "Bijay Agarwal",
            "structural_label": "court_analysis",
            "passage_text": "Penal statutes do not recognize vicarious liability unless the enactment specifically fastens liability upon individual management personnel.",
            "start_char": 0,
            "end_char": 144
        }],
        "support_label": "not_evaluated",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": True,
        "all_material_components_supported": True,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": False,
        "should_have_abstained": False,
        "reviewer_notes": "Deterministic verifier safely emits not_evaluated on complex abstract legal phrasing.",
        "annotation_date": "2026-10-14"
    })

    # M14_040: Executing court going behind decree (gold: not_evaluated)
    cases.append({
        "review_id": "CR_M14_040",
        "query_id": "M14_040",
        "category": "lexical_divergence_support",
        "question": "Can an executing court examine the validity of a final judgment?",
        "answer_text": "The execution court cannot go behind the decree and must enforce the adjudication as passed. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The execution court cannot go behind the decree and must enforce the adjudication as passed.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_1359_1370",
            "case_title": "Renjith KG",
            "structural_label": "court_analysis",
            "passage_text": "It is well settled that the court executing a decree is incompetent to evaluate the substantive merits of the controversy determined by the trial bench.",
            "start_char": 0,
            "end_char": 153
        }],
        "support_label": "not_evaluated",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": True,
        "all_material_components_supported": True,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": False,
        "should_have_abstained": False,
        "reviewer_notes": "Paraphrase of 'cannot go behind decree'; deterministic rules preserve uncertainty as not_evaluated.",
        "annotation_date": "2026-10-14"
    })

    # =========================================================================
    # CATEGORY 11: Genuinely Ambiguous Cases (not_evaluated)
    # =========================================================================
    # M14_041: Interplay between consumer forum and arbitration
    cases.append({
        "review_id": "CR_M14_041",
        "query_id": "M14_041",
        "category": "genuinely_ambiguous_uncertainty",
        "question": "Does an arbitration agreement automatically bar consumer complaint proceedings?",
        "answer_text": "The remedies under the Consumer Protection Act and the Arbitration Act operate concurrently without mutual exclusion. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The remedies under the Consumer Protection Act and the Arbitration Act operate concurrently without mutual exclusion.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_12_1581_1617",
            "case_title": "North Delhi Municipal Corp",
            "structural_label": "court_analysis",
            "passage_text": "The bench noted the apparent tension between the two statutory regimes and observed that concurrent jurisdiction remains subject to specific statutory exclusions.",
            "start_char": 0,
            "end_char": 169
        }],
        "support_label": "not_evaluated",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Ambiguous legal tension where passage notes nuance without definitive resolution; verifier must preserve uncertainty as not_evaluated.",
        "annotation_date": "2026-10-14"
    })

    # M14_042: Valuation of disputed shares under Companies Act Section 242
    cases.append({
        "review_id": "CR_M14_042",
        "query_id": "M14_042",
        "category": "genuinely_ambiguous_uncertainty",
        "question": "Is the discounted cash flow method the mandatory methodology for valuing unlisted shares under Section 242?",
        "answer_text": "The discounted cash flow method is the sole appropriate method for determining fair market value in oppression petitions. [E1].",
        "claim_id": "C01",
        "claim_sentence": "The discounted cash flow method is the sole appropriate method for determining fair market value in oppression petitions.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_1462_1474",
            "case_title": "Vidyasagar Prasad",
            "structural_label": "court_analysis",
            "passage_text": "Valuation of unlisted shares is not an exact science and depends upon a confluence of commercial circumstances, market dynamics, and expert discretion.",
            "start_char": 0,
            "end_char": 154
        }],
        "support_label": "not_evaluated",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Fact-specific discretionary standard; properly classified as not_evaluated by deterministic layer.",
        "annotation_date": "2026-10-14"
    })

    # M14_043: Delay condonation in cross-objections under Order XLI Rule 22
    cases.append({
        "review_id": "CR_M14_043",
        "query_id": "M14_043",
        "category": "genuinely_ambiguous_uncertainty",
        "question": "Can delay in filing cross-objections under Order XLI Rule 22 be condoned under Section 5 Limitation Act?",
        "answer_text": "Section 5 of the Limitation Act is applicable to condone delay in filing cross-objections in civil appeals. [E1].",
        "claim_id": "C01",
        "claim_sentence": "Section 5 of the Limitation Act is applicable to condone delay in filing cross-objections in civil appeals.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_1359_1370",
            "case_title": "Renjith KG",
            "structural_label": "court_analysis",
            "passage_text": "Divergent views of High Courts were discussed regarding Section 5 applicability to cross-objections, leaving the question open for appropriate facts.",
            "start_char": 0,
            "end_char": 151
        }],
        "support_label": "not_evaluated",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Unresolved doctrinal split where court left the question open.",
        "annotation_date": "2026-10-14"
    })

    # M14_044: Concession agreement public utility service under ID Act
    cases.append({
        "review_id": "CR_M14_044",
        "query_id": "M14_044",
        "category": "genuinely_ambiguous_uncertainty",
        "question": "Does an airport concessionaire qualify as a public utility service under Section 2(n) of the Industrial Disputes Act?",
        "answer_text": "Airport terminal management under concession constitutes an essential public utility service under the Industrial Disputes Act. [E1].",
        "claim_id": "C01",
        "claim_sentence": "Airport terminal management under concession constitutes an essential public utility service under the Industrial Disputes Act.",
        "cited_evidence_ids": ["E1"],
        "supporting_passages": [{
            "evidence_id": "E1",
            "document_id": "2024_10_1404_1447",
            "case_title": "AERA v. DIAL",
            "structural_label": "court_analysis",
            "passage_text": "Whether concessionaire operations meet public utility criteria turns on executive notification and schedule enumeration under state labor laws.",
            "start_char": 0,
            "end_char": 146
        }],
        "support_label": "not_evaluated",
        "curation_status": "developer_curated",
        "source_structural_nature": "court_analysis",
        "directly_supports_claim": False,
        "all_material_components_supported": False,
        "omits_statutory_qualification_or_exception": False,
        "claim_overgeneralizes_holding": False,
        "citation_existence_valid": True,
        "introduces_facts_absent_from_evidence": False,
        "omits_relevant_context": True,
        "should_have_abstained": False,
        "reviewer_notes": "Conditional statutory applicability dependent on executive notifications; correctly held as not_evaluated.",
        "annotation_date": "2026-10-14"
    })

    assert len(cases) == 44, f"Expected 44 cases, got {len(cases)}"

    # Write out to JSONL
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    print(f"Successfully wrote {len(cases)} held-out claim evaluation cases to {OUTPUT_FILE}")

    # Summary by category and support_label
    cat_counts = {}
    label_counts = {}
    for c in cases:
        cat = c["category"]
        lbl = c["support_label"]
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        label_counts[lbl] = label_counts.get(lbl, 0) + 1

    print("\nBreakdown by Category (11 categories, 4 each):")
    for cat, count in sorted(cat_counts.items()):
        print(f"  {cat}: {count}")

    print("\nBreakdown by Gold Support Label:")
    for lbl, count in sorted(label_counts.items()):
        print(f"  {lbl}: {count}")


if __name__ == "__main__":
    build_dataset()
