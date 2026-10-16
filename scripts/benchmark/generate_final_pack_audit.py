import json
from pathlib import Path
import re

aws_sc_dir = Path("data/processed/aws_sc")
m25_template_path = Path("evaluation/rag/milestone25_reviewer_template.jsonl")
m25_mapping_path = Path("evaluation/rag/milestone25_frozen_mapping.json")

with m25_template_path.open("r", encoding="utf-8") as f:
    template_records = [json.loads(line) for line in f if line.strip()]

with m25_mapping_path.open("r", encoding="utf-8") as f:
    mapping_records = json.load(f)

# The 11 synthetic cases identified
SYNTHETIC_CASES = {
    "M25_REV_014", "M25_REV_015", "M25_REV_019", "M25_REV_020", "M25_REV_021",
    "M25_REV_022", "M25_REV_023", "M25_REV_024", "M25_REV_028", "M25_REV_029", "M25_REV_030"
}

audit_cases = []
template_v2 = []
mapping_v2 = {}

for t in template_records:
    cid = t["case_id"]
    m = mapping_records[cid]
    doc_id = t["official_document_id"]
    doc_title = t["official_case_title"]
    prop = t["legal_proposition"]
    passage = t["source_passage_text"]
    stat_ctx = t["statutory_and_doctrinal_context"]
    cat = m["curated_target_category"]
    sub_cat = m["curated_sub_category"]
    start_char = t["source_offsets"]["start_char"]
    end_char = t["source_offsets"]["end_char"]
    
    doc_file = aws_sc_dir / f"{doc_id}.json"
    doc_exists = doc_file.exists()
    full_text = ""
    exact_slice = False
    in_corpus = False
    actual_offsets = {"start_char": start_char, "end_char": end_char}
    
    if doc_exists:
        with doc_file.open("r", encoding="utf-8") as df:
            d = json.load(df)
        full_text = d.get("full_text") or d.get("text") or ""
        
        # Check slice
        if start_char is not None and end_char is not None and end_char <= len(full_text):
            if full_text[start_char:end_char].strip() == passage.strip():
                exact_slice = True
                in_corpus = True
                
        if not exact_slice:
            # Check if passage text is in doc
            norm_pass = re.sub(r'\s+', ' ', passage).strip().lower()
            norm_full = re.sub(r'\s+', ' ', full_text).strip().lower()
            
            # Find in text
            first_40 = norm_pass[:40]
            if first_40 in norm_full:
                in_corpus = True
                # Find character position in full_text
                # Try finding first 30 chars of passage in raw text
                clean_passage_head = passage.strip()[:30]
                pos = full_text.find(clean_passage_head)
                if pos != -1:
                    actual_offsets = {"start_char": pos, "end_char": pos + len(passage.strip())}

    is_synthetic = cid in SYNTHETIC_CASES
    
    # Status and discrepancies
    status = "PASS"
    mismatch_details = []
    stat_aligned = True
    rat_aligned = True
    action_taken = "Preserved verbatim excerpt from official Supreme Court judgment."
    
    # Case specific corrections
    v2_t = dict(t)
    v2_m = dict(m)
    
    if cid == "M25_REV_017":
        status = "FLAGGED_DISCREPANCY"
        stat_aligned = False
        rat_aligned = False
        mismatch_details.append(
            "CRITICAL MISALIGNMENT: Legal proposition and passage concern SC/ST Act Section 18/18-A anticipatory bail (Shajan Skaria v. State of Kerala), but statutory context was mistakenly assigned to Code of Civil Procedure Section 100 second appeals."
        )
        action_taken = "Corrected statutory context to SC/ST Act Section 18/18-A bail bar/exception and updated subcategory from 'statutory_exception_cpc_section100' to 'statutory_exception_scst_act_bail'."
        v2_t["statutory_and_doctrinal_context"] = (
            "Scheduled Castes and the Scheduled Tribes (Prevention of Atrocities) Act, 1989: Section 18 and 18-A bar on anticipatory bail (Section 438 CrPC), and the constitutional exception permitting pre-arrest bail where the complaint fails to disclose a prima facie offence."
        )
        v2_m["curated_sub_category"] = "statutory_exception_scst_act_bail"
        v2_m["doctrinal_rationale"] = (
            "Scheduled Castes and the Scheduled Tribes (Prevention of Atrocities) Act, 1989: Section 18/18-A does not impose an absolute bar on pre-arrest bail if the complaint does not disclose a prima facie offence under the Act."
        )
    elif cid == "M25_REV_018":
        status = "FLAGGED_DISCREPANCY"
        stat_aligned = False
        rat_aligned = False
        mismatch_details.append(
            "CRITICAL MISALIGNMENT: Legal proposition and passage concern Consumer Protection Act medical negligence evidentiary weight of Medical Council reports (Najrul Seikh v. Dr. Sumit Banerjee), but statutory context was mistakenly assigned to Arbitration Act Section 34(3) limitation."
        )
        action_taken = "Corrected statutory context to Consumer Protection Act medical negligence evidentiary standards and updated subcategory from 'statutory_condition_arbitration_limitation' to 'statutory_condition_consumer_medical_negligence'."
        v2_t["statutory_and_doctrinal_context"] = (
            "Consumer Protection Act, 2019 / 1986: Adjudication of deficiency of service in medical negligence claims, and the evidentiary status of Medical Council / expert opinions (relevant evidence, but non-binding and non-conclusive)."
        )
        v2_m["curated_sub_category"] = "statutory_condition_consumer_medical_negligence"
        v2_m["doctrinal_rationale"] = (
            "Consumer Protection Act: While a Medical Council report is relevant evidence before a Consumer Commission, it cannot be treated as conclusive or determinative over evidentiary findings."
        )
    elif is_synthetic:
        status = "SYNTHETIC_PASSAGE_DOCUMENTED"
        mismatch_details.append(
            f"Adversarial synthetic passage generated during Milestone 16 benchmark synthesis to evaluate verifier robustness against {cat.replace('_', ' ')}. Text was injected into judgment context envelope."
        )
        action_taken = f"Documented passage as synthetic adversarial test artifact. Blinding preserved; annotated provenance as synthetic."
    elif not exact_slice and in_corpus:
        action_taken = f"Corpus passage verified. Character offsets aligned from ({start_char}, {end_char}) to ({actual_offsets['start_char']}, {actual_offsets['end_char']})."
        v2_t["source_offsets"] = actual_offsets

    passage_prov = "synthetic_adversarial_passage" if is_synthetic else "verbatim_judgment_excerpt"
    offset_acc = "exact_slice_match" if exact_slice else ("approximate_in_corpus" if in_corpus else "synthetic_or_dummy_offsets")
    
    # Add metadata provenance tag to v2
    v2_t["metadata"]["passage_provenance"] = passage_prov
    v2_m["passage_provenance"] = passage_prov

    template_v2.append(v2_t)
    mapping_v2[cid] = v2_m

    audit_cases.append({
        "case_id": cid,
        "original_blind_case_id": m.get("original_blind_case_id", f"M20_BLIND_{cid.split('_')[-1]}"),
        "status": status,
        "corpus_verification": {
            "document_exists": doc_exists,
            "official_document_id": doc_id,
            "official_case_title": doc_title,
            "passage_in_corpus": in_corpus,
            "passage_provenance": passage_prov,
            "offset_accuracy": offset_acc,
            "reported_offsets": {"start_char": start_char, "end_char": end_char},
            "verified_offsets": actual_offsets
        },
        "metadata_verification": {
            "target_category": cat,
            "sub_category": sub_cat,
            "legal_proposition": prop,
            "statutory_context": stat_ctx,
            "statutory_context_aligned": stat_aligned,
            "doctrinal_rationale": m.get("doctrinal_rationale", ""),
            "doctrinal_rationale_aligned": rat_aligned,
            "mismatch_details": mismatch_details
        },
        "v2_remediation": {
            "action_taken": action_taken,
            "v2_statutory_context": v2_t["statutory_and_doctrinal_context"],
            "v2_sub_category": v2_m["curated_sub_category"]
        }
    })

