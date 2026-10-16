import json
from pathlib import Path
import re

with open("evaluation/rag/milestone25_reviewer_template.jsonl", "r", encoding="utf-8") as f:
    template = [json.loads(l) for l in f if l.strip()]

with open("evaluation/rag/milestone25_frozen_mapping.json", "r", encoding="utf-8") as f:
    mapping = json.load(f)

aws_sc_dir = Path("data/processed/aws_sc")

print(f"{'Case ID':<12} | {'Cat':<35} | {'Doc ID':<18} | {'In Doc?':<8} | {'Exact Slice?':<12} | Notes")
print("-" * 115)

for t in template:
    cid = t["case_id"]
    m = mapping[cid]
    cat = m["curated_target_category"]
    doc_id = t["official_document_id"]
    passage = t["source_passage_text"]
    start, end = t["source_offsets"]["start_char"], t["source_offsets"]["end_char"]
    
    doc_file = aws_sc_dir / f"{doc_id}.json"
    in_doc = False
    exact_slice = False
    note = ""
    
    if doc_file.exists():
        with doc_file.open("r", encoding="utf-8") as df:
            d = json.load(df)
        text = d.get("full_text") or d.get("text") or ""
        
        # Exact slice check
        if start is not None and end is not None and end <= len(text):
            actual_slice = text[start:end]
            if actual_slice.strip() == passage.strip():
                exact_slice = True
                in_doc = True
        
        if not exact_slice:
            # Check normalized search
            norm_passage = re.sub(r'\s+', ' ', passage).strip()
            norm_text = re.sub(r'\s+', ' ', text).strip()
            if norm_passage[:50].lower() in norm_text.lower():
                in_doc = True
                note = "Text exists in document, but start/end offsets differ"
            else:
                note = "Passage text NOT FOUND in document (synthetic or external)"
    else:
        note = "Document file missing"
        
    print(f"{cid:<12} | {cat:<35} | {doc_id:<18} | {str(in_doc):<8} | {str(exact_slice):<12} | {note}")
