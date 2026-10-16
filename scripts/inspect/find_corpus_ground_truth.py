import os
import json
import re
from collections import defaultdict

CORPUS_DIR = "data/processed/aws_sc"

files = sorted([f for f in os.listdir(CORPUS_DIR) if f.endswith('.json')])

# 1. Collect title -> [doc_ids]
titles = defaultdict(list)
# 2. Collect scr -> doc_id
scrs = {}
# 3. Collect insc -> doc_id
inscs = {}

for f in files:
    doc_id = f[:-5]
    with open(os.path.join(CORPUS_DIR, f), 'r', encoding='utf-8') as fp:
        d = json.load(fp)
    title = d.get('case_title', '').strip()
    cite = d.get('citation', '').strip()
    text = d.get('full_text', '')[:600]
    
    titles[title].append(doc_id)
    if cite and "INSC" in cite:
        inscs[cite] = doc_id
    m = re.search(r'\[2024\]\s*(?:\d+\s+)?S\.?C\.?R\.?\s*\d+', text)
    if m:
        scrs[m.group(0)] = doc_id

print(f"Total documents: {len(files)}")
print(f"Available INSC citations: {len(inscs)}")
print(f"Available SCR citations: {len(scrs)}")

# Find duplicate titles (companion appeals)
companion_titles = {t: ids for t, ids in titles.items() if len(ids) > 1}
print(f"Titles with multiple companion appeals: {len(companion_titles)}")
for t, ids in list(companion_titles.items())[:10]:
    print(f"  Companion: '{t[:60]}...' -> {ids}")
