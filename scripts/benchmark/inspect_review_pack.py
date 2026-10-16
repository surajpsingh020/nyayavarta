import json
from pathlib import Path
import re

mapping_path = Path("evaluation/rag/milestone25_frozen_mapping.json")
template_path = Path("evaluation/rag/milestone25_reviewer_template.jsonl")
aws_sc_dir = Path("data/processed/aws_sc")

with mapping_path.open("r", encoding="utf-8") as f:
    mapping = json.load(f)

with template_path.open("r", encoding="utf-8") as f:
    template = [json.loads(l) for l in f if l.strip()]

results = []

for t in template:
    cid = t["case_id"]
    m = mapping.get(cid, {})
    doc_id = t["official_document_id"]
    title = t["official_case_title"]
    prop = t["legal_proposition"]
    passage = t["source_passage_text"]
    start_char = t["source_offsets"]["start_char"]
    end_char = t["source_offsets"]["end_char"]
    stat_ctx = t["statutory_and_doctrinal_context"]
    rationale = m.get("doctrinal_rationale", "")
    target_cat = m.get("curated_target_category", "")
    sub_cat = m.get("curated_sub_category", "")

    doc_file = aws_sc_dir / f"{doc_id}.json"
    doc_exists = doc_file.exists()
    
    doc_title_match = False
    doc_passage_match = False
    passage_offset_match = False
    doc_title_actual = None
    doc_text_len = 0
    statute_in_doc = None
    statute_in_passage = None

    if doc_exists:
        try:
            with doc_file.open("r", encoding="utf-8") as df:
                doc_data = json.load(df)
            doc_title_actual = doc_data.get("title", "")
            raw_text = doc_data.get("full_text") or doc_data.get("text") or ""
            doc_text_len = len(raw_text)
            
            # Title match check (relaxed)
            t_clean = re.sub(r'[^a-zA-Z0-9]', '', title.lower())
            dt_clean = re.sub(r'[^a-zA-Z0-9]', '', doc_title_actual.lower())
            doc_title_match = (t_clean in dt_clean) or (dt_clean in t_clean) or (t_clean[:20] in dt_clean)
            
            # Passage match in document
            clean_pass = " ".join(passage.replace("", " ").split())[:50]
            clean_raw = " ".join(raw_text.replace("", " ").split())
            doc_passage_match = clean_pass.lower() in clean_raw.lower()
            
            # Exact offset check
            if start_char is not None and end_char is not None and end_char <= doc_text_len:
                slice_text = raw_text[start_char:end_char]
                clean_slice = " ".join(slice_text.replace("", " ").split())[:50]
                passage_offset_match = clean_slice.lower() == clean_pass.lower()
        except Exception as e:
            doc_exists = False
            doc_title_actual = f"Error: {e}"

    # Check whether claim and rationale concern the same legal issue
    # Extract legal keywords from prop and stat_ctx
    prop_lower = prop.lower()
    stat_lower = stat_ctx.lower()
    
    # Topical alignment check
    # Check if key tokens in stat_ctx appear in prop or passage
    stat_tokens = set(re.findall(r'\b[a-zA-Z0-9]{4,}\b', stat_lower)) - {
        "section", "article", "court", "supreme", "india", "under", "with", "from",
        "that", "this", "which", "provisions", "procedure", "doctrine", "established", "examined"
    }
    pass_prop_tokens = set(re.findall(r'\b[a-zA-Z0-9]{4,}\b', prop_lower + " " + passage.lower()))
    common_tokens = stat_tokens.intersection(pass_prop_tokens)
    
    # Flag known mismatches or low overlap
    mismatch_flag = False
    mismatch_reasons = []
    
    if not doc_exists:
        mismatch_flag = True
        mismatch_reasons.append(f"Document ID {doc_id} not found in {aws_sc_dir}")
        
    if doc_exists and not doc_title_match:
        mismatch_reasons.append(f"Title mismatch: template '{title[:30]}...' vs doc '{doc_title_actual[:30]}...'")
        
    if doc_exists and not doc_passage_match:
        mismatch_reasons.append("Source passage text not found in document full text")
        
    # Check specific keyword divergence between proposition and statutory context
    # E.g. SC/ST Act vs CPC Section 100
    if ("sc/st" in prop_lower or "1989 act" in prop_lower or "shajan" in title.lower()) and "cpc" in stat_lower:
        mismatch_flag = True
        mismatch_reasons.append("Severe Mismatch: Claim concerns SC/ST Act anticipatory bail, but statutory context describes CPC Section 100")
        
    # E.g. Medical negligence / consumer vs Arbitration limitation
    if ("consumer" in prop_lower or "medical" in prop_lower or "negligence" in prop_lower) and "arbitration" in stat_lower:
        mismatch_flag = True
        mismatch_reasons.append("Severe Mismatch: Claim concerns Consumer Forum / Medical Negligence, but statutory context describes Arbitration Act Section 34(3)")
        
    # Check other cases
    if len(common_tokens) == 0 and len(stat_tokens) > 0:
        mismatch_reasons.append(f"Low semantic overlap between claim/passage and statutory context (common tokens: {common_tokens})")

    res = {
        "case_id": cid,
        "doc_id": doc_id,
        "doc_exists": doc_exists,
        "doc_title_match": doc_title_match,
        "doc_passage_match": doc_passage_match,
        "passage_offset_match": passage_offset_match,
        "target_category": target_cat,
        "sub_category": sub_cat,
        "has_mismatch": mismatch_flag,
        "mismatch_reasons": mismatch_reasons,
        "legal_proposition": prop,
        "statutory_context": stat_ctx
    }
    results.append(res)

print("=" * 80)
print("AUDIT RESULTS SUMMARY ACROSS ALL 30 CASES")
print("=" * 80)
mismatched_cases = [r for r in results if r["has_mismatch"] or len(r["mismatch_reasons"]) > 0]
print(f"Total cases evaluated: {len(results)}")
print(f"Cases with flags/discrepancies: {len(mismatched_cases)}")

for r in results:
    status_str = "PASS" if not r["mismatch_reasons"] else "FLAGGED"
    print(f"[{status_str}] {r['case_id']}: doc={r['doc_id']} (exists={r['doc_exists']}, title={r['doc_title_match']}, pass={r['doc_passage_match']})")
    if r["mismatch_reasons"]:
        for reason in r["mismatch_reasons"]:
            print(f"   -> {reason}")
