import json
from pathlib import Path
import re

template_path = Path("evaluation/rag/milestone25_reviewer_template.jsonl")
mapping_path = Path("evaluation/rag/milestone25_frozen_mapping.json")
aws_sc_dir = Path("data/processed/aws_sc")

with template_path.open("r", encoding="utf-8") as f:
    template = [json.loads(line) for line in f if line.strip()]

with mapping_path.open("r", encoding="utf-8") as f:
    mapping = json.load(f)

cases_info = []

for t in template:
    cid = t["case_id"]
    m = mapping[cid]
    doc_id = t["official_document_id"]
    title = t["official_case_title"]
    prop = t["legal_proposition"]
    passage = t["source_passage_text"]
    stat_ctx = t["statutory_and_doctrinal_context"]
    cat = m["curated_target_category"]
    sub_cat = m["curated_sub_category"]
    policy_1 = m.get("frozen_system_prediction_policy_1")
    policy_3 = m.get("frozen_system_prediction_policy_3")
    badge = m.get("expected_answer_badge")
    rationale = m.get("doctrinal_rationale")
    
    doc_file = aws_sc_dir / f"{doc_id}.json"
    doc_exists = doc_file.exists()
    doc_full_text = ""
    in_corpus_exact = False
    in_corpus_fuzzy = False
    
    if doc_exists:
        with doc_file.open("r", encoding="utf-8") as df:
            d = json.load(df)
        doc_full_text = d.get("full_text") or d.get("text") or ""
        
        # Check slice
        start = t["source_offsets"]["start_char"]
        end = t["source_offsets"]["end_char"]
        if start is not None and end is not None and end <= len(doc_full_text):
            if doc_full_text[start:end].strip() == passage.strip():
                in_corpus_exact = True
                in_corpus_fuzzy = True
        
        if not in_corpus_exact:
            norm_pass = re.sub(r'\s+', ' ', passage).strip().lower()
            norm_doc = re.sub(r'\s+', ' ', doc_full_text).strip().lower()
            # check 50 char substring
            if norm_pass[:50] in norm_doc:
                in_corpus_fuzzy = True

    # Classification of case type
    # Check if passage is synthetic (from M16 adversarial synthesis or adversarial injection)
    is_synthetic_passage = not in_corpus_fuzzy
    
    # Check metadata mismatch (like M25_REV_017 and 018)
    has_metadata_mismatch = False
    metadata_notes = []
    
    if cid == "M25_REV_017":
        has_metadata_mismatch = True
        metadata_notes.append("SC/ST Act bail proposition mistakenly paired with CPC Section 100 context and subcategory")
    elif cid == "M25_REV_018":
        has_metadata_mismatch = True
        metadata_notes.append("Medical negligence consumer forum proposition mistakenly paired with Arbitration Section 34(3) context and subcategory")
        
    case_record = {
        "case_id": cid,
        "official_document_id": doc_id,
        "official_case_title": title,
        "curated_target_category": cat,
        "curated_sub_category": sub_cat,
        "legal_proposition": prop,
        "source_passage_text": passage,
        "statutory_and_doctrinal_context": stat_ctx,
        "doctrinal_rationale": rationale,
        "frozen_system_prediction_policy_1": policy_1,
        "frozen_system_prediction_policy_3": policy_3,
        "expected_answer_badge": badge,
        "document_exists": doc_exists,
        "in_corpus_exact_slice": in_corpus_exact,
        "in_corpus_fuzzy_passage": in_corpus_fuzzy,
        "is_synthetic_passage": is_synthetic_passage,
        "has_metadata_mismatch": has_metadata_mismatch,
        "metadata_notes": metadata_notes
    }
    cases_info.append(case_record)

print(f"Total cases: {len(cases_info)}")
print(f"In-corpus passages: {sum(1 for c in cases_info if c['in_corpus_fuzzy_passage'])}")
print(f"Synthetic passages: {sum(1 for c in cases_info if c['is_synthetic_passage'])}")
print(f"Metadata mismatches: {sum(1 for c in cases_info if c['has_metadata_mismatch'])}")

# Distribution of categories
from collections import Counter
cat_counts = Counter(c['curated_target_category'] for c in cases_info)
print("\nCategory Distribution:")
for cat, count in cat_counts.items():
    print(f"  {cat}: {count}")

with open("evaluation/rag/final_review_pack_audit_scratch.json", "w", encoding="utf-8") as out:
    json.dump(cases_info, out, indent=2)
print("Saved scratch audit.")
