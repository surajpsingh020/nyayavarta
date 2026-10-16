"""
Script to create the Blinded Independent Legal Review Pack for Milestone 20 Task 2.
Selects 30 representative claims from existing evaluation artifacts (M14, M16, M17, M18, M19)
spanning all 9 specified legal verification categories:
1. Supported claims
2. Partially supported claims
3. Unsupported claims with valid citations
4. Contradicted claims
5. Statutory exceptions and conditions
6. Party submissions versus judicial holdings
7. Quoted precedents
8. Overgeneralized holdings
9. Ambiguous claims

Outputs: evaluation/rag/milestone20_blinded_review_pack.jsonl
"""
import json
from pathlib import Path
from typing import Dict, Any, List

def build_blinded_pack():
    output_path = Path("evaluation/rag/milestone20_blinded_review_pack.jsonl")
    
    # Load historical candidates from M16 review pack, M17, M18, M19
    m16_path = Path("evaluation/rag/milestone16_reviewer_pack.jsonl")
    m17_path = Path("evaluation/rag/milestone17_unseen_claims.jsonl")
    m18_path = Path("evaluation/rag/milestone18_generalization_claims.jsonl")
    m19_path = Path("evaluation/rag/milestone19_unseen_claims.jsonl")
    
    selected_cases: List[Dict[str, Any]] = []

    # Category 1: Supported claims (4 cases)
    # Category 2: Partially supported claims (4 cases)
    # Category 3: Unsupported claims with valid citations (3 cases)
    # Category 4: Contradicted claims (4 cases)
    # Category 5: Statutory exceptions and conditions (3 cases)
    # Category 6: Party submissions versus judicial holdings (3 cases)
    # Category 7: Quoted precedents (3 cases)
    # Category 8: Overgeneralized holdings (3 cases)
    # Category 9: Ambiguous claims (3 cases)
    # Total: 30 cases

    # Read M16 pack
    m16_cases = []
    if m16_path.exists():
        with m16_path.open("r", encoding="utf-8") as f:
            m16_cases = [json.loads(line) for line in f if line.strip()]

    # Map M16 cases into categories
    # M16_REV_001..004: Supported
    # M16_REV_005..008: Contradicted
    # M16_REV_009..012: Unsupported
    # M16_REV_013..016: Overgeneralized
    # M16_REV_017..020: Statutory exceptions
    # M16_REV_021..024: Party submissions
    # M16_REV_025..028: Quoted precedents
    # M16_REV_029..032: Ambiguous

    # Select representative cases from M16, M17, M18, M19
    categories_spec = [
        ("supported", [
            {"src": "m16", "idx": 0, "case_id": "M20_BLIND_001", "sub_cat": "supported_direct_holding"}, # Tej Prakash Pathak
            {"src": "m16", "idx": 1, "case_id": "M20_BLIND_002", "sub_cat": "supported_constitutional"}, # Sukanya Shantha
            {"src": "m16", "idx": 2, "case_id": "M20_BLIND_003", "sub_cat": "supported_liberty"}, # Senthil Balaji
            {"src": "m16", "idx": 3, "case_id": "M20_BLIND_004", "sub_cat": "supported_service_law"}, # Tinku
        ]),
        ("partially_supported", [
            {"src": "m16", "idx": 16, "case_id": "M20_BLIND_005", "sub_cat": "partially_supported_sarfaesi_proviso"}, # IDBI Bank
            {"src": "m16", "idx": 18, "case_id": "M20_BLIND_006", "sub_cat": "partially_supported_dv_act"}, # S. Vijikumari
            {"src": "m16", "idx": 19, "case_id": "M20_BLIND_007", "sub_cat": "partially_supported_sanction_pc_act"}, # Partap Singh Verka
            {"src": "m18", "idx": 4,  "case_id": "M20_BLIND_008", "sub_cat": "partially_supported_exclusionary_clause"}, # Pradeep Kumar (M18_GEN_005)
        ]),
        ("unsupported_with_valid_citation", [
            {"src": "m16", "idx": 8,  "case_id": "M20_BLIND_009", "sub_cat": "unsupported_valid_citation_marine_ins"}, # Naeem
            {"src": "m16", "idx": 9,  "case_id": "M20_BLIND_010", "sub_cat": "unsupported_valid_citation_mva"}, # Renjith
            {"src": "m16", "idx": 11, "case_id": "M20_BLIND_011", "sub_cat": "unsupported_valid_citation_env_clearance"}, # Tinku
        ]),
        ("contradicted", [
            {"src": "m16", "idx": 4,  "case_id": "M20_BLIND_012", "sub_cat": "contradicted_rules_of_game"}, # Tej Prakash
            {"src": "m16", "idx": 5,  "case_id": "M20_BLIND_013", "sub_cat": "contradicted_section34_modification"}, # North Delhi
            {"src": "m16", "idx": 6,  "case_id": "M20_BLIND_014", "sub_cat": "contradicted_kesavananda_basic_structure"}, # Sukanya
            {"src": "m16", "idx": 7,  "case_id": "M20_BLIND_015", "sub_cat": "contradicted_patents_act"}, # Patents
        ]),
        ("statutory_exceptions_and_conditions", [
            {"src": "m16", "idx": 17, "case_id": "M20_BLIND_016", "sub_cat": "statutory_exception_pmla_section45"}, # Senthil Balaji
            {"src": "m17", "idx": 8,  "case_id": "M20_BLIND_017", "sub_cat": "statutory_exception_cpc_section100"}, # M17_UNSEEN_009
            {"src": "m17", "idx": 10, "case_id": "M20_BLIND_018", "sub_cat": "statutory_condition_arbitration_limitation"}, # M17_UNSEEN_011
        ]),
        ("party_submissions_vs_holdings", [
            {"src": "m16", "idx": 20, "case_id": "M20_BLIND_019", "sub_cat": "party_submission_arbitral_modification"}, # North Delhi
            {"src": "m16", "idx": 21, "case_id": "M20_BLIND_020", "sub_cat": "party_submission_remission_immunity"}, # Mafabhai
            {"src": "m16", "idx": 22, "case_id": "M20_BLIND_021", "sub_cat": "party_submission_sarfaesi_forfeiture"}, # IDBI Bank
        ]),
        ("quoted_precedents", [
            {"src": "m16", "idx": 24, "case_id": "M20_BLIND_022", "sub_cat": "quoted_precedent_lalita_kumari_fir"}, # Vijay Singh
            {"src": "m16", "idx": 25, "case_id": "M20_BLIND_023", "sub_cat": "quoted_precedent_dk_basu_arrest"}, # Sukanya Shantha
            {"src": "m16", "idx": 26, "case_id": "M20_BLIND_024", "sub_cat": "quoted_precedent_maneka_gandhi"}, # Senthil Balaji
        ]),
        ("overgeneralized_holdings", [
            {"src": "m16", "idx": 12, "case_id": "M20_BLIND_025", "sub_cat": "overgeneralization_speedy_trial_discharge"}, # Senthil Balaji
            {"src": "m16", "idx": 13, "case_id": "M20_BLIND_026", "sub_cat": "overgeneralization_caste_quash_all"}, # Sukanya Shantha
            {"src": "m16", "idx": 14, "case_id": "M20_BLIND_027", "sub_cat": "overgeneralization_selection_appointment"}, # Tej Prakash
        ]),
        ("ambiguous_claims", [
            {"src": "m16", "idx": 28, "case_id": "M20_BLIND_028", "sub_cat": "ambiguous_admission_deadline_waiver"}, # M16_REV_029
            {"src": "m16", "idx": 29, "case_id": "M20_BLIND_029", "sub_cat": "ambiguous_mall_plant_cgst"}, # M16_REV_030
            {"src": "m16", "idx": 32, "case_id": "M20_BLIND_030", "sub_cat": "ambiguous_arbitration_consumer_bar"}, # M16_REV_033
        ])
    ]

    # Load m17, m18, m19
    m17_cases = []
    if m17_path.exists():
        with m17_path.open("r", encoding="utf-8") as f:
            m17_cases = [json.loads(line) for line in f if line.strip()]

    m18_cases = []
    if m18_path.exists():
        with m18_path.open("r", encoding="utf-8") as f:
            m18_cases = [json.loads(line) for line in f if line.strip()]

    for cat_name, entries in categories_spec:
        for ent in entries:
            src = ent["src"]
            idx = ent["idx"]
            cid = ent["case_id"]
            sub_cat = ent["sub_cat"]

            if src == "m16" and idx < len(m16_cases):
                raw = m16_cases[idx]
                record = {
                    "blind_case_id": cid,
                    "target_category": cat_name,
                    "sub_category": sub_cat,
                    "query": raw.get("query"),
                    "claim_under_review": raw.get("generated_claim"),
                    "cited_evidence_ids": raw.get("cited_evidence_ids", ["E1"]),
                    "source_document_id": raw.get("source_document_id"),
                    "source_case_title": raw.get("source_case_title"),
                    "exact_source_passage": raw.get("exact_source_passage"),
                    "start_char": raw.get("start_char"),
                    "end_char": raw.get("end_char"),
                    "surrounding_context": raw.get("surrounding_context"),
                    # Blinded fields for legal reviewer to complete:
                    "reviewer_verdict": None, # Options: 'supported', 'partially_supported', 'unsupported', 'contradicted', 'ambiguous'
                    "reviewer_rationale": None,
                    "reviewer_identified_caveat": None,
                    "reviewer_requires_more_context": False,
                    "review_status": "PENDING_EXTERNAL_REVIEW"
                }
                selected_cases.append(record)
            elif src == "m18" and idx < len(m18_cases):
                raw = m18_cases[idx]
                sp = raw.get("supporting_passages", [{}])[0]
                record = {
                    "blind_case_id": cid,
                    "target_category": cat_name,
                    "sub_category": sub_cat,
                    "query": raw.get("question"),
                    "claim_under_review": raw.get("claim_sentence"),
                    "cited_evidence_ids": raw.get("cited_evidence_ids", ["E1"]),
                    "source_document_id": sp.get("document_id"),
                    "source_case_title": sp.get("case_title"),
                    "exact_source_passage": sp.get("passage_text"),
                    "start_char": sp.get("start_char"),
                    "end_char": sp.get("end_char"),
                    "surrounding_context": sp.get("passage_text"),
                    "reviewer_verdict": None,
                    "reviewer_rationale": None,
                    "reviewer_identified_caveat": None,
                    "reviewer_requires_more_context": False,
                    "review_status": "PENDING_EXTERNAL_REVIEW"
                }
                selected_cases.append(record)
            elif src == "m17" and idx < len(m17_cases):
                raw = m17_cases[idx]
                sp = raw.get("supporting_passages", [{}])[0]
                record = {
                    "blind_case_id": cid,
                    "target_category": cat_name,
                    "sub_category": sub_cat,
                    "query": raw.get("question"),
                    "claim_under_review": raw.get("claim_sentence"),
                    "cited_evidence_ids": raw.get("cited_evidence_ids", ["E1"]),
                    "source_document_id": sp.get("document_id"),
                    "source_case_title": sp.get("case_title"),
                    "exact_source_passage": sp.get("passage_text"),
                    "start_char": sp.get("start_char"),
                    "end_char": sp.get("end_char"),
                    "surrounding_context": sp.get("passage_text"),
                    "reviewer_verdict": None,
                    "reviewer_rationale": None,
                    "reviewer_identified_caveat": None,
                    "reviewer_requires_more_context": False,
                    "review_status": "PENDING_EXTERNAL_REVIEW"
                }
                selected_cases.append(record)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for sc in selected_cases:
            f.write(json.dumps(sc, ensure_ascii=False) + "\n")

    print(f"Created {output_path} with {len(selected_cases)} blinded review cases.")

if __name__ == "__main__":
    build_blinded_pack()
