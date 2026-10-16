import os
import json
import re

# Load one document and inspect paragraphs and sections
doc_path = "data/processed/aws_sc/2024_10_108_125.json"
with open(doc_path, "r", encoding="utf-8") as f:
    doc = json.load(f)

text = doc.get("full_text", "")
paragraphs = re.split(r'\n\s*\n', text)
print(f"Total paragraphs in document: {len(paragraphs)}")

# Sample first 5 paragraphs
for i, p in enumerate(paragraphs[:5]):
    print(f"--- Para {i} (len={len(p)}) ---")
    print(p[:200] + "...\n")
