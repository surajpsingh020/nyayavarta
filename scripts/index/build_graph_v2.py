"""
Script to build Graph V2 from extraction v2 artifacts.
Outputs to data/processed/graph/v2/
"""
import os
import sys
sys.path.insert(0, os.path.abspath("."))

from services.graph.builder_v2 import GraphBuilderV2

if __name__ == "__main__":
    builder = GraphBuilderV2(
        corpus_dir="data/processed/aws_sc",
        extraction_dir="data/processed/extraction/v2",
        output_dir="data/processed/graph/v2",
        include_external_stubs=True
    )
    manifest = builder.build_and_export()
    print("Graph V2 build completed successfully!")