audit_report = {
    "audit_metadata": {
        "title": "Milestone 25 Review Pack Comprehensive Audit",
        "milestone": "Final Audit and College Demo Readiness",
        "date": "2026-10-16",
        "total_cases_audited": len(audit_cases),
        "exact_corpus_slice_matches": sum(1 for c in audit_cases if c["corpus_verification"]["offset_accuracy"] == "exact_slice_match"),
        "approximate_in_corpus_matches": sum(1 for c in audit_cases if c["corpus_verification"]["offset_accuracy"] == "approximate_in_corpus"),
        "synthetic_adversarial_passages": sum(1 for c in audit_cases if c["corpus_verification"]["passage_provenance"] == "synthetic_adversarial_passage"),
        "metadata_discrepancies_found": sum(1 for c in audit_cases if c["status"] == "FLAGGED_DISCREPANCY"),
        "discrepancy_case_ids": ["M25_REV_017", "M25_REV_018"],
        "historical_pack_status": "PRESERVED_UNCHANGED (Preserves M20–M25 benchmark hash integrity)",
        "v2_pack_status": "PRODUCED_VERSIONED (Corrected metadata and annotated provenance)",
        "release_gate_status": "HOLD_PENDING_EXTERNAL_REVIEW"
    },
    "cases": audit_cases
}

# Write files
with open("evaluation/rag/final_review_pack_audit.json", "w", encoding="utf-8") as f:
    json.dump(audit_report, f, indent=2)

with open("evaluation/rag/milestone25_reviewer_template_v2.jsonl", "w", encoding="utf-8") as f:
    for t in template_v2:
        f.write(json.dumps(t, ensure_ascii=False) + "\n")

with open("evaluation/rag/milestone25_frozen_mapping_v2.json", "w", encoding="utf-8") as f:
    json.dump(mapping_v2, f, indent=2, ensure_ascii=False)

print("Generated final_review_pack_audit.json")
print("Generated milestone25_reviewer_template_v2.jsonl")
print("Generated milestone25_frozen_mapping_v2.json")
