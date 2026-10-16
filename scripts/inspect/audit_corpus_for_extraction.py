"""
Corpus audit for legal citation and entity extraction (Milestone 4A).
Inspects all 782 canonical documents in data/processed/aws_sc/
"""
import os
import json
import re
import statistics

PROCESSED_DIR = "data/processed/aws_sc"


def audit_corpus():
    files = [f for f in os.listdir(PROCESSED_DIR) if f.endswith('.json')]
    total_docs = len(files)
    
    unique_ids = set()
    text_lengths = []
    empty_text_docs = []
    short_text_docs = []  # < 1000 chars
    
    field_counts = {
        "case_title": 0,
        "citation": 0,
        "decision_date": 0,
        "judges": 0,
        "case_number": 0,
        "disposition": 0,
        "source_url": 0,
        "provenance": 0,
        "license": 0
    }
    
    # Citation pattern counters in full text
    citation_patterns = {
        "scc": re.compile(r'\b(?:\(\d{4}\)|\d{4})\s+\d+\s+SCC(?:\s+\(Cri\)|\s+\(L&S\))?\s+\d+\b|\b\d{4}\s+SCC\s+OnLine\s+SC\s+\d+\b', re.IGNORECASE),
        "air": re.compile(r'\bAIR\s+\d{4}\s+SC\s+\d+\b', re.IGNORECASE),
        "scr": re.compile(r'\[\d{4}\]\s+\d+\s+S\.?C\.?R\.?\s+\d+|\(\d{4}\)\s+\d+\s+SCR\s+\d+', re.IGNORECASE),
        "insc": re.compile(r'\b\d{4}\s+INSC\s+\d+\b', re.IGNORECASE),
        "v_versus": re.compile(r'\b[A-Z][A-Za-z0-9\.\,\'\s\(\)\@\-]{2,50}\s+(?:v\.|vs\.?|versus)\s+[A-Z][A-Za-z0-9\.\,\'\s\(\)\@\-]{2,50}\b'),
        "section": re.compile(r'\b(?:Section|Sec\.|s\.)\s+\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*', re.IGNORECASE),
        "article": re.compile(r'\b(?:Article|Art\.)\s+\d+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*', re.IGNORECASE),
        "act": re.compile(r'\b[A-Z][A-Za-z\s]{3,40}(?:Act|Code|Rules|Regulations|Order),\s+\d{4}\b'),
        "order_rule": re.compile(r'\bOrder\s+[IVXLCDM0-9]+\s+Rule\s+\d+\b', re.IGNORECASE),
        "schedule": re.compile(r'\b(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth|\d+th)\s+Schedule\b', re.IGNORECASE)
    }
    
    pattern_matches = {k: 0 for k in citation_patterns}
    docs_with_pattern = {k: 0 for k in citation_patterns}
    
    # Artifact checks
    ocr_artifacts_count = 0
    headnote_count = 0
    coram_asterisk_count = 0
    
    for fname in files:
        fpath = os.path.join(PROCESSED_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            doc = json.load(f)
            
        doc_id = doc.get("document_id")
        unique_ids.add(doc_id)
        
        # Metadata checks
        for field in field_counts:
            val = doc.get(field)
            if val is not None and str(val).strip() != "":
                field_counts[field] += 1
                
        # Text checks
        text = doc.get("full_text", "")
        text_len = len(text)
        text_lengths.append(text_len)
        
        if text_len == 0:
            empty_text_docs.append(doc_id)
        elif text_len < 1000:
            short_text_docs.append((doc_id, text_len))
            
        # Pattern scanning
        for pat_name, pat_regex in citation_patterns.items():
            matches = pat_regex.findall(text)
            if matches:
                pattern_matches[pat_name] += len(matches)
                docs_with_pattern[pat_name] += 1
                
        # Known artifacts
        if "†Headnotes prepared by" in text or "Headnotes prepared by" in text:
            headnote_count += 1
        if "JJ.*" in text or "J.*" in text or "* JJ" in text or "*, JJ" in text:
            coram_asterisk_count += 1
        if re.search(r'[^\x00-\x7F\u0900-\u097F\u0A00-\u0A7F\u2010-\u2026\u2018-\u201D]', text):
            ocr_artifacts_count += 1

    audit_summary = {
        "total_documents": total_docs,
        "unique_document_ids": len(unique_ids),
        "text_statistics": {
            "empty_documents": len(empty_text_docs),
            "empty_document_ids": empty_text_docs,
            "short_documents_under_1000_chars": len(short_text_docs),
            "min_length_chars": min(text_lengths) if text_lengths else 0,
            "max_length_chars": max(text_lengths) if text_lengths else 0,
            "mean_length_chars": round(statistics.mean(text_lengths), 1) if text_lengths else 0,
            "median_length_chars": round(statistics.median(text_lengths), 1) if text_lengths else 0
        },
        "metadata_completeness": {
            k: {
                "present_count": v,
                "percentage": round((v / total_docs) * 100, 2)
            } for k, v in field_counts.items()
        },
        "citation_pattern_scan": {
            k: {
                "total_occurrences": pattern_matches[k],
                "documents_containing": docs_with_pattern[k],
                "doc_coverage_pct": round((docs_with_pattern[k] / total_docs) * 100, 2)
            } for k in citation_patterns
        },
        "detected_artifacts": {
            "headnotes_marker_present": headnote_count,
            "coram_author_asterisk_present": coram_asterisk_count,
            "non_standard_encoding_present": ocr_artifacts_count
        }
    }
    
    os.makedirs("docs/graph", exist_ok=True)
    with open("docs/graph/corpus_audit.json", "w", encoding="utf-8") as f:
        json.dump(audit_summary, f, indent=4)
        
    print(f"Audited {total_docs} documents.")
    print(f"Empty text docs: {len(empty_text_docs)}")
    print(f"Short text docs (<1000 chars): {len(short_text_docs)}")
    print(f"Mean text length: {audit_summary['text_statistics']['mean_length_chars']} chars")
    print("\nMetadata completeness:")
    for k, v in audit_summary["metadata_completeness"].items():
        print(f"  {k:15s}: {v['present_count']}/{total_docs} ({v['percentage']}%)")
    print("\nCitation patterns found:")
    for k, v in audit_summary["citation_pattern_scan"].items():
        print(f"  {k:15s}: {v['total_occurrences']:6d} mentions across {v['documents_containing']} docs ({v['doc_coverage_pct']}%)")
    print("\nArtifact counts:")
    print(f"  Headnotes markers: {headnote_count}")
    print(f"  Coram author asterisks: {coram_asterisk_count}")
    print(f"  Non-standard char presence: {ocr_artifacts_count}")

if __name__ == "__main__":
    audit_corpus()
