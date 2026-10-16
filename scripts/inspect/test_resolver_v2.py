import sys, os
sys.path.insert(0, os.path.abspath("."))
from services.extraction.entity_resolver_v2 import EntityResolverV2
r = EntityResolverV2()

cases = [
    {
        'citation_type': 'case_title',
        'raw_text': 'In State of H.P. v. Gujarat Ambuja Cement Ltd',
        'normalized_citation': 'State of H.P. v. Gujarat Ambuja Cement Ltd',
        'mention_context': 'In State of H.P. v. Gujarat Ambuja Cement Ltd, (2005) 6 SCC 499, this Court held...',
        'source_doc_id': '2024_10_1381_1403'
    },
    {
        'citation_type': 'case_title',
        'raw_text': 'Satender Kumar Antil v. Central Bureau of Investigation',
        'normalized_citation': 'Satender Kumar Antil v. Central Bureau of Investigation',
        'mention_context': 'In Satender Kumar Antil v. Central Bureau of Investigation (2022) 10 SCC 51, guidelines were issued...',
        'source_doc_id': '2024_10_393_410'
    },
    {
        'citation_type': 'case_title',
        'raw_text': 'Karan Singh v. Union of India',
        'normalized_citation': 'Karan Singh v. Union of India',
        'mention_context': 'Karan Singh v. Union of India [1997] Supp. SCR 12, was referred to.',
        'source_doc_id': '2024_10_1709_1725'
    },
    {
        'citation_type': 'scr',
        'raw_text': '[2024] 10 S.C.R. 108',
        'normalized_citation': '[2024] 10 SCR 108',
        'components': {'year': 2024, 'vol': '10', 'page': '108'},
        'mention_context': 'Reported at [2024] 10 S.C.R. 108',
        'source_doc_id': 'other_doc'
    },
    {
        'citation_type': 'neutral_insc',
        'raw_text': '2024 INSC 735',
        'normalized_citation': '2024 INSC 735',
        'components': {'year': 2024, 'number': 735},
        'mention_context': 'Judgment in 2024 INSC 735',
        'source_doc_id': 'other_doc'
    }
]

for c in cases:
    res = r.resolve_citation(c)
    print(f"Mention: {c['raw_text']}")
    print(f"  Status: {res['resolution_status']} | Method: {res['match_method']} | Target: {res['resolved_document_id']}")
    print(f"  Reason: {res['resolution_reason']}\n")
