"""
Retrieval regression tests for NyayaVarta.
Tests BM25, Dense, Hybrid retrievers and evaluation infrastructure.
"""
import pytest
import os
import json
import tempfile
import sqlite3
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.retrieval.bm25_retriever import BM25Retriever
from services.retrieval.hybrid_retriever import HybridRetriever
from services.retrieval.config import DEFAULT_CONFIG, load_config


# --- BM25 Tests ---

class TestBM25Retriever:
    @pytest.fixture
    def bm25_db(self, tmp_path):
        """Create a temporary BM25 index with sample documents."""
        db_path = str(tmp_path / "test_bm25.db")
        retriever = BM25Retriever(db_path)
        retriever.init_db()

        docs = [
            {
                "document_id": "doc001",
                "case_title": "State of Maharashtra vs Accused",
                "full_text": "The appellant was convicted under Section 302 of the Indian Penal Code for murder."
            },
            {
                "document_id": "doc002",
                "case_title": "ABC Corporation vs XYZ Ltd",
                "full_text": "This is a commercial dispute regarding breach of contract under the Indian Contract Act."
            },
            {
                "document_id": "doc003",
                "case_title": "Petitioner vs Union of India",
                "full_text": "Article 21 of the Constitution guarantees the right to life and personal liberty."
            },
            {
                "document_id": "doc004",
                "case_title": "Anti-Defection Case",
                "full_text": "The anti-defection law under the Tenth Schedule of the Constitution was examined."
            },
        ]
        retriever.index_documents(docs)
        return retriever

    def test_basic_search(self, bm25_db):
        results, latency = bm25_db.search("murder Section 302")
        assert len(results) > 0
        assert results[0]["document_id"] == "doc001"
        assert latency < 5.0  # Should be fast

    def test_empty_query(self, bm25_db):
        results, _ = bm25_db.search("")
        assert results == []

    def test_special_chars_query(self, bm25_db):
        """Queries with special characters should not crash."""
        results, _ = bm25_db.search("Section 302/34 IPC (read with)")
        assert isinstance(results, list)

    def test_sanitize_query_deduplication(self):
        tokens = BM25Retriever.sanitize_query("section section SECTION appeal")
        # Should deduplicate case-insensitively
        assert len([t for t in tokens if t.lower() == "section"]) == 1

    def test_sanitize_query_token_limit(self):
        long_query = " ".join([f"word{i}" for i in range(100)])
        tokens = BM25Retriever.sanitize_query(long_query)
        assert len(tokens) <= BM25Retriever.MAX_QUERY_TOKENS

    def test_sanitize_preserves_legal_terms(self):
        tokens = BM25Retriever.sanitize_query("anti-defection Tenth Schedule")
        token_strs = [t.lower() for t in tokens]
        assert "anti-defection" in token_strs or "anti" in token_strs

    def test_top_k_respected(self, bm25_db):
        results, _ = bm25_db.search("Constitution", top_k=2)
        assert len(results) <= 2

    def test_connection_reuse(self, bm25_db):
        """Multiple searches should reuse the connection."""
        bm25_db.search("test")
        conn1 = bm25_db._conn
        bm25_db.search("test2")
        conn2 = bm25_db._conn
        assert conn1 is conn2
        bm25_db.close()


# --- Hybrid Retriever Tests ---

class TestHybridRetriever:
    def test_rrf_combination(self):
        hybrid = HybridRetriever(k=60)
        bm25_results = [
            {"document_id": "A", "score": -1.0},
            {"document_id": "B", "score": -2.0},
        ]
        dense_results = [
            {"document_id": "B", "score": 0.9},
            {"document_id": "C", "score": 0.8},
        ]
        combined = hybrid.combine(bm25_results, dense_results, top_k=3)
        # B appears in both lists, should rank highest
        assert combined[0]["document_id"] == "B"
        assert len(combined) == 3

    def test_empty_inputs(self):
        hybrid = HybridRetriever()
        result = hybrid.combine([], [], top_k=5)
        assert result == []


# --- Config Tests ---

