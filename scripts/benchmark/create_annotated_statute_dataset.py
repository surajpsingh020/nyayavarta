"""
Create transparently annotated statutory evaluation benchmark (Milestone 4A.1).
Extracts diverse passages from real judgments in the canonical corpus across legal domains:
Criminal, Civil, Constitutional, Commercial/Insolvency, Service, and Tax.

Includes:
- Acts (Formal and Acronyms)
- Sections & Subsections (both with governing statute and bare/ambiguous sections)
- Constitutional Articles
- Procedural Orders and Rules
- Schedules
"""
import os
import json

OUT_DIR = "evaluation/statutes"
OUT_PATH = os.path.join(OUT_DIR, "annotated_statutes_sample.json")
os.makedirs(OUT_DIR, exist_ok=True)

def build_annotated_statute_benchmark():
    samples = [
        # Passage 1: Criminal Law - Murder & Abduction (Doc 2024_10_108_125)
        {
            "sample_id": "STAT_SAMPLE_001",
            "source_doc_id": "2024_10_108_125",
            "legal_domain": "Criminal Law",
            "text_segment": "The Trial Court charged all seven accused persons for the commission of offences punishable under Sections 323, 302, 364, 449, 450, 380/34 and 120-B of the Indian Penal Code, 1860. Accused nos. 6 and 7 were distinctly charged under Sections 342, 506 read with Section 34 of IPC.",
            "gold_statutory_references": [
                {"raw_text": "Sections 323, 302, 364, 449, 450, 380/34 and 120-B of the Indian Penal Code, 1860", "reference_type": "statutory_section", "normalized": "Section 323, 302, 364, 449, 450, 380/34 and 120-B", "governing_statute": "Indian Penal Code, 1860", "is_ambiguous_provision": False},
                {"raw_text": "Indian Penal Code, 1860", "reference_type": "statute_act", "normalized": "Indian Penal Code, 1860", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Sections 342, 506", "reference_type": "statutory_section", "normalized": "Section 342, 506", "governing_statute": None, "is_ambiguous_provision": True},
                {"raw_text": "Section 34 of IPC", "reference_type": "statutory_section", "normalized": "Section 34 of IPC", "governing_statute": "IPC", "is_ambiguous_provision": False},
                {"raw_text": "IPC", "reference_type": "statute_act", "normalized": "Indian Penal Code, 1860", "governing_statute": None, "is_ambiguous_provision": False}
            ]
        },
        # Passage 2: Constitutional Law - Fundamental Rights (Doc 2024_10_1404_1447)
        {
            "sample_id": "STAT_SAMPLE_002",
            "source_doc_id": "2024_10_1404_1447",
            "legal_domain": "Constitutional Law",
            "text_segment": "The petitioners contended that the levy was violative of Article 14, Article 19(1)(g) and Article 21 of the Constitution of India. It was also argued that Article 265 prohibits the collection of taxes without authority of law.",
            "gold_statutory_references": [
                {"raw_text": "Article 14", "reference_type": "constitutional_article", "normalized": "Article 14", "governing_statute": "Constitution of India", "is_ambiguous_provision": False},
                {"raw_text": "Article 19(1)(g)", "reference_type": "constitutional_article", "normalized": "Article 19(1)(g)", "governing_statute": "Constitution of India", "is_ambiguous_provision": False},
                {"raw_text": "Article 21", "reference_type": "constitutional_article", "normalized": "Article 21", "governing_statute": "Constitution of India", "is_ambiguous_provision": False},
                {"raw_text": "Constitution of India", "reference_type": "statute_act", "normalized": "Constitution of India", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Article 265", "reference_type": "constitutional_article", "normalized": "Article 265", "governing_statute": "Constitution of India", "is_ambiguous_provision": False}
            ]
        },
        # Passage 3: PMLA & Criminal Procedure - Bail & Incarceration (Doc 2024_8_1061_1085)
        {
            "sample_id": "STAT_SAMPLE_003",
            "source_doc_id": "2024_8_1061_1085",
            "legal_domain": "Financial Crime / Bail",
            "text_segment": "Whether the claim was rejected applying the triple test contemplated under Section 45, Prevention of Money Laundering Act, 2002. Right to bail should be read into Section 439, Code of Criminal Procedure, 1973 and Section 45 of the PMLA.",
            "gold_statutory_references": [
                {"raw_text": "Section 45, Prevention of Money Laundering Act, 2002", "reference_type": "statutory_section", "normalized": "Section 45", "governing_statute": "Prevention of Money Laundering Act, 2002", "is_ambiguous_provision": False},
                {"raw_text": "Prevention of Money Laundering Act, 2002", "reference_type": "statute_act", "normalized": "Prevention of Money Laundering Act, 2002", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Section 439, Code of Criminal Procedure, 1973", "reference_type": "statutory_section", "normalized": "Section 439", "governing_statute": "Code of Criminal Procedure, 1973", "is_ambiguous_provision": False},
                {"raw_text": "Code of Criminal Procedure, 1973", "reference_type": "statute_act", "normalized": "Code of Criminal Procedure, 1973", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Section 45 of the PMLA", "reference_type": "statutory_section", "normalized": "Section 45 of PMLA", "governing_statute": "PMLA", "is_ambiguous_provision": False},
                {"raw_text": "PMLA", "reference_type": "statute_act", "normalized": "Prevention of Money Laundering Act, 2002", "governing_statute": None, "is_ambiguous_provision": False}
            ]
        },
        # Passage 4: Civil Procedure - Execution Petition (Doc 2024_10_1359_1370)
        {
            "sample_id": "STAT_SAMPLE_004",
            "source_doc_id": "2024_10_1359_1370",
            "legal_domain": "Civil Procedure",
            "text_segment": "Application was filed under Order XXI Rule 97 and Order XXI Rule 99 of the Code of Civil Procedure, 1908 resisting delivery of possession. The High Court also considered Section 47 of CPC.",
            "gold_statutory_references": [
                {"raw_text": "Order XXI Rule 97", "reference_type": "procedural_order_rule", "normalized": "Order XXI Rule 97", "governing_statute": "Code of Civil Procedure, 1908", "is_ambiguous_provision": False},
                {"raw_text": "Order XXI Rule 99", "reference_type": "procedural_order_rule", "normalized": "Order XXI Rule 99", "governing_statute": "Code of Civil Procedure, 1908", "is_ambiguous_provision": False},
                {"raw_text": "Code of Civil Procedure, 1908", "reference_type": "statute_act", "normalized": "Code of Civil Procedure, 1908", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Section 47 of CPC", "reference_type": "statutory_section", "normalized": "Section 47 of CPC", "governing_statute": "CPC", "is_ambiguous_provision": False},
                {"raw_text": "CPC", "reference_type": "statute_act", "normalized": "Code of Civil Procedure, 1908", "governing_statute": None, "is_ambiguous_provision": False}
            ]
        },
        # Passage 5: Insolvency & Commercial Law (Doc 2024_10_1371_1380)
        {
            "sample_id": "STAT_SAMPLE_005",
            "source_doc_id": "2024_10_1371_1380",
            "legal_domain": "Commercial / Insolvency",
            "text_segment": "Proceedings initiated under Section 7 of the Insolvency and Bankruptcy Code, 2016 for resolution of debt. Moratorium declared under Section 14 of IBC. The personal guarantor invoked Section 60(2).",
            "gold_statutory_references": [
                {"raw_text": "Section 7 of the Insolvency and Bankruptcy Code, 2016", "reference_type": "statutory_section", "normalized": "Section 7 of Insolvency and Bankruptcy Code", "governing_statute": "Insolvency and Bankruptcy Code, 2016", "is_ambiguous_provision": False},
                {"raw_text": "Insolvency and Bankruptcy Code, 2016", "reference_type": "statute_act", "normalized": "Insolvency and Bankruptcy Code, 2016", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Section 14 of IBC", "reference_type": "statutory_section", "normalized": "Section 14 of IBC", "governing_statute": "IBC", "is_ambiguous_provision": False},
                {"raw_text": "IBC", "reference_type": "statute_act", "normalized": "Insolvency and Bankruptcy Code, 2016", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Section 60(2)", "reference_type": "statutory_section", "normalized": "Section 60(2)", "governing_statute": None, "is_ambiguous_provision": True}
            ]
        },
        # Passage 6: Constitutional Schedules & Disqualification (Doc 2024_12_617_626)
        {
            "sample_id": "STAT_SAMPLE_006",
            "source_doc_id": "2024_12_617_626",
            "legal_domain": "Constitutional Law",
            "text_segment": "Powers exercised under Article 341 and Article 342 of the Constitution. References to the Fifth Schedule and Sixth Schedule were examined regarding tribal areas, alongside the Tenth Schedule disqualification provisions.",
            "gold_statutory_references": [
                {"raw_text": "Article 341", "reference_type": "constitutional_article", "normalized": "Article 341", "governing_statute": "Constitution of India", "is_ambiguous_provision": False},
                {"raw_text": "Article 342", "reference_type": "constitutional_article", "normalized": "Article 342", "governing_statute": "Constitution of India", "is_ambiguous_provision": False},
                {"raw_text": "Constitution", "reference_type": "statute_act", "normalized": "Constitution of India", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Fifth Schedule", "reference_type": "statutory_schedule", "normalized": "Fifth Schedule", "governing_statute": "Constitution of India", "is_ambiguous_provision": False},
                {"raw_text": "Sixth Schedule", "reference_type": "statutory_schedule", "normalized": "Sixth Schedule", "governing_statute": "Constitution of India", "is_ambiguous_provision": False},
                {"raw_text": "Tenth Schedule", "reference_type": "statutory_schedule", "normalized": "Tenth Schedule", "governing_statute": "Constitution of India", "is_ambiguous_provision": False}
            ]
        },
        # Passage 7: Limitation Act & Ambiguous Sections (Doc 2024_10_1462_1474)
        {
            "sample_id": "STAT_SAMPLE_007",
            "source_doc_id": "2024_10_1462_1474",
            "legal_domain": "Commercial / Limitation",
            "text_segment": "Barred under Section 3 of the Limitation Act, 1963. The appellant sought extension under Section 5 and Section 14. Further argued that Section 18 acknowledges liability.",
            "gold_statutory_references": [
                {"raw_text": "Section 3 of the Limitation Act, 1963", "reference_type": "statutory_section", "normalized": "Section 3 of Limitation Act", "governing_statute": "Limitation Act, 1963", "is_ambiguous_provision": False},
                {"raw_text": "Limitation Act, 1963", "reference_type": "statute_act", "normalized": "Limitation Act, 1963", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Section 5", "reference_type": "statutory_section", "normalized": "Section 5", "governing_statute": None, "is_ambiguous_provision": True},
                {"raw_text": "Section 14", "reference_type": "statutory_section", "normalized": "Section 14", "governing_statute": None, "is_ambiguous_provision": True},
                {"raw_text": "Section 18", "reference_type": "statutory_section", "normalized": "Section 18", "governing_statute": None, "is_ambiguous_provision": True}
            ]
        },
        # Passage 8: Procedural Rules & Pleadings (Doc 2024_9_999_1010)
        {
            "sample_id": "STAT_SAMPLE_008",
            "source_doc_id": "2024_9_999_1010",
            "legal_domain": "Civil Procedure / Insurance",
            "text_segment": "Pleadings must conform to Order 6 Rule 4 of the Code of Civil Procedure. Claim petition filed under Section 166 of the Motor Vehicles Act, 1988 read with Section 173 of the Code of Criminal Procedure, 1973.",
            "gold_statutory_references": [
                {"raw_text": "Order 6 Rule 4", "reference_type": "procedural_order_rule", "normalized": "Order 6 Rule 4", "governing_statute": "Code of Civil Procedure, 1908", "is_ambiguous_provision": False},
                {"raw_text": "Code of Civil Procedure", "reference_type": "statute_act", "normalized": "Code of Civil Procedure, 1908", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Section 166 of the Motor Vehicles Act, 1988", "reference_type": "statutory_section", "normalized": "Section 166 of Motor Vehicles Act", "governing_statute": "Motor Vehicles Act, 1988", "is_ambiguous_provision": False},
                {"raw_text": "Motor Vehicles Act, 1988", "reference_type": "statute_act", "normalized": "Motor Vehicles Act, 1988", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Section 173 of the Code of Criminal Procedure, 1973", "reference_type": "statutory_section", "normalized": "Section 173 of Code of Criminal Procedure", "governing_statute": "Code of Criminal Procedure, 1973", "is_ambiguous_provision": False},
                {"raw_text": "Code of Criminal Procedure, 1973", "reference_type": "statute_act", "normalized": "Code of Criminal Procedure, 1973", "governing_statute": None, "is_ambiguous_provision": False}
            ]
        },
        # Passage 9: Criminal Procedure & Sentence Remission (Doc 2024_10_1448_1461)
        {
            "sample_id": "STAT_SAMPLE_009",
            "source_doc_id": "2024_10_1448_1461",
            "legal_domain": "Criminal Law / Remission",
            "text_segment": "Power to remit sentence exercised under Section 432 and Section 433A of the Code of Criminal Procedure, 1973. Offence was under Section 302 IPC. The State policy framed under Article 161 was also cited.",
            "gold_statutory_references": [
                {"raw_text": "Section 432", "reference_type": "statutory_section", "normalized": "Section 432", "governing_statute": "Code of Criminal Procedure, 1973", "is_ambiguous_provision": False},
                {"raw_text": "Section 433A of the Code of Criminal Procedure, 1973", "reference_type": "statutory_section", "normalized": "Section 433A of Code of Criminal Procedure", "governing_statute": "Code of Criminal Procedure, 1973", "is_ambiguous_provision": False},
                {"raw_text": "Code of Criminal Procedure, 1973", "reference_type": "statute_act", "normalized": "Code of Criminal Procedure, 1973", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Section 302", "reference_type": "statutory_section", "normalized": "Section 302", "governing_statute": "IPC", "is_ambiguous_provision": False},
                {"raw_text": "IPC", "reference_type": "statute_act", "normalized": "Indian Penal Code, 1860", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Article 161", "reference_type": "constitutional_article", "normalized": "Article 161", "governing_statute": "Constitution of India", "is_ambiguous_provision": False}
            ]
        },
        # Passage 10: Special Statutes - Negotiable Instruments & Contract (Doc 2024_8_847_853)
        {
            "sample_id": "STAT_SAMPLE_010",
            "source_doc_id": "2024_8_847_853",
            "legal_domain": "Commercial / Contract",
            "text_segment": "Notice issued under Section 138 of the Negotiable Instruments Act, 1881. In addition, relief was claimed under Section 10 of the Specific Relief Act, 1963 and damages under Section 73 of the Contract Act, 1872.",
            "gold_statutory_references": [
                {"raw_text": "Section 138 of the Negotiable Instruments Act, 1881", "reference_type": "statutory_section", "normalized": "Section 138 of Negotiable Instruments Act", "governing_statute": "Negotiable Instruments Act, 1881", "is_ambiguous_provision": False},
                {"raw_text": "Negotiable Instruments Act, 1881", "reference_type": "statute_act", "normalized": "Negotiable Instruments Act, 1881", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Section 10 of the Specific Relief Act, 1963", "reference_type": "statutory_section", "normalized": "Section 10 of Specific Relief Act", "governing_statute": "Specific Relief Act, 1963", "is_ambiguous_provision": False},
                {"raw_text": "Specific Relief Act, 1963", "reference_type": "statute_act", "normalized": "Specific Relief Act, 1963", "governing_statute": None, "is_ambiguous_provision": False},
                {"raw_text": "Section 73 of the Contract Act, 1872", "reference_type": "statutory_section", "normalized": "Section 73 of Contract Act", "governing_statute": "Contract Act, 1872", "is_ambiguous_provision": False},
                {"raw_text": "Contract Act, 1872", "reference_type": "statute_act", "normalized": "Contract Act, 1872", "governing_statute": None, "is_ambiguous_provision": False}
            ]
        }
    ]

    total_refs = sum(len(s["gold_statutory_references"]) for s in samples)
    type_counts = {}
    ambig_count = 0
    for s in samples:
        for r in s["gold_statutory_references"]:
            t = r["reference_type"]
            type_counts[t] = type_counts.get(t, 0) + 1
            if r.get("is_ambiguous_provision"):
                ambig_count += 1

    benchmark_data = {
        "benchmark_version": "1.0.0",
        "benchmark_name": "NyayaVarta Statutory Extraction Gold Benchmark",
        "description": "Transparently annotated statutory references sample from Supreme Court judgments across 6 legal domains.",
        "legal_disclosure": (
            "DISCLAIMER: Extracted statutory mentions indicate textual references within judicial opinions. "
            "They do NOT establish or imply that a provision currently governs the case, was applied by the court as the ratio decidendi, "
            "or remains in force/un-amended under contemporary Indian law."
        ),
        "provenance": {
            "annotator": "Internal engineering curation and corpus cross-verification",
            "independent_legal_review": False,
            "passages_count": len(samples),
            "total_statutory_references": total_refs,
            "type_distribution": type_counts,
            "ambiguous_provisions_count": ambig_count
        },
        "samples": samples
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=4)

    print(f"Created statutory gold benchmark at {OUT_PATH}:")
    print(f"  Passages: {len(samples)}")
    print(f"  Total references: {total_refs}")
    print(f"  Type breakdown: {type_counts}")
    print(f"  Ambiguous bare provisions: {ambig_count}")
    return benchmark_data

if __name__ == "__main__":
    build_annotated_statute_benchmark()
