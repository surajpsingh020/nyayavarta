"""
BM25 Profiling and Latency Analysis Script.

Profiles separately:
1. Connection overhead (open/close vs persistent)
2. Query sanitization & tokenization
3. FTS5 MATCH execution
4. Result retrieval & tuple mapping
5. Query mode latency comparison (naive unoptimized OR vs optimized AND-fallback)
6. Legal term preservation validation
"""
import os
import json
import time
import sqlite3
import statistics
import re

from services.retrieval.bm25_retriever import BM25Retriever

DB_PATH = "data/indexes/bm25.db"


def load_queries():
    queries = []
    # Load synthetic queries
    syn_path = "evaluation/queries/queries.json"
    if os.path.exists(syn_path):
        with open(syn_path, "r", encoding="utf-8") as f:
            for q in json.load(f):
                queries.append(("synthetic", q["query_id"], q["query_text"]))

    # Load legal queries
    legal_path = "evaluation/queries/legal_queries.json"
    if os.path.exists(legal_path):
        with open(legal_path, "r", encoding="utf-8") as f:
            for q in json.load(f):
                queries.append(("legal", q["query_id"], q["query_text"]))

    return queries


def profile_stages(queries):
    """Profile connection, sanitization, FTS execution, and retrieval."""
    conn_times = []
    sanitize_times = []
    fts_and_times = []
    fts_or_times = []
    fetch_times = []

    retriever = BM25Retriever(DB_PATH)
    persistent_conn = retriever.conn

    for _, _, q_text in queries:
        # 1. Connection overhead (fresh connection)
        t0 = time.perf_counter()
        c = sqlite3.connect(DB_PATH)
        c.close()
        t1 = time.perf_counter()
        conn_times.append((t1 - t0) * 1000)

        # 2. Sanitization time
        t0 = time.perf_counter()
        tokens = BM25Retriever.sanitize_query(q_text)
        t1 = time.perf_counter()
        sanitize_times.append((t1 - t0) * 1000)

        if not tokens:
            continue

        # 3. FTS execution (AND mode)
        and_fts_query = " AND ".join(f'"{t}"' for t in tokens)
        cursor = persistent_conn.cursor()
        t0 = time.perf_counter()
        cursor.execute('''
            SELECT document_id, bm25(legal_docs) as score
            FROM legal_docs
            WHERE legal_docs MATCH ?
            ORDER BY score
            LIMIT 10
        ''', (and_fts_query,))
        t1 = time.perf_counter()
        fts_and_times.append((t1 - t0) * 1000)

        # 4. Fetch/mapping time
        t0 = time.perf_counter()
        _ = cursor.fetchall()
        t1 = time.perf_counter()
        fetch_times.append((t1 - t0) * 1000)

        # 5. FTS execution (naive OR mode with all tokens)
        or_fts_query = " OR ".join(f'"{t}"' for t in tokens)
        t0 = time.perf_counter()
        try:
            cursor.execute('''
                SELECT document_id, bm25(legal_docs) as score
                FROM legal_docs
                WHERE legal_docs MATCH ?
                ORDER BY score
                LIMIT 10
            ''', (or_fts_query,))
            _ = cursor.fetchall()
            t1 = time.perf_counter()
            fts_or_times.append((t1 - t0) * 1000)
        except Exception:
            pass

    retriever.close()

    def stats(arr):
        if not arr:
            return {"mean": 0, "median": 0, "p95": 0, "min": 0, "max": 0}
        s = sorted(arr)
        p95_idx = min(int(len(s) * 0.95), len(s) - 1)
        return {
            "mean": statistics.mean(arr),
            "median": statistics.median(arr),
            "p95": s[p95_idx],
            "min": min(arr),
            "max": max(arr)
        }

    return {
        "connection_overhead_ms": stats(conn_times),
        "sanitization_ms": stats(sanitize_times),
        "fts_and_execution_ms": stats(fts_and_times),
        "fts_or_execution_ms": stats(fts_or_times),
        "fetch_tuples_ms": stats(fetch_times),
    }


