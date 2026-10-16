"""
Dense Retriever using FAISS and fastembed.
Uses the centralized retrieval config for model selection.
"""
import faiss
import numpy as np
from fastembed import TextEmbedding
import json
import time


class DenseRetriever:
    def __init__(self, model_name=None, index_path=None, doc_ids_path=None):
        """
        Initialize dense retriever.

        Args:
            model_name: Override model name (defaults to config)
            index_path: Path to FAISS index file
            doc_ids_path: Path to JSON file mapping index positions to doc IDs
        """
        from services.retrieval.config import load_config
        config = load_config()

        if model_name is None:
            model_name = config["embedding"]["model_name"]

        self.model_name = model_name
        self.normalize = config["embedding"].get("normalize", True)
        self.model = TextEmbedding(model_name=model_name)

        if index_path:
            self.index = faiss.read_index(index_path)
        else:
            self.index = None

        self.doc_ids = []
        if doc_ids_path:
            with open(doc_ids_path, "r", encoding="utf-8") as f:
                self.doc_ids = json.load(f)

    def search(self, query, top_k=10):
        """Search the FAISS index for similar documents."""
        start_time = time.time()

        if not self.index:
            return [], time.time() - start_time

        q_emb = list(self.model.embed([query]))[0]
        q_emb = np.array([q_emb], dtype="float32")

        if self.normalize:
            faiss.normalize_L2(q_emb)

        distances, indices = self.index.search(q_emb, top_k)
        latency = time.time() - start_time

        results = []
        for i, idx in enumerate(indices[0]):
            if 0 <= idx < len(self.doc_ids):
                results.append({
                    "document_id": self.doc_ids[idx],
                    "score": float(distances[0][i])
                })

        return results, latency
