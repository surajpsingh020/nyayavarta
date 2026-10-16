import json
import os
import re
from collections import Counter

cites_path = "data/processed/extraction/v2/case_citations.jsonl"
res_path = "data/processed/extraction/v2/resolved_entities.jsonl"

total = 0
cross_doc = 0
cross_methods = Counter()
pre_2024_cross = 0
sample_cross = []

with open(cites_path, "r", encoding="utf-8") as fc, open(res_path, "r", encoding="utf-8") as fr:
    for lc, lr in zip(fc, fr):
        total += 1
        c = json.loads(lc)
        r = json.loads(lr)
        
        status = r.get("resolution_status")
        is_self = r.get("is_self_citation", False)
        method = r.get("match_method")
        
        if status == "resolved" and not is_self:
            cross_doc += 1
            cross_methods[method] += 1
            raw = c.get("raw_text", "")
            ctx = c.get("mention_context", "")
            comps = c.get("components", {})
            year = comps.get("year")
            # Check for pre-2024 years
            years = [int(y) for y in re.findall(r'\b(19\d\d|20[0-1]\d|202[0-3])\b', f"{raw} {ctx}")]
            if years:
                pre_2024_cross += 1
                if pre_2024_cross <= 3:
                    print(f"Pre-2024 in cross match: raw='{raw}', years={years}")
            if len(sample_cross) < 5:
                sample_cross.append((raw, method, r.get("resolved_document_id"), r.get("resolution_reason")))

print(f"\nTotal Citations: {total}")
print(f"Cross-Doc Matches: {cross_doc}")
print(f"Cross-Doc Methods: {dict(cross_methods)}")
print(f"Cross-Doc with pre-2024 years in context: {pre_2024_cross} ({pre_2024_cross/cross_doc*100:.2f}%)")
print("\nSample Cross-Doc Matches:")
for s in sample_cross:
    print(f"  Mention: {s[0]}")
    print(f"    Method: {s[1]} -> Target: {s[2]}")
    print(f"    Reason: {s[3]}")
