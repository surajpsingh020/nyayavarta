import json
import re

cites_path = 'data/processed/extraction/v1/case_citations.jsonl'
res_path = 'data/processed/extraction/v1/resolved_entities.jsonl'
count = 0
found_pre2024 = 0

with open(cites_path, 'r', encoding='utf-8') as fc, open(res_path, 'r', encoding='utf-8') as fr:
    for lc, lr in zip(fc, fr):
        c = json.loads(lc)
        r = json.loads(lr)
        if r.get('resolution_status') == 'resolved' and not r.get('is_self_citation'):
            count += 1
            ctx = c.get('mention_context', '')
            raw = c.get('raw_text', '')
            method = r.get('match_method')
            years = [int(y) for y in re.findall(r'\b(19\d\d|20[0-1]\d|202[0-3])\b', ctx)]
            if years:
                found_pre2024 += 1
                if found_pre2024 <= 5:
                    print(f'Match {count} [{method}]: raw="{raw}" -> target={r.get("resolved_document_id")} years_in_ctx={years}')
                    print(f'  ctx: {ctx[:120]}...\n')

print(f'Total cross-doc: {count}, Pre-2024 years in context: {found_pre2024} ({found_pre2024/count*100:.2f}%)')
