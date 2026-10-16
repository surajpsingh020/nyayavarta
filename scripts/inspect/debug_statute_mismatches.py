import sys, os
sys.path.insert(0, os.path.abspath("."))
import json

with open("evaluation/statutes/milestone11_statute_eval_results.json", "r") as f:
    eval_res = json.load(f)

with open("evaluation/statutes/milestone11_statute_gold.json", "r") as f:
    gold = json.load(f)

from services.extraction.statute_extractor import StatuteExtractor
from services.extraction.statute_resolver_v2 import StatuteResolverV2

ext = StatuteExtractor()
res = StatuteResolverV2()

print("Statute Mismatches:")
for item in gold:
    text = item["sample_document_text"]
    raw_secs = ext.extract_sections(text, "eval_doc")
    resolved_secs = res.resolve_document_statutes(text, "eval_doc", extracted_sections=raw_secs)
    
    matched = None
    for s in resolved_secs:
        if s["components"]["section_numbers"] == item["section_number"]:
            matched = s
            break
    if not matched and resolved_secs:
        matched = resolved_secs[0]
        
    pred_act = matched["components"].get("governing_statute") if matched else None
    pred_type = matched.get("attribution_type") if matched else "none"
    
    if pred_act != item["gold_governing_statute"] or pred_type != item["gold_attribution_type"]:
        print(f"[{item['test_category']}] raw='{item['raw_text']}' in text='{text}'")
        print(f"  Extracted sections: {[s['raw_text'] for s in raw_secs]}")
        print(f"  Gold: act={item['gold_governing_statute']}, type={item['gold_attribution_type']}")
        print(f"  Pred: act={pred_act}, type={pred_type}\n")
