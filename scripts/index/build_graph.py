"""
Build NyayaVarta Knowledge Graph (Milestone 4B).
Orchestrates GraphBuilder across the canonical corpus and validated M4A.1 extractions.
"""
import sys
import os
import json
import time

sys.path.insert(0, ".")
from services.graph.builder import GraphBuilder

def main():
    print("=" * 70)
    print("NyayaVarta Milestone 4B: Restricted Knowledge Graph Builder")
    print("=" * 70)

    start_time = time.time()
    builder = GraphBuilder(
        corpus_dir="data/processed/aws_sc",
        extraction_dir="data/processed/extraction/v1",
        output_dir="data/processed/graph/v1",
        include_external_stubs=True
    )
    manifest = builder.build()
    elapsed = time.time() - start_time

    print("\n=== BUILD SUMMARY ===")
    print(f"Total Runtime: {elapsed:.2f} seconds")
    print(f"Total Nodes: {manifest.nodes_count}")
    for k, v in manifest.nodes_by_type.items():
        print(f"  Node [{k}]: {v}")
    print(f"\nTotal Edges: {manifest.edges_count}")
    for k, v in manifest.edges_by_type.items():
        print(f"  Edge [{k}]: {v}")
    print(f"\nTotal Excluded Edges: {manifest.excluded_edges_count}")
    for k, v in manifest.exclusions_by_reason.items():
        print(f"  Exclusion [{k}]: {v}")
    print(f"\nUnresolved External References: {manifest.unresolved_external_references_count}")
    print(f"\nManifest saved to data/processed/graph/v1/graph_manifest.json")

if __name__ == "__main__":
    main()
