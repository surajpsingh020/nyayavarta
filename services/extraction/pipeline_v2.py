"""
Extraction and Resolution Pipeline V2 for NyayaVarta (Milestone 11 Task 5).

Runs:
1. Citation extraction with CitationExtractor and canonical normalization with CitationNormalizer.
2. Conservative entity resolution with EntityResolverV2 (exact SCR/INSC indexing, year-aware bipartite title matching).
3. Statutory extraction with StatuteExtractor and paragraph-bounded conservative inheritance with StatuteResolverV2.

Writes versioned outputs to data/processed/extraction/v2/:
- case_citations.jsonl
- resolved_entities.jsonl
- statutory_references.jsonl
- extraction_manifest.json
"""
import os, sys
sys.path.insert(0, os.path.abspath("."))
import json
import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from services.extraction.citation_extractor import CitationExtractor
from services.extraction.citation_normalizer import CitationNormalizer
from services.extraction.entity_resolver_v2 import EntityResolverV2
from services.extraction.statute_extractor import StatuteExtractor
from services.extraction.statute_resolver_v2 import StatuteResolverV2

PROCESSED_DIR = "data/processed/aws_sc"
OUTPUT_DIR_V2 = "data/processed/extraction/v2"


class ExtractionPipelineV2:
    PIPELINE_VERSION = "2.0.0"

    def __init__(self, processed_dir: str = PROCESSED_DIR, output_dir: str = OUTPUT_DIR_V2):
        self.processed_dir = processed_dir
        self.output_dir = output_dir

        self.citation_extractor = CitationExtractor()
        self.citation_normalizer = CitationNormalizer()
        self.entity_resolver = EntityResolverV2(processed_dir=processed_dir)
        self.statute_extractor = StatuteExtractor()
        self.statute_resolver = StatuteResolverV2()

        os.makedirs(self.output_dir, exist_ok=True)

    def run(self, max_docs: Optional[int] = None) -> Dict[str, Any]:
        files = sorted([f for f in os.listdir(self.processed_dir) if f.endswith('.json')])
        if max_docs:
            files = files[:max_docs]

        total_docs = len(files)
        print(f"Starting Extraction Pipeline V2 on {total_docs} documents...")

        citations_file = os.path.join(self.output_dir, "case_citations.jsonl")
        resolved_file = os.path.join(self.output_dir, "resolved_entities.jsonl")
        statutes_file = os.path.join(self.output_dir, "statutory_references.jsonl")

        start_time = time.time()
        total_citations = 0
        total_statutes = 0
        resolution_counts = {"resolved": 0, "ambiguous": 0, "unresolved": 0}
        self_citations_count = 0
        cross_doc_count = 0
        match_method_counts = {}

        statute_attribution_counts = {
            "explicit": 0,
            "inherited": 0,
            "ambiguous": 0,
            "unresolved": 0,
            "other_statutory_types": 0
        }

        with open(citations_file, "w", encoding="utf-8") as f_cite, \
             open(resolved_file, "w", encoding="utf-8") as f_res, \
             open(statutes_file, "w", encoding="utf-8") as f_stat:

            for idx, fname in enumerate(files):
                fpath = os.path.join(self.processed_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    doc = json.load(f)

                doc_id = doc.get("document_id")
                text = doc.get("full_text", "")
                provenance = doc.get("provenance", "AWS Open Data")

                # 1. Extract raw citations
                raw_cites = self.citation_extractor.extract_all(text, doc_id)

                for c in raw_cites:
                    c["provenance"] = provenance
                    # Canonical citation normalization if formal reporter
                    norm_record = self.citation_normalizer.normalize(c.get("raw_text", ""))
                    if norm_record.parsing_status == "valid":
                        c["normalized_citation"] = norm_record.normalized_citation
                        c["citation_scheme"] = norm_record.citation_scheme
                        if norm_record.year:
                            c.setdefault("components", {})["year"] = norm_record.year
                        if norm_record.volume:
                            c.setdefault("components", {})["vol"] = norm_record.volume
                        if norm_record.page_or_number:
                            c.setdefault("components", {})["page"] = norm_record.page_or_number

                    f_cite.write(json.dumps(c, ensure_ascii=False) + "\n")
                    total_citations += 1

                    # 2. Conservative Entity Resolution V2
                    resolution = self.entity_resolver.resolve_citation(c)
                    resolution["provenance"] = provenance
                    f_res.write(json.dumps(resolution, ensure_ascii=False) + "\n")

                    status = resolution["resolution_status"]
                    resolution_counts[status] = resolution_counts.get(status, 0) + 1
                    method = resolution.get("match_method", "unknown")
                    match_method_counts[method] = match_method_counts.get(method, 0) + 1

                    if resolution.get("is_self_citation"):
                        self_citations_count += 1
                    elif status == "resolved":
                        cross_doc_count += 1

                # 3. Extract statutory references
                # A: Non-sections (acts, articles, orders/rules, schedules)
                doc_acts = self.statute_extractor.extract_acts(text, doc_id)
                doc_articles = self.statute_extractor.extract_articles(text, doc_id)
                doc_rules = self.statute_extractor.extract_orders_and_rules(text, doc_id)
                doc_schedules = self.statute_extractor.extract_schedules(text, doc_id)

                for s in (doc_acts + doc_articles + doc_rules + doc_schedules):
                    s["provenance"] = provenance
                    s["attribution_type"] = "explicit"
                    s["attribution_source"] = "direct_extraction"
                    f_stat.write(json.dumps(s, ensure_ascii=False) + "\n")
                    total_statutes += 1
                    statute_attribution_counts["other_statutory_types"] += 1

                # B: Statutory sections with conservative paragraph-bounded inheritance
                doc_sections_raw = self.statute_resolver.extract_sections_v2(text, doc_id)
                resolved_sections = self.statute_resolver.resolve_document_statutes(
                    text=text,
                    source_doc_id=doc_id,
                    extracted_sections=doc_sections_raw
                )

                for sec in resolved_sections:
                    sec["provenance"] = provenance
                    f_stat.write(json.dumps(sec, ensure_ascii=False) + "\n")
                    total_statutes += 1
                    atype = sec.get("attribution_type", "unresolved")
                    statute_attribution_counts[atype] = statute_attribution_counts.get(atype, 0) + 1

                if (idx + 1) % 100 == 0 or (idx + 1) == total_docs:
                    elapsed = time.time() - start_time
                    rate = (idx + 1) / elapsed if elapsed > 0 else 0
                    print(f"Processed {idx + 1}/{total_docs} docs ({rate:.1f} docs/s). Citations: {total_citations}, Statutes: {total_statutes}")

        elapsed_total = time.time() - start_time

        manifest = {
            "pipeline_version": self.PIPELINE_VERSION,
            "extraction_timestamp": datetime.now().isoformat(),
            "corpus_processed_docs": total_docs,
            "runtime_seconds": round(elapsed_total, 2),
            "throughput_docs_per_sec": round(total_docs / elapsed_total, 2) if elapsed_total > 0 else 0,
            "citation_counts": {
                "total_citations_extracted": total_citations,
                "resolution_breakdown": resolution_counts,
                "self_citations_flagged": self_citations_count,
                "cross_doc_matches": cross_doc_count,
                "matching_methods": match_method_counts
            },
            "statutory_counts": {
                "total_statutory_references": total_statutes,
                "section_attribution_breakdown": statute_attribution_counts
            },
            "output_files": {
                "citations": citations_file,
                "resolved_entities": resolved_file,
                "statutory_references": statutes_file
            }
        }

        manifest_file = os.path.join(self.output_dir, "extraction_manifest.json")
        with open(manifest_file, "w", encoding="utf-8") as f_man:
            json.dump(manifest, f_man, indent=4)

        print("\n=== Extraction Pipeline V2 Complete ===")
        print(f"Runtime: {manifest['runtime_seconds']}s")
        print(f"Total Citations: {total_citations}")
        print(f"Resolution Breakdown: {resolution_counts}")
        print(f"Self-Citations: {self_citations_count}")
        print(f"Cross-Doc Matches: {cross_doc_count}")
        print(f"Statutory Section Attribution: {statute_attribution_counts}")
        print(f"Manifest written to {manifest_file}")

        return manifest


if __name__ == "__main__":
    p = ExtractionPipelineV2()
    p.run()
