"""
Generates the versioned gold evaluation dataset for Milestone 11 Task 7:
`evaluation/statutes/milestone11_statute_gold.json`

Contains 60 developer-curated statutory section mentions spanning 4 critical attribution scenarios:
1. Explicit Inline Attribution (20 items): Section with explicit trailing or inline Act.
2. Conservative Intra-Paragraph Inheritance (15 items): Unambiguous single preceding Act in same paragraph.
3. Ambiguous Multi-Act Contexts (15 items): Multiple candidate Acts coexisting in paragraph.
4. Correctly Unresolved References (10 items): Bare sections without local Act context or separated by paragraph breaks.
"""
import os
import json

OUTPUT_PATH = "evaluation/statutes/milestone11_statute_gold.json"

def create_statute_gold():
    records = []

    # 1. Explicit Inline References (20 items)
    explicit_samples = [
        ("Section 302 of the Indian Penal Code, 1860", "302", "Indian Penal Code, 1860", "explicit"),
        ("Section 307 IPC", "307", "Indian Penal Code, 1860", "explicit"),
        ("Section 438 of the Code of Criminal Procedure, 1973", "438", "Code of Criminal Procedure, 1973", "explicit"),
        ("Section 482 CrPC", "482", "Code of Criminal Procedure, 1973", "explicit"),
        ("Section 34 of the Arbitration and Conciliation Act, 1996", "34", "Arbitration and Conciliation Act, 1996", "explicit"),
        ("Section 37 of the Arbitration Act", "37", "Arbitration and Conciliation Act, 1996", "explicit"),
        ("Section 138 of the Negotiable Instruments Act, 1881", "138", "Negotiable Instruments Act, 1881", "explicit"),
        ("Section 141 NI Act", "141", "Negotiable Instruments Act, 1881", "explicit"),
        ("Section 17(5)(d) of the Central Goods and Services Tax Act, 2017", "17(5)(d)", "Central Goods and Services Tax Act, 2017", "explicit"),
        ("Section 16 CGST Act", "16", "Central Goods and Services Tax Act, 2017", "explicit"),
        ("Section 45 of the Prevention of Money Laundering Act, 2002", "45", "Prevention of Money Laundering Act, 2002", "explicit"),
        ("Section 3 PMLA", "3", "Prevention of Money Laundering Act, 2002", "explicit"),
        ("Section 7 of the Insolvency and Bankruptcy Code, 2016", "7", "Insolvency and Bankruptcy Code, 2016", "explicit"),
        ("Section 9 IBC", "9", "Insolvency and Bankruptcy Code, 2016", "explicit"),
        ("Section 5 of the Limitation Act, 1963", "5", "Limitation Act, 1963", "explicit"),
        ("Section 14 Limitation Act", "14", "Limitation Act, 1963", "explicit"),
        ("Section 54 of the Transfer of Property Act, 1882", "54", "Transfer of Property Act, 1882", "explicit"),
        ("Section 100 CPC", "100", "Code of Civil Procedure, 1908", "explicit"),
        ("Section 13 of the SARFAESI Act", "13", "Securitisation and Reconstruction of Financial Assets and Enforcement of Security Interest Act, 2002", "explicit"),
        ("Section 20 of the Specific Relief Act, 1963", "20", "Specific Relief Act, 1963", "explicit")
    ]
    for raw, sec, act, atype in explicit_samples:
        text = f"The proceedings involved {raw} in the High Court."
        records.append({
            "mention_id": f"STAT_GOLD_{len(records)+1:03d}",
            "raw_text": raw,
            "section_number": sec,
            "sample_document_text": text,
            "gold_attribution_type": "explicit",
            "gold_governing_statute": act,
            "test_category": "explicit_inline",
            "provenance": "developer_curated"
        })

    # 2. Conservative Intra-Paragraph Inheritance (15 items)
    inherited_samples = [
        ("Arbitration and Conciliation Act, 1996", "Section 34", "34", "Arbitration and Conciliation Act, 1996", "The petition arose under the Arbitration and Conciliation Act, 1996. The award was challenged under Section 34."),
        ("Arbitration and Conciliation Act, 1996", "Section 11(6)", "11(6)", "Arbitration and Conciliation Act, 1996", "An application was filed under the Arbitration and Conciliation Act, 1996. The Chief Justice was moved under Section 11(6)."),
        ("Prevention of Money Laundering Act, 2002", "Section 45", "45", "Prevention of Money Laundering Act, 2002", "Prosecution was initiated under the Prevention of Money Laundering Act, 2002. Bail was sought under Section 45."),
        ("Prevention of Money Laundering Act, 2002", "Section 19", "19", "Prevention of Money Laundering Act, 2002", "Investigating officers acted under the Prevention of Money Laundering Act, 2002. Arrest was effected under Section 19."),
        ("Central Goods and Services Tax Act, 2017", "Section 17(5)(d)", "17(5)(d)", "Central Goods and Services Tax Act, 2017", "The assessee claimed input tax credit under the Central Goods and Services Tax Act, 2017. Revenue denied credit under Section 17(5)(d)."),
        ("Insolvency and Bankruptcy Code, 2016", "Section 7", "7", "Insolvency and Bankruptcy Code, 2016", "Financial creditors moved under the Insolvency and Bankruptcy Code, 2016. Admission was ordered under Section 7."),
        ("Insolvency and Bankruptcy Code, 2016", "Section 31", "31", "Insolvency and Bankruptcy Code, 2016", "Resolution plan approved under the Insolvency and Bankruptcy Code, 2016. Adjudicating authority sanctioned under Section 31."),
        ("Limitation Act, 1963", "Section 5", "5", "Limitation Act, 1963", "The appeal was barred under the Limitation Act, 1963. Condonation of delay was sought under Section 5."),
        ("Limitation Act, 1963", "Section 14", "14", "Limitation Act, 1963", "Exclusion of time was argued under the Limitation Act, 1963. The appellant relied upon Section 14."),
        ("Negotiable Instruments Act, 1881", "Section 138", "138", "Negotiable Instruments Act, 1881", "Complaint was instituted under the Negotiable Instruments Act, 1881. Cheque bounce was prosecuted under Section 138."),
        ("Code of Criminal Procedure, 1973", "Section 438", "438", "Code of Criminal Procedure, 1973", "Anticipatory bail petition under the Code of Criminal Procedure, 1973. High Court rejected relief under Section 438."),
        ("Code of Criminal Procedure, 1973", "Section 311", "311", "Code of Criminal Procedure, 1973", "Witness examination under the Code of Criminal Procedure, 1973. Summons issued under Section 311."),
        ("Indian Penal Code, 1860", "Section 302", "302", "Indian Penal Code, 1860", "Charges framed under the Indian Penal Code, 1860. The trial court convicted under Section 302."),
        ("Indian Penal Code, 1860", "Section 420", "420", "Indian Penal Code, 1860", "Allegations of cheating under the Indian Penal Code, 1860. Charge sheet filed under Section 420."),
        ("Motor Vehicles Act, 1988", "Section 166", "166", "Motor Vehicles Act, 1988", "Claim petition filed under the Motor Vehicles Act, 1988. Compensation awarded under Section 166.")
    ]
    for act, raw_sec, sec_num, gold_act, text in inherited_samples:
        records.append({
            "mention_id": f"STAT_GOLD_{len(records)+1:03d}",
            "raw_text": raw_sec,
            "section_number": sec_num,
            "sample_document_text": text,
            "gold_attribution_type": "inherited",
            "gold_governing_statute": gold_act,
            "test_category": "intra_paragraph_inherited",
            "provenance": "developer_curated"
        })

    # 3. Ambiguous Multi-Act Contexts (15 items)
    ambiguous_samples = [
        ("The appellant was charged under the Indian Penal Code, 1860 and Code of Criminal Procedure, 1973. Application filed under Section 389.", "Section 389", "389"),
        ("Charges under the Indian Penal Code, 1860 and the Prevention of Corruption Act, 1988 were investigated. Relief was claimed under Section 13.", "Section 13", "13"),
        ("Proceedings under the Companies Act, 2013 and the Insolvency and Bankruptcy Code, 2016 were pending. Action taken under Section 9.", "Section 9", "9"),
        ("Matters under the Arbitration and Conciliation Act, 1996 and the Commercial Courts Act, 2015 were listed. Appeal preferred under Section 37.", "Section 37", "37"),
        ("Provisions of the Limitation Act, 1963 and the Code of Civil Procedure, 1908 were considered. The court exercised powers under Section 14.", "Section 14", "14"),
        ("Under the Indian Penal Code, 1860 and the Protection of Children from Sexual Offences Act, 2012 offences were alleged. Trial conducted under Section 6.", "Section 6", "6"),
        ("Claims under the Transfer of Property Act, 1882 and the Specific Relief Act, 1963 were argued. Suit framed under Section 10.", "Section 10", "10"),
        ("Offences under the Indian Penal Code, 1860 and Narcotic Drugs and Psychotropic Substances Act, 1985 were registered. Accused arrested under Section 50.", "Section 50", "50"),
        ("Inquiries under the Central Goods and Services Tax Act, 2017 and Customs Act, 1962 were conducted. Notice issued under Section 73.", "Section 73", "73"),
        ("Under the Indian Penal Code, 1860 and Unlawful Activities (Prevention) Act, 1967 charges were filed. Bail rejected under Section 43D.", "Section 43D", "43D"),
        ("Petitions under the Code of Civil Procedure, 1908 and the Constitution of India were considered. Order passed under Section 151.", "Section 151", "151"),
        ("Statutes including the Competition Act, 2002 and Companies Act, 2013 were reviewed. Inquiry initiated under Section 26.", "Section 26", "26"),
        ("Under the Indian Evidence Act, 1872 and the Code of Criminal Procedure, 1973 evidence was taken. Statement recorded under Section 164.", "Section 164", "164"),
        ("Provisions under the Mines and Minerals (Development and Regulation) Act, 1957 and Environment (Protection) Act, 1986 applied. Royalty demanded under Section 9.", "Section 9", "9"),
        ("Under the Negotiable Instruments Act, 1881 and Code of Criminal Procedure, 1973 trial proceeded. Compensation ordered under Section 357.", "Section 357", "357")
    ]
    for text, raw_sec, sec_num in ambiguous_samples:
        records.append({
            "mention_id": f"STAT_GOLD_{len(records)+1:03d}",
            "raw_text": raw_sec,
            "section_number": sec_num,
            "sample_document_text": text,
            "gold_attribution_type": "ambiguous",
            "gold_governing_statute": None,
            "test_category": "multi_act_ambiguous",
            "provenance": "developer_curated"
        })

    # 4. Correctly Unresolved References / Collision Protection (10 items)
    unresolved_samples = [
        ("Paragraph 1: Motor Vehicles Act, 1988 was mentioned.\n\nParagraph 2: Relief sought under Section 5.", "Section 5", "5"),
        ("Paragraph 1: Land Acquisition Act, 1894 applied.\n\nParagraph 2: Objections under Section 9.", "Section 9", "9"),
        ("Paragraph 1: Indian Penal Code, 1860.\n\nParagraph 2: Application under Section 14.", "Section 14", "14"),
        ("Paragraph 1: Companies Act, 2013.\n\nParagraph 2: Arbitrator appointed under Section 34.", "Section 34", "34"),
        ("Paragraph 1: Negotiable Instruments Act, 1881.\n\nParagraph 2: Second appeal admitted under Section 100.", "Section 100", "100"),
        ("In the present appeal, the learned judge examined Section 302 without any Act mentioned.", "Section 302", "302"),
        ("The High Court rejected the application under Section 438 in limine.", "Section 438", "438"),
        ("The petition was moved under Section 482 on procedural grounds.", "Section 482", "482"),
        ("Relief claimed under Section 138 alone.", "Section 138", "138"),
        ("Powers exercised under Section 151 in the trial court.", "Section 151", "151")
    ]
    for text, raw_sec, sec_num in unresolved_samples:
        records.append({
            "mention_id": f"STAT_GOLD_{len(records)+1:03d}",
            "raw_text": raw_sec,
            "section_number": sec_num,
            "sample_document_text": text,
            "gold_attribution_type": "unresolved",
            "gold_governing_statute": None,
            "test_category": "unresolved_collision_protection",
            "provenance": "developer_curated"
        })

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)

    print(f"Created gold statutory attribution dataset: {OUTPUT_PATH}")
    print(f"Total evaluated records: {len(records)}")
    return records

if __name__ == "__main__":
    create_statute_gold()
