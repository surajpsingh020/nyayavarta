"""
Extraction and Resolution Pipeline for NyayaVarta (Milestone 4A).

Runs citation extraction, statutory extraction, and entity resolution across
the 782 canonical judgments and produces versioned JSONL outputs.
"""
import os
import json
import time
from typing import Dict, Any, List
from datetime import datetime

from services.extraction.citation_extractor import CitationExtractor
from services.extraction.statute_extractor import StatuteExtractor
from services.extraction.entity_resolver import EntityResolver

PROCESSED_DIR = "data/processed/aws_sc"
OUTPUT_DIR = "data/processed/extraction/v1"


class ExtractionPipeline:
    PIPELINE_VERSION = "1.0.0"

    def __init__(self, processed_dir: str = PROCESSED_DIR, output_dir: str = OUTPUT_DIR):
        self.processed_dir = processed_dir
        self.output_dir = output_dir
        self.citation_extractor = CitationExtractor()
        self.statute_extractor = StatuteExtractor()
        self.entity_resolver = EntityResolver(processed_dir=processed_dir)

        os.makedirs(self.output_dir, exist_ok=True)

    def run(self, max_docs: int = None) -> Dict[str, Any]:
        files = [f for f in os.listdir(self.processed_dir) if f.endswith('.json')]
        if max_docs:
            files = files[:max_docs]

        total_docs = len(files)
        print(f"Starting extraction on {total_docs} documents...")

        citations_file = os.path.join(self.output_dir, "case_citations.jsonl")
        statutes_file = os.path.join(self.output_dir, "statutory_references.jsonl")
        resolved_file = os.path.join(self.output_dir, "resolved_entities.jsonl")

        start_time = time.time()
        total_citations = 0
        total_statutes = 0
        resolution_counts = {"resolved": 0, "ambiguous": 0, "unresolved": 0}
        self_citations_count = 0

        with open(citations_file, "w", encoding="utf-8") as f_cite, \
             open(statutes_file, "w", encoding="utf-8") as f_stat, \
             open(resolved_file, "w", encoding="utf-8") as f_res:

            for idx, fname in enumerate(files):
                fpath = os.path.join(self.processed_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    doc = json.load(f)

                doc_id = doc.get("document_id")
                text = doc.get("full_text", "")
                provenance = doc.get("provenance", "AWS Open Data")

                # 1. Extract citations
                cites = self.citation_extractor.extract_all(text, doc_id)
                for c in cites:
                    c["provenance"] = provenance
                    f_cite.write(json.dumps(c, ensure_ascii=False) + "\n")
                    total_citations += 1

                    # 2. Resolve citation entities
                    resolution = self.entity_resolver.resolve_citation(c)
                    resolution["provenance"] = provenance
                    f_res.write(json.dumps(resolution, ensure_ascii=False) + "\n")

                    status = resolution["resolution_status"]
                    resolution_counts[status] = resolution_counts.get(status, 0) + 1
                    if resolution.get("is_self_citation"):
                        self_citations_count += 1

                # 3. Extract statutory references
                stats = self.statute_extractor.extract_all(text, doc_id)
                for s in stats:
                    s["provenance"] = provenance
                    f_stat.write(json.dumps(s, ensure_ascii=False) + "\n")
                    total_statutes += 1

                if (idx + 1) % 100 == 0 or (idx + 1) == total_docs:
                    elapsed = time.time() - start_time
                    rate = (idx + 1) / elapsed if elapsed > 0 else 0
                    print(f"Processed {idx + 1}/{total_docs} docs ({rate:.1f} docs/s). Citations: {total_citations}, Statutes: {total_statutes}")

        elapsed_total = time.time() - start_time

        # Create extraction manifest
        manifest = {
            "pipeline_version": self.PIPELINE_VERSION,
            "extraction_timestamp": datetime.now().isoformat(),
            "corpus_processed_docs": total_docs,
            "runtime_seconds": round(elapsed_total, 2),
            "throughput_docs_per_sec": round(total_docs / elapsed_total, 2) if elapsed_total > 0 else 0,
            "counts": {
                "total_case_citations_extracted": total_citations,
                "total_statutory_references_extracted": total_statutes,
                "resolution_breakdown": resolution_counts,
                "self_citations_flagged": self_citations_count
            },
            "output_files": {
                "citations": citations_file,
                "statutory_references": statutes_file,
                "resolved_entities": resolved_file
            }
        }

        manifest_file = os.path.join(self.output_dir, "extraction_manifest.json")
        with open(manifest_file, "w", encoding="utf-8") as f_man:
            json.dump(manifest, f_man, indent=4)

        print("\nExtraction complete!")
        print(f"Runtime: {manifest['runtime_seconds']}s")
        print(f"Citations extracted: {total_citations}")
        print(f"Statutes extracted: {total_statutes}")
        print(f"Resolution breakdown: {resolution_counts}")
        print(f"Manifest written to {manifest_file}")

        return manifest


if __name__ == "__main__":
    pipeline = ExtractionPipeline()
    pipeline.run()
