"""
Comprehensive JSONL Integrity Validator for NyayaVarta (Milestone 4A.1).
Audits all records across extraction v1 files:
- case_citations.jsonl
- statutory_references.jsonl
- resolved_entities.jsonl
- extraction_manifest.json

Verifies schema adherence, record alignment, corpus foreign keys, status invariants,
exact duplicate extraction records, and overlapping spans.
"""
import os
import json
import re
from collections import defaultdict
from typing import Dict, Any, List, Set, Tuple

PROCESSED_DIR = "data/processed/aws_sc"
EXTRACTION_DIR = "data/processed/extraction/v1"
OUT_REPORT = "evaluation/validation/jsonl_integrity_report.json"


def validate_jsonl():
    print("=" * 70)
    print("Starting Comprehensive JSONL Integrity Audit")
    print("=" * 70)

    # 1. Load Corpus Document IDs
    corpus_ids = set()
    for fname in os.listdir(PROCESSED_DIR):
        if fname.endswith(".json"):
            corpus_ids.add(fname[:-5])
    print(f"Loaded {len(corpus_ids)} canonical corpus document IDs.")

    # 2. Check Manifest
    manifest_path = os.path.join(EXTRACTION_DIR, "extraction_manifest.json")
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    print(f"Loaded extraction manifest (version {manifest.get('pipeline_version')}).")

    citations_path = os.path.join(EXTRACTION_DIR, "case_citations.jsonl")
    statutes_path = os.path.join(EXTRACTION_DIR, "statutory_references.jsonl")
    resolved_path = os.path.join(EXTRACTION_DIR, "resolved_entities.jsonl")

    # 3. Audit case_citations.jsonl
    print("\n[1/4] Auditing case_citations.jsonl...")
    cite_records = []
    cite_keys_seen = set()
    cite_exact_dups = []
    cite_invalid_docs = []
    cite_schema_errors = []
    doc_citation_spans = defaultdict(list)
    cite_type_counts = defaultdict(int)

    req_cite_fields = [
        "source_doc_id", "citation_type", "raw_text", "normalized_citation",
        "components", "start_char", "end_char", "mention_context",
        "extraction_method", "confidence", "version", "provenance"
    ]

    with open(citations_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            try:
                rec = json.loads(line)
            except Exception as e:
                cite_schema_errors.append(f"Line {idx}: JSON parse error: {e}")
                continue

            for field in req_cite_fields:
                if field not in rec or rec[field] is None:
                    cite_schema_errors.append(f"Line {idx}: Missing/null required field '{field}'")

            doc_id = rec.get("source_doc_id")
            if doc_id not in corpus_ids:
                cite_invalid_docs.append((idx, doc_id))

            c_type = rec.get("citation_type")
            cite_type_counts[c_type] += 1

            start_c = rec.get("start_char", 0)
            end_c = rec.get("end_char", 0)
            raw = rec.get("raw_text", "")

            # Exact duplicate check: (doc_id, raw_text, start_char, end_char)
            dup_key = (doc_id, raw, start_c, end_c)
            if dup_key in cite_keys_seen:
                cite_exact_dups.append({
                    "line": idx,
                    "doc_id": doc_id,
                    "raw_text": raw[:60],
                    "span": [start_c, end_c]
                })
            cite_keys_seen.add(dup_key)

            doc_citation_spans[doc_id].append((start_c, end_c, c_type, raw[:50]))
            cite_records.append(rec)

    total_citations = len(cite_records)
    print(f"  Parsed {total_citations} citation records.")
    print(f"  Schema errors: {len(cite_schema_errors)}")
    print(f"  Invalid source doc IDs: {len(cite_invalid_docs)}")
    print(f"  Exact duplicates: {len(cite_exact_dups)}")

    # Overlapping span analysis
    overlapping_spans = []
    overlap_type_pairs = defaultdict(int)

    for doc_id, spans in doc_citation_spans.items():
        spans.sort(key=lambda s: (s[0], s[1]))
        for i in range(len(spans) - 1):
            curr_span = spans[i]
            next_span = spans[i + 1]
            if curr_span[1] > next_span[0]:  # overlap
                pair_type = f"{curr_span[2]} <-> {next_span[2]}"
                overlap_type_pairs[pair_type] += 1
                if len(overlapping_spans) < 10:
                    overlapping_spans.append({
                        "doc_id": doc_id,
                        "span_a": [curr_span[0], curr_span[1], curr_span[2], curr_span[3]],
                        "span_b": [next_span[0], next_span[1], next_span[2], next_span[3]]
                    })

    total_overlaps = sum(overlap_type_pairs.values())
    print(f"  Overlapping span pairs in citations: {total_overlaps}")

    # 4. Audit statutory_references.jsonl
    print("\n[2/4] Auditing statutory_references.jsonl...")
    statute_records = []
    stat_exact_dups = []
    stat_invalid_docs = []
    stat_schema_errors = []
    stat_type_counts = defaultdict(int)
    stat_keys_seen = set()

    req_stat_fields = [
        "source_doc_id", "reference_type", "raw_text", "normalized_reference",
        "components", "start_char", "end_char", "mention_context",
        "extraction_method", "confidence", "version", "provenance"
    ]

    with open(statutes_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            try:
                rec = json.loads(line)
            except Exception as e:
                stat_schema_errors.append(f"Line {idx}: JSON parse error: {e}")
                continue

            for field in req_stat_fields:
                if field not in rec or rec[field] is None:
                    stat_schema_errors.append(f"Line {idx}: Missing/null required field '{field}'")

            doc_id = rec.get("source_doc_id")
            if doc_id not in corpus_ids:
                stat_invalid_docs.append((idx, doc_id))

            r_type = rec.get("reference_type")
            stat_type_counts[r_type] += 1

            start_c = rec.get("start_char", 0)
            end_c = rec.get("end_char", 0)
            raw = rec.get("raw_text", "")

            dup_key = (doc_id, raw, start_c, end_c)
            if dup_key in stat_keys_seen:
                stat_exact_dups.append({
                    "line": idx,
                    "doc_id": doc_id,
                    "raw_text": raw[:60],
                    "span": [start_c, end_c]
                })
            stat_keys_seen.add(dup_key)
            statute_records.append(rec)

    total_statutes = len(statute_records)
    print(f"  Parsed {total_statutes} statutory records.")
    print(f"  Schema errors: {len(stat_schema_errors)}")
    print(f"  Invalid source doc IDs: {len(stat_invalid_docs)}")
    print(f"  Exact duplicates: {len(stat_exact_dups)}")

    # 5. Audit resolved_entities.jsonl
    print("\n[3/4] Auditing resolved_entities.jsonl...")
    res_records = []
    res_schema_errors = []
    res_status_invariants_broken = []
    res_invalid_targets = []
    res_invalid_candidates = []
    res_status_counts = defaultdict(int)
    res_method_counts = defaultdict(int)
    self_citations_count = 0
    cross_doc_resolved_count = 0

    req_res_fields = [
        "source_doc_id", "mention_raw", "mention_normalized",
        "resolution_status", "match_method", "confidence_score",
        "is_self_citation", "version", "provenance"
    ]

    with open(resolved_path, "r", encoding="utf-8") as f:
        for idx, line in enumerate(f):
            try:
                rec = json.loads(line)
            except Exception as e:
                res_schema_errors.append(f"Line {idx}: JSON parse error: {e}")
                continue

            for field in req_res_fields:
                if field not in rec or rec[field] is None:
                    res_schema_errors.append(f"Line {idx}: Missing/null required field '{field}'")

            status = rec.get("resolution_status")
            res_status_counts[status] += 1
            method = rec.get("match_method")
            res_method_counts[method] += 1

            target_id = rec.get("resolved_document_id")
            candidates = rec.get("ambiguous_candidate_ids")
            is_self = rec.get("is_self_citation", False)

            # Invariant checks
            if status == "resolved":
                if not target_id:
                    res_status_invariants_broken.append((idx, "Status 'resolved' with null resolved_document_id"))
                elif target_id not in corpus_ids:
                    res_invalid_targets.append((idx, target_id))
                else:
                    if is_self:
                        self_citations_count += 1
                    else:
                        cross_doc_resolved_count += 1

            elif status == "unresolved":
                if target_id is not None:
                    res_status_invariants_broken.append((idx, "Status 'unresolved' with non-null resolved_document_id"))

            elif status == "ambiguous":
                if target_id is not None:
                    res_status_invariants_broken.append((idx, "Status 'ambiguous' with non-null resolved_document_id"))
                if not candidates or len(candidates) < 2:
                    res_status_invariants_broken.append((idx, "Status 'ambiguous' with empty/<2 candidates"))
                else:
                    for cid in candidates:
                        if cid not in corpus_ids:
                            res_invalid_candidates.append((idx, cid))

            res_records.append(rec)

    total_resolved = len(res_records)
    print(f"  Parsed {total_resolved} resolved entity records.")
    print(f"  Schema errors: {len(res_schema_errors)}")
    print(f"  Status invariant violations: {len(res_status_invariants_broken)}")
    print(f"  Invalid target IDs: {len(res_invalid_targets)}")
    print(f"  Invalid ambiguous candidate IDs: {len(res_invalid_candidates)}")
    print(f"  Status breakdown: {dict(res_status_counts)}")
    print(f"  Self-citations: {self_citations_count}, Cross-doc resolved: {cross_doc_resolved_count}")

    # 6. Alignment & Manifest Cross-Check
    print("\n[4/4] Verifying 1:1 Alignment & Manifest Counts...")
    alignment_mismatches = 0
    if len(cite_records) != len(res_records):
        print(f"  CRITICAL: Citation count ({len(cite_records)}) != Resolution count ({len(res_records)})")
    else:
        for idx in range(len(cite_records)):
            c = cite_records[idx]
            r = res_records[idx]
            if c["source_doc_id"] != r["source_doc_id"] or c["raw_text"] != r["mention_raw"]:
                alignment_mismatches += 1
                if alignment_mismatches <= 5:
                    print(f"  Alignment mismatch at line {idx}: {c['source_doc_id']} vs {r['source_doc_id']}")

    print(f"  Total 1:1 alignment mismatches: {alignment_mismatches}")

    # Manifest checks
    m_counts = manifest.get("counts", {})
    manifest_discrepancies = []
    if m_counts.get("total_case_citations_extracted") != total_citations:
        manifest_discrepancies.append(f"Citations: manifest={m_counts.get('total_case_citations_extracted')} actual={total_citations}")
    if m_counts.get("total_statutory_references_extracted") != total_statutes:
        manifest_discrepancies.append(f"Statutes: manifest={m_counts.get('total_statutory_references_extracted')} actual={total_statutes}")
    m_res = m_counts.get("resolution_breakdown", {})
    if m_res.get("resolved") != res_status_counts["resolved"]:
        manifest_discrepancies.append(f"Resolved: manifest={m_res.get('resolved')} actual={res_status_counts['resolved']}")
    if m_res.get("ambiguous") != res_status_counts["ambiguous"]:
        manifest_discrepancies.append(f"Ambiguous: manifest={m_res.get('ambiguous')} actual={res_status_counts['ambiguous']}")
    if m_res.get("unresolved") != res_status_counts["unresolved"]:
        manifest_discrepancies.append(f"Unresolved: manifest={m_res.get('unresolved')} actual={res_status_counts['unresolved']}")
    if m_counts.get("self_citations_flagged") != self_citations_count:
        manifest_discrepancies.append(f"Self-citations: manifest={m_counts.get('self_citations_flagged')} actual={self_citations_count}")

    print(f"  Manifest discrepancies: {len(manifest_discrepancies)}")
    if manifest_discrepancies:
        for d in manifest_discrepancies:
            print(f"    - {d}")

    # Compile report
    report = {
        "validator_version": "1.0.0",
        "milestone": "4A.1",
        "audit_timestamp": "2026-10-12T12:00:00Z",
        "corpus_documents_verified": len(corpus_ids),
        "summary": {
            "case_citations_count": total_citations,
            "statutory_references_count": total_statutes,
            "resolved_entities_count": total_resolved,
            "alignment_1_to_1": (alignment_mismatches == 0 and len(cite_records) == len(res_records)),
            "all_targets_valid_foreign_keys": (len(res_invalid_targets) == 0),
            "status_invariants_preserved": (len(res_status_invariants_broken) == 0),
            "manifest_verified": (len(manifest_discrepancies) == 0)
        },
        "case_citations_audit": {
            "total_records": total_citations,
            "schema_errors": len(cite_schema_errors),
            "invalid_source_doc_ids": len(cite_invalid_docs),
            "exact_duplicate_records_count": len(cite_exact_dups),
            "exact_duplicate_samples": cite_exact_dups[:5],
            "overlapping_spans_count": total_overlaps,
            "overlapping_span_distribution": dict(overlap_type_pairs),
            "overlapping_span_samples": overlapping_spans,
            "type_distribution": dict(cite_type_counts)
        },
        "statutory_references_audit": {
            "total_records": total_statutes,
            "schema_errors": len(stat_schema_errors),
            "invalid_source_doc_ids": len(stat_invalid_docs),
            "exact_duplicate_records_count": len(stat_exact_dups),
            "type_distribution": dict(stat_type_counts)
        },
        "resolved_entities_audit": {
            "total_records": total_resolved,
            "schema_errors": len(res_schema_errors),
            "status_invariants_violations_count": len(res_status_invariants_broken),
            "invalid_target_doc_ids_count": len(res_invalid_targets),
            "invalid_ambiguous_candidates_count": len(res_invalid_candidates),
            "status_distribution": dict(res_status_counts),
            "match_methods_distribution": dict(res_method_counts),
            "linking_breakdown": {
                "self_citations_resolved": self_citations_count,
                "cross_document_resolved": cross_doc_resolved_count,
                "self_citation_percentage": round((self_citations_count / res_status_counts["resolved"]) * 100, 2)
            }
        },
        "manifest_audit": {
            "manifest_path": manifest_path,
            "manifest_discrepancies": manifest_discrepancies
        }
    }

    os.makedirs(os.path.dirname(OUT_REPORT), exist_ok=True)
    with open(OUT_REPORT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)
    print(f"\nSaved complete integrity report to {OUT_REPORT}")
    return report


if __name__ == "__main__":
    validate_jsonl()