def test_legal_term_preservation():
    """Verify that key legal terms, sections, and statutes are preserved in sanitization."""
    test_cases = [
        ("Section 302/34 of IPC", ["Section", "302", "34", "IPC"]),
        ("bail under Section 439 Cr.P.C.", ["bail", "Section", "439", "Cr", "P"]),
        ("twin conditions under Section 45 PMLA", ["twin", "conditions", "Section", "45", "PMLA"]),
        ("Article 21 and 14 of the Constitution", ["Article", "21", "14", "Constitution"]),
        ("Order XXI Rule 99 CPC dispossession", ["Order", "XXI", "Rule", "99", "CPC", "dispossession"]),
        ("anti-defection law under Tenth Schedule", ["anti-defection", "law", "Tenth", "Schedule"]),
        ("Section 17(5)(d) of CGST Act", ["Section", "17", "CGST", "Act"]),
    ]

    results = []
    for raw, expected_terms in test_cases:
        tokens = BM25Retriever.sanitize_query(raw)
        token_lower = [t.lower() for t in tokens]
        preserved = []
        missing = []
        for term in expected_terms:
            if term.lower() in token_lower or any(term.lower() in t for t in token_lower):
                preserved.append(term)
            else:
                missing.append(term)
        results.append({
            "query": raw,
            "tokens": tokens,
            "preserved": preserved,
            "missing": missing,
            "success": len(missing) == 0
        })

    return results


def main():
    print("=" * 60)
    print("BM25 Profiling and Latency Analysis")
    print("=" * 60)

    queries = load_queries()
    print(f"Total queries for profiling: {len(queries)}")

    # Stage breakdown
    print("\n1. Measuring stage latency breakdown...")
    breakdown = profile_stages(queries)

    print("\n--- Latency Breakdown (Per Query) ---")
    for stage, s in breakdown.items():
        print(f"  {stage:26s} | Mean: {s['mean']:7.2f}ms | Med: {s['median']:7.2f}ms | P95: {s['p95']:7.2f}ms")

    # Legal term preservation
    print("\n2. Testing legal term preservation...")
    preservation = test_legal_term_preservation()
    all_ok = True
    for p in preservation:
        status = "PASS" if p["success"] else "FAIL"
        print(f"  [{status}] '{p['query']}' -> Tokens: {p['tokens']}")
        if p["missing"]:
            print(f"         Missing terms: {p['missing']}")
            all_ok = False

    # Measure full retriever latency across queries
    print("\n3. Measuring full BM25Retriever.search() latency...")
    retriever = BM25Retriever(DB_PATH)
    latencies = []
    for _, _, q_text in queries:
        _, lat = retriever.search(q_text, top_k=10)
        latencies.append(lat * 1000)
    retriever.close()

    s = sorted(latencies)
    p95_idx = min(int(len(s) * 0.95), len(s) - 1)
    print(f"  Full BM25 search latency ({len(latencies)} queries):")
    print(f"    Mean:   {statistics.mean(latencies):.2f} ms")
    print(f"    Median: {statistics.median(latencies):.2f} ms")
    print(f"    P95:    {s[p95_idx]:.2f} ms")
    print(f"    Min:    {min(latencies):.2f} ms")
    print(f"    Max:    {max(latencies):.2f} ms")

    # Save report
    report = {
        "query_count": len(queries),
        "stage_breakdown": breakdown,
        "term_preservation": preservation,
        "full_search_latency_ms": {
            "mean": statistics.mean(latencies),
            "median": statistics.median(latencies),
            "p95": s[p95_idx],
            "min": min(latencies),
            "max": max(latencies)
        }
    }

    os.makedirs("docs/retrieval", exist_ok=True)
    with open("docs/retrieval/BM25_PROFILE.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    print("\nSaved profile report to docs/retrieval/BM25_PROFILE.json")


if __name__ == "__main__":
    main()
