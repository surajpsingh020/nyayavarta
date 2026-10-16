"""
Graph-Expanded Hybrid Retriever for NyayaVarta (Milestone 4B.1).

Extends the validated Milestone 3.1 Hybrid Retriever (BM25 + Dense FAISS via RRF)
with Knowledge Graph expansion over the restricted SQLite graph store:
1. Sub-millisecond graph traversal via in-memory index preloading.
2. 1-hop Citation Expansion (direct CITES edges to/from seed judgments).
3. IDF-thresholded Grounded Statutory Provision Expansion (skipping ubiquitous umbrella provisions).
4. Full expansion provenance recorded per retrieved document.
5. User-facing retrieval path has graph expansion DISABLED BY DEFAULT (enable_graph=False).
"""
import time
import math
from typing import Dict, Any, List, Optional, Tuple, Set
from collections import defaultdict

from services.retrieval.config import load_config
from services.retrieval.bm25_retriever import BM25Retriever
from services.retrieval.dense_retriever import DenseRetriever
from services.retrieval.hybrid_retriever import HybridRetriever
from services.graph.sqlite_store import SQLiteGraphStore


class GraphExpandedRetriever:
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        graph_store: Optional[SQLiteGraphStore] = None,
        alpha: float = 0.20,
        citation_weight: float = 0.70,
        statute_weight: float = 0.30,
        seed_k: int = 10,
        max_provision_df: int = 25,
        min_provision_df: int = 2
    ):
        self.config = config or load_config()
        self.graph = graph_store or SQLiteGraphStore(preload_index=True)
        if not self.graph._in_memory_loaded:
            self.graph.load_in_memory_index()

        self.alpha = alpha
        self.citation_weight = citation_weight
        self.statute_weight = statute_weight
        self.seed_k = seed_k
        self.max_provision_df = max_provision_df
        self.min_provision_df = min_provision_df
        self.total_corpus_docs = 782

        # Initialize base retrieval components
        self.bm25 = BM25Retriever(self.config["bm25"]["db_path"])
        self.dense = DenseRetriever(
            self.config["embedding"]["model_name"],
            index_path="data/indexes/dense.faiss",
            doc_ids_path="data/indexes/dense_doc_ids.json"
        )
        self.hybrid = HybridRetriever(k=self.config["hybrid"]["rrf_k"])

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        enable_graph: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents using either Hybrid Baseline or Hybrid + Graph Expansion.
        Default is enable_graph=False to preserve the baseline retrieval path.
        """
        t0 = time.perf_counter()

        # Step 1: Hybrid Retrieval Baseline
        fetch_k = max(top_k, self.seed_k) * self.config["hybrid"]["bm25_fetch_multiplier"]
        b_res, _ = self.bm25.search(query, top_k=fetch_k)
        d_res, _ = self.dense.search(query, top_k=fetch_k)
        raw_hybrid = self.hybrid.combine(b_res, d_res, top_k=max(top_k, self.seed_k))

        if not enable_graph or not raw_hybrid:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return [
                {
                    "document_id": r["document_id"],
                    "fused_score": round(r["score"], 5),
                    "hybrid_score": round(r["score"], 5),
                    "graph_boost": 0.0,
                    "is_graph_discovered": False,
                    "expansion_provenance": [{"type": "text_hybrid_seed", "seed_rank": idx + 1}],
                    "rank": idx + 1,
                    "latency_ms": elapsed_ms,
                    "retrieval_method": "hybrid_baseline"
                }
                for idx, r in enumerate(raw_hybrid[:top_k])
            ]

        # Step 2: Graph Expansion from Top Seed Documents
        seed_results = raw_hybrid[:self.seed_k]
        hybrid_scores = {}
        candidate_provenance = defaultdict(list)

        for rank, r in enumerate(seed_results):
            doc_id = r["document_id"]
            recip_score = 1.0 / (rank + 1)
            hybrid_scores[doc_id] = recip_score
            candidate_provenance[doc_id].append({
                "type": "text_hybrid_seed",
                "seed_rank": rank + 1,
                "seed_score": round(recip_score, 4)
            })

        graph_scores = defaultdict(float)

        for seed_doc_id, seed_score in hybrid_scores.items():
            seed_node_id = f"doc:{seed_doc_id}"

            # 2a. 1-hop Citation Expansion (Judgments cited by seed)
            cited_edges = self.graph.get_cited_judgments(seed_node_id)
            for edge in cited_edges:
                target_doc = edge["target_node_id"].replace("doc:", "")
                mention_factor = min(edge.get("mention_count", 1), 3) / 3.0
                boost = self.citation_weight * seed_score * mention_factor
                graph_scores[target_doc] += boost
                candidate_provenance[target_doc].append({
                    "type": "citation_expansion",
                    "direction": "cited_by",
                    "via_seed": seed_doc_id,
                    "mention_count": edge.get("mention_count", 1)
                })

            # 2b. 1-hop Citation Expansion (Judgments that cite seed)
            citing_edges = self.graph.get_citing_judgments(seed_node_id)
            for edge in citing_edges:
                source_doc = edge["source_node_id"].replace("doc:", "")
                mention_factor = min(edge.get("mention_count", 1), 3) / 3.0
                boost = self.citation_weight * seed_score * mention_factor
                graph_scores[source_doc] += boost
                candidate_provenance[source_doc].append({
                    "type": "citation_expansion",
                    "direction": "cites",
                    "via_seed": seed_doc_id,
                    "mention_count": edge.get("mention_count", 1)
                })

            # 2c. Shared Grounded Statutory Provision Expansion with IDF Filtering
            provisions = self.graph.get_provisions_mentioned(seed_node_id)
            for prov in provisions:
                prov_node_id = prov["target_node_id"]
                prov_type = prov.get("provision_type", "")
                prov_name = prov.get("provision_name", prov_node_id)

                # Skip bare ungrounded sections or entire Acts
                if "unspecified" in prov_node_id or prov_type == "Act":
                    continue

                df = self.graph.get_provision_df(prov_node_id)
                # Apply IDF filter: skip ubiquitous umbrella provisions (df > max_provision_df) or singleton (df < min_provision_df)
                if df > self.max_provision_df or df < self.min_provision_df:
                    continue

                # Standard smoothed IDF calculation
                idf = math.log((self.total_corpus_docs - df + 0.5) / (df + 0.5) + 1.0)
                # Specific Sections and Rules carry higher discriminative weight than constitutional Articles
                type_multiplier = 0.50 if prov_type == "Article" else (0.75 if prov_type == "Schedule" else 1.0)
                prov_weight = self.statute_weight * type_multiplier * (idf / 4.5)

                co_judgments = self.graph.get_judgments_mentioning_provision(prov_node_id)
                for co_doc_node in co_judgments:
                    co_doc = co_doc_node.replace("doc:", "")
                    if co_doc != seed_doc_id:
                        boost = (prov_weight / max(len(co_judgments), 1)) * seed_score
                        graph_scores[co_doc] += boost
                        candidate_provenance[co_doc].append({
                            "type": "statutory_expansion",
                            "via_seed": seed_doc_id,
                            "provision_id": prov_node_id,
                            "provision_name": prov_name,
                            "provision_df": df,
                            "idf": round(idf, 3)
                        })

        # Step 3: Score Fusion
        all_candidate_ids = set(hybrid_scores.keys()).union(graph_scores.keys())
        fused_candidates = []

        max_graph_score = max(graph_scores.values()) if graph_scores else 1.0
        if max_graph_score == 0:
            max_graph_score = 1.0

        for doc_id in all_candidate_ids:
            h_score = hybrid_scores.get(doc_id, 0.0)
            norm_g_score = graph_scores.get(doc_id, 0.0) / max_graph_score
            fused_score = h_score + (self.alpha * norm_g_score)

            fused_candidates.append({
                "document_id": doc_id,
                "fused_score": round(fused_score, 5),
                "hybrid_score": round(h_score, 5),
                "graph_boost": round(self.alpha * norm_g_score, 5),
                "is_graph_discovered": (doc_id not in hybrid_scores),
                "expansion_provenance": candidate_provenance.get(doc_id, []),
                "retrieval_method": "hybrid_plus_graph_expansion"
            })

        # Sort by fused score descending, then by hybrid_score descending as tie-breaker
        fused_candidates.sort(key=lambda x: (x["fused_score"], x["hybrid_score"]), reverse=True)
        top_results = fused_candidates[:top_k]

        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        for rank, r in enumerate(top_results):
            r["rank"] = rank + 1
            r["latency_ms"] = elapsed_ms

        return top_results

