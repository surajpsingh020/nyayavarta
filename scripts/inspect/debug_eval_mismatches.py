import sys, os
sys.path.insert(0, os.path.abspath("."))
import json
from services.extraction.entity_resolver_v2 import EntityResolverV2
from services.extraction.citation_normalizer import CitationNormalizer

with open("evaluation/citations/milestone11_citation_gold.json", "r") as f:
    gold = json.load(f)

r = EntityResolverV2()
cn = CitationNormalizer()

print("Mismatches:")
for item in gold:
    raw = item["raw_text"]
    norm_rec = cn.normalize(raw)
    norm_cite = norm_rec.normalized_citation if norm_rec.parsing_status == "valid" else raw

    m = dict(item)
    m["normalized_citation"] = norm_cite

    pred = r.resolve_citation(m)
    st_match = (pred["resolution_status"] == item["gold_resolution_status"])
    tgt_match = (pred["resolved_document_id"] == item["gold_target_document_id"])

    if not st_match or not tgt_match:
        print(f"[{item['test_category']}] raw='{raw}'")
        print(f"  Gold: status={item['gold_resolution_status']}, tgt={item['gold_target_document_id']}")
        print(f"  Pred: status={pred['resolution_status']}, tgt={pred['resolved_document_id']}, method={pred['match_method']}, is_self={pred.get('is_self_citation')}\n")