class TestConfig:
    def test_default_config_structure(self):
        config = DEFAULT_CONFIG
        assert "embedding" in config
        assert "bm25" in config
        assert "hybrid" in config
        assert "reranker" in config
        assert "selection_rule" in config
        assert config["embedding"]["model_name"] == "sentence-transformers/all-MiniLM-L6-v2"
        assert config["reranker"]["enabled"] is False
        assert config["selection_rule"]["primary_metric"] == "recall_10"


# --- Evaluation Data Tests ---

class TestEvaluationData:
    def test_synthetic_queries_exist(self):
        path = "evaluation/queries/queries.json"
        assert os.path.exists(path), f"Missing {path}"
        with open(path, "r", encoding="utf-8") as f:
            queries = json.load(f)
        assert len(queries) >= 20
        for q in queries:
            assert "query_id" in q
            assert "query_text" in q
            assert len(q["query_text"]) > 10

    def test_synthetic_gold_exists(self):
        path = "evaluation/gold/gold.json"
        assert os.path.exists(path), f"Missing {path}"
        with open(path, "r", encoding="utf-8") as f:
            gold = json.load(f)
        assert len(gold) >= 20
        for g in gold:
            assert "query_id" in g
            assert "relevant_document_ids" in g
            assert len(g["relevant_document_ids"]) >= 1

    def test_legal_queries_exist(self):
        path = "evaluation/queries/legal_queries.json"
        if not os.path.exists(path):
            pytest.skip("Legal evaluation set not yet created")
        with open(path, "r", encoding="utf-8") as f:
            queries = json.load(f)
        assert len(queries) >= 30
        for q in queries:
            assert "query_id" in q
            assert "query_text" in q
            assert "legal_domain" in q

    def test_legal_gold_exists(self):
        path = "evaluation/gold/legal_gold.json"
        if not os.path.exists(path):
            pytest.skip("Legal evaluation set not yet created")
        with open(path, "r", encoding="utf-8") as f:
            gold = json.load(f)
        assert len(gold) >= 30
        for g in gold:
            assert "query_id" in g
            assert "relevant_document_ids" in g
            assert "annotation_method" in g


# --- Index File Tests ---

class TestIndexFiles:
    def test_bm25_index_exists(self):
        assert os.path.exists("data/indexes/bm25.db")

    def test_faiss_index_exists(self):
        assert os.path.exists("data/indexes/dense.faiss")

    def test_doc_ids_exists(self):
        assert os.path.exists("data/indexes/dense_doc_ids.json")
        with open("data/indexes/dense_doc_ids.json", "r") as f:
            ids = json.load(f)
        assert len(ids) > 0

    def test_model_config_exists(self):
        assert os.path.exists("data/indexes/dense_model_config.json")


# --- Regression Tests ---

class TestRQ001RetrievalRegression:
    def test_rq001_bm25_stopword_preservation(self):
        from services.retrieval.bm25_retriever import BM25Retriever
        q = "What are the legal standards and grounds for granting bail to an accused facing prosecution under Section 45 of the Prevention of Money Laundering Act (PMLA)?"
        tokens = BM25Retriever.sanitize_query(q)
        # Verify conversational stopwords were stripped
        for sw in ["what", "are", "the", "and", "for", "to", "an", "of"]:
            assert sw not in [t.lower() for t in tokens]
        # Verify critical substantive statutory tokens are present
        assert "45" in tokens
        assert "pmla" in [t.lower() for t in tokens]
        assert "bail" in [t.lower() for t in tokens]
        assert "laundering" in [t.lower() for t in tokens]

    def test_rq001_retrieval_finds_expected_judgments(self):
        from services.graph.graph_retriever import GraphExpandedRetriever
        gr = GraphExpandedRetriever()
        q = "What are the legal standards and grounds for granting bail to an accused facing prosecution under Section 45 of the Prevention of Money Laundering Act (PMLA)?"
        expected_docs = {"2024_10_393_410", "2024_3_778_811"}

        results = gr.retrieve(q, top_k=5, enable_graph=False)
        top5_ids = [r["document_id"] for r in results]
        
        # Verify that at least one (and in fact both) expected judgments are in top 5
        matches = [d for d in top5_ids if d in expected_docs]
        assert len(matches) >= 1, f"Expected {expected_docs} in top 5, but got {top5_ids}"
        # Verify top rank contains expected authority
        assert top5_ids[0] in expected_docs or top5_ids[1] in expected_docs
