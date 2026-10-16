import json
import os
import re

files = [f for f in os.listdir('data/processed/aws_sc') if f.endswith('.json')]
print(f"Total corpus documents: {len(files)}")

neutrals = 0
scr_in_header = 0
sample_scrs = []

for f in files:
    with open(os.path.join('data/processed/aws_sc', f), 'r', encoding='utf-8') as fp:
        d = json.load(fp)
    doc_id = d.get('document_id')
    cite = d.get('citation')
    if cite:
        neutrals += 1
    # Check for SCR pattern in header (first 600 chars)
    header = d.get('full_text', '')[:600]
    m_scr = re.search(r'\[2024\]\s*(?:\(\d+\)\s*)?(?:\d+\s+)?S\.?C\.?R\.?\s*\d+', header, re.IGNORECASE)
    if m_scr:
        scr_in_header += 1
        if len(sample_scrs) < 5:
            sample_scrs.append((doc_id, m_scr.group(0)))

print(f"Documents with neutral citation field: {neutrals}/{len(files)}")
print(f"Documents with SCR citation in header: {scr_in_header}/{len(files)}")
print(f"Sample SCR citations in header: {sample_scrs}")
