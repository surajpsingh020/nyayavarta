"""
Unit Tests for GraphExpandedRetriever (Milestone 4B.1).

Verifies:
1. Disabled by default in user-facing retrieve() path.
2. Latency optimization: sub-second response without multi-second bottleneck.
3. Ranking determinism across identical queries.
4. Duplicate prevention in result set.
5. Provenance tracking for seed, citation expansion, and statutory expansion.
"""
import pytest
import os
import json
from services.graph.graph_retriever import GraphExpandedRetriever
from services.graph.sqlite_store import SQLiteGraphStore


@pytest.fixture(scope="module")
def retriever():
    db_path = "data/processed/graph/v1/graph.db"
    assert os.path.exists(db_path), f"Graph database missing at {db_path}"
    store = SQLiteGraphStore(db_path=db_path, preload_index=True)
    return GraphExpandedRetriever(graph_store=store)


class TestGraphExpandedRetriever:

    def test_default_retrieval_has_graph_disabled(self, retriever):
        """Default call to retrieve() must have graph expansion disabled."""
        query = "grounds for granting bail under PMLA"
        results = retriever.retrieve(query, top_k=5)

        assert len(results) == 5
        for r in results:
            assert r["retrieval_method"] == "hybrid_baseline"
            assert r["graph_boost"] == 0.0
            assert r["is_graph_discovered"] is False

    def test_graph_expansion_enabled_returns_provenance(self, retriever):
        """When enable_graph=True, graph expansion runs and records provenance."""
        query = "dishonour of cheque section 138 negotiable instruments act"
        results = retriever.retrieve(query, top_k=5, enable_graph=True)

        assert len(results) == 5
        for r in results:
            assert r["retrieval_method"] == "hybrid_plus_graph_expansion"
            assert "expansion_provenance" in r
            assert isinstance(r["expansion_provenance"], list)
            assert len(r["expansion_provenance"]) >= 1

    def test_retrieval_latency_is_optimized_under_500ms(self, retriever):
        """Query latency with graph expansion must not have multi-second bottleneck (< 500ms)."""
        query = "quashing of criminal proceedings under section 482"
        results = retriever.retrieve(query, top_k=10, enable_graph=True)

        assert len(results) == 10
        latency = results[0]["latency_ms"]
        assert latency < 500.0, f"Query took {latency:.2f} ms (expected < 500 ms)"

    def test_deterministic_ranking_across_calls(self, retriever):
        """Repeated identical queries must produce identical document rankings."""
        query = "arbitration agreement appointment of arbitrator section 11"
        res1 = retriever.retrieve(query, top_k=5, enable_graph=True)
        res2 = retriever.retrieve(query, top_k=5, enable_graph=True)

        docs1 = [r["document_id"] for r in res1]
        docs2 = [r["document_id"] for r in res2]
        assert docs1 == docs2, f"Rankings differ: {docs1} vs {docs2}"

    def test_no_duplicate_document_ids_in_results(self, retriever):
        """Result list must not contain duplicate document IDs."""
        query = "insolvency resolution process moratorium corporate debtor"
        results = retriever.retrieve(query, top_k=10, enable_graph=True)

        doc_ids = [r["document_id"] for r in results]
        assert len(doc_ids) == len(set(doc_ids)), f"Found duplicate documents: {doc_ids}"
