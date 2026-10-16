"""
Baseline verification script for Milestone 11 Task 1.
Audits data/processed/extraction/v1/ and data/processed/graph/v1/ to verify:
1. Total citation mentions and resolution breakdown
2. Self-citations vs cross-document links
3. Matching methods
4. Statutory references with/without governing Act
5. Treatment signals
6. Graph nodes, edges, and exclusions in v1
"""
import os
import json
import sqlite3
from collections import Counter, defaultdict

EXTRACTION_V1 = "data/processed/extraction/v1"
GRAPH_V1 = "data/processed/graph/v1"

def audit_baseline():
    print("=== Auditing Extraction v1 Artifacts ===")
    
    # 1. Citations & Resolutions
    cites_path = os.path.join(EXTRACTION_V1, "case_citations.jsonl")
    res_path = os.path.join(EXTRACTION_V1, "resolved_entities.jsonl")
    
    total_citations = 0
    status_counts = Counter()
    match_method_counts = Counter()
    self_citations = 0
    cross_doc_matches = 0
    
    # Track cross-doc matches for year analysis
    cross_doc_records = []
    
    with open(cites_path, "r", encoding="utf-8") as fc, open(res_path, "r", encoding="utf-8") as fr:
        for lc, lr in zip(fc, fr):
            total_citations += 1
            c = json.loads(lc)
            r = json.loads(lr)
            
            status = r.get("resolution_status")
            status_counts[status] += 1
            
            method = r.get("match_method")
            match_method_counts[method] += 1
            
            is_self = r.get("is_self_citation", False)
            if is_self:
                self_citations += 1
            elif status == "resolved":
                cross_doc_matches += 1
                cross_doc_records.append((c, r))
                
    print(f"Total Citations: {total_citations}")
    print(f"Status Breakdown: {dict(status_counts)}")
    print(f"Self-Citations: {self_citations} ({self_citations/status_counts['resolved']*100:.2f}% of resolved)")
    print(f"Cross-Doc Matches: {cross_doc_matches} ({cross_doc_matches/status_counts['resolved']*100:.2f}% of resolved)")
    print("Match Methods:")
    for m, cnt in match_method_counts.most_common():
        print(f"  - {m}: {cnt} ({cnt/total_citations*100:.2f}%)")
        
    # Check historical year in cross-doc matches
    pre_2024_cross = 0
    for c, r in cross_doc_records:
        comps = c.get("components", {})
        year = comps.get("year")
        raw = c.get("raw_text", "")
        # Check if 19xx or 200x or 201x or 2020-2023 appears in raw or context
        if year and year < 2024:
            pre_2024_cross += 1
        elif any(f"({y})" in raw or f"[{y}]" in raw or f" {y} " in raw for y in range(1950, 2024)):
            pre_2024_cross += 1
            
    print(f"Cross-Doc Matches with pre-2024 year in mention: {pre_2024_cross} ({pre_2024_cross/cross_doc_matches*100:.2f}%)")
    
    # 2. Statutory References
    print("\n=== Auditing Statutory References v1 ===")
    stat_path = os.path.join(EXTRACTION_V1, "statutory_references.jsonl")
    total_statutes = 0
    ref_type_counts = Counter()
    sec_with_gov = 0
    sec_without_gov = 0
    
    with open(stat_path, "r", encoding="utf-8") as fs:
        for ls in fs:
            total_statutes += 1
            s = json.loads(ls)
            rtype = s.get("reference_type")
            ref_type_counts[rtype] += 1
            if rtype == "statutory_section":
                gov = s.get("components", {}).get("governing_statute")
                if gov:
                    sec_with_gov += 1
                else:
                    sec_without_gov += 1
                    
    print(f"Total Statutory References: {total_statutes}")
    print(f"Types: {dict(ref_type_counts)}")
    total_sections = ref_type_counts["statutory_section"]
    print(f"Sections with Governing Act: {sec_with_gov} ({sec_with_gov/total_sections*100:.2f}%)")
    print(f"Orphan Sections (without Act): {sec_without_gov} ({sec_without_gov/total_sections*100:.2f}%)")
    
    # 3. Treatment signals
    print("\n=== Auditing Treatment Signals in Citations ===")
    treatment_counts = Counter()
    treatment_by_status = defaultdict(Counter)
    with open(cites_path, "r", encoding="utf-8") as fc, open(res_path, "r", encoding="utf-8") as fr:
        for lc, lr in zip(fc, fr):
            c = json.loads(lc)
            r = json.loads(lr)
            sig = c.get("treatment_signal")
            if sig:
                treatment_counts[sig] += 1
                status = r.get("resolution_status")
                is_self = r.get("is_self_citation", False)
                cat = "self" if is_self else ("cross_2024" if status == "resolved" else "historical_unresolved")
                treatment_by_status[sig][cat] += 1
                
    print(f"Total Treatment Signals: {sum(treatment_counts.values())}")
    for sig, cnt in treatment_counts.most_common():
        print(f"  - {sig}: {cnt} (hist={treatment_by_status[sig]['historical_unresolved']}, self={treatment_by_status[sig]['self']}, cross={treatment_by_status[sig]['cross_2024']})")

    # 4. Graph v1 DB
    print("\n=== Auditing Graph v1 Database ===")
    db_path = os.path.join(GRAPH_V1, "graph.db")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT node_type, COUNT(*) FROM nodes GROUP BY node_type")
        nodes_summary = cur.fetchall()
        print(f"Graph Nodes: {nodes_summary}")
        cur.execute("SELECT relationship_type, COUNT(*) FROM edges GROUP BY relationship_type")
        edges_summary = cur.fetchall()
        print(f"Graph Edges: {edges_summary}")
        cur.execute("SELECT exclusion_reason, COUNT(*) FROM excluded_edges GROUP BY exclusion_reason")
        excl_summary = cur.fetchall()
        print(f"Excluded Edges: {excl_summary}")
        conn.close()

if __name__ == "__main__":
    audit_baseline()
