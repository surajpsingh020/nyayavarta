import sys, os
sys.path.insert(0, os.path.abspath("."))

from services.extraction.statute_extractor import StatuteExtractor
from services.extraction.statute_resolver_v2 import StatuteResolverV2

ext = StatuteExtractor()
res = StatuteResolverV2()

text = (
    "Paragraph 1: The proceedings arose under the Arbitration and Conciliation Act, 1996.\n"
    "The High Court considered the objections filed under Section 34.\n\n"
    "Paragraph 2: The appellant was charged under the Indian Penal Code, 1860 and the Code of Criminal Procedure, 1973.\n"
    "An application was preferred under Section 389.\n\n"
    "Paragraph 3: Shorn of details, the question relates to the Motor Vehicles Act, 1988.\n\n"
    "Paragraph 4: In the present appeal, relief was sought under Section 5.\n\n"
    "Paragraph 5: The respondent was prosecuted under Section 138 of the Negotiable Instruments Act, 1881."
)

acts = ext.extract_acts(text, "doc_test")
secs = ext.extract_sections(text, "doc_test")

resolved = res.resolve_document_statutes(text, "doc_test", extracted_sections=secs)

for s in resolved:
    num = s['components']['section_numbers']
    gov = s['components']['governing_statute']
    atype = s.get('attribution_type')
    asrc = s.get('attribution_source')
    print(f"Section: {num:15} -> Gov: {str(gov):40} | Type: {atype:10} | Src: {asrc}")
