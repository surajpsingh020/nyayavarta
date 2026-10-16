import os
import json
import re

files = [f for f in os.listdir('data/processed/aws_sc') if f.endswith('.json')][:10]
for fname in files:
    with open(os.path.join('data/processed/aws_sc', fname), 'r', encoding='utf-8') as f:
        d = json.load(f)
    txt = d['full_text']
    doc_id = d['document_id']
    
    scc = re.findall(r'([^.\n]{0,80}(?:\d{4}\s+\d+\s+SCC|\(\d{4}\)\s+\d+\s+SCC|\d{4}\s+SCC\s+OnLine)[^.\n]{0,80})', txt)
    air = re.findall(r'([^.\n]{0,80}AIR\s+\d{4}\s+SC\s+\d+[^.\n]{0,80})', txt)
    sec = re.findall(r'([^.\n]{0,80}(?:Section|u/s|s\.)\s+\d+[^.\n]{0,80})', txt)
    art = re.findall(r'([^.\n]{0,80}Article\s+\d+[^.\n]{0,80})', txt)
    case = re.findall(r'([A-Z][A-Za-z0-9\.\s]{2,40}\s+(?:v\.|vs\.|versus)\s+[A-Z][A-Za-z0-9\.\s]{2,40})', txt)
    
    if scc or air or sec or art or case:
        print(f"=== Doc: {doc_id} ({d.get('case_title')}) ===")
        if scc:
            print("  SCC:", scc[0].strip().replace('\n', ' '))
        if air:
            print("  AIR:", air[0].strip().replace('\n', ' '))
        if sec:
            print("  SEC:", sec[0].strip().replace('\n', ' '))
        if art:
            print("  ART:", art[0].strip().replace('\n', ' '))
        if case:
            print("  CASE:", case[0].strip().replace('\n', ' '))
