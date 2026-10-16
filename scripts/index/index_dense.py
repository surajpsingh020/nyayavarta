"""
Dense index builder using fastembed and FAISS CPU.
Uses centralized configuration and selection rule.
"""
import os
import json
import faiss
from fastembed import TextEmbedding
import numpy as np
import time

from services.retrieval.config import load_config, save_config

PROCESSED_DIR = "data/processed/aws_sc"
INDEX_DIR = "data/indexes"
BENCHMARK_FILE = "docs/retrieval/EMBEDDING_BENCHMARK.json"

os.makedirs(INDEX_DIR, exist_ok=True)


def select_best_model():
    """
    Select best model prioritizing Recall@10, with latency as tie-breaker.
    Fallback to config default if benchmark file does not exist.
    """
    config = load_config()
    default_model = config["embedding"]["model_name"]

    if not os.path.exists(BENCHMARK_FILE):
        print(f"Benchmark file not found. Using default model: {default_model}")
        return default_model, config["embedding"]["dimension"]

    with open(BENCHMARK_FILE, "r", encoding="utf-8") as f:
        results = json.load(f)

    if not results:
        return default_model, config["embedding"]["dimension"]

    # Sort key: primary = recall_10 (descending), tie-breaker = query_latency_ms (ascending)
    def model_sort_key(entry):
        recall_10 = entry.get("recall_10", 0.0)
        latency = entry.get("query_latency_ms", float("inf"))
        return (recall_10, -latency)

    best_entry = max(results, key=model_sort_key)
    best_model_name = best_entry["model"]
    dim = best_entry.get("dimension", 384)
    print(f"Selected model: {best_model_name} (Recall@10: {best_entry.get('recall_10', 0):.4f}, Latency: {best_entry.get('query_latency_ms', 0):.2f}ms)")
    return best_model_name, dim


def main():
    best_model_name, dim = select_best_model()

    # Update centralized config
    config = load_config()
    config["embedding"]["model_name"] = best_model_name
    config["embedding"]["dimension"] = dim
    save_config(config)

    docs = []
    doc_ids = []
    for file in os.listdir(PROCESSED_DIR):
        if file.endswith('.json'):
            with open(os.path.join(PROCESSED_DIR, file), "r", encoding="utf-8") as f:
                doc = json.load(f)
                docs.append(doc.get("full_text", ""))
                doc_ids.append(doc["document_id"])

    print(f"Loaded {len(docs)} documents. Encoding with {best_model_name}...")
    start_time = time.time()
    model = TextEmbedding(model_name=best_model_name)
    doc_embeddings = list(model.embed(docs, batch_size=32))
    doc_embeddings = np.array(doc_embeddings, dtype="float32")
    encoding_time = time.time() - start_time
    print(f"Encoding complete in {encoding_time:.2f}s.")

    # Explicit L2 normalization for cosine similarity compatibility with IndexFlatIP
    if config["embedding"].get("normalize", True):
        faiss.normalize_L2(doc_embeddings)

    dimension = doc_embeddings.shape[1]
    index = faiss.IndexFlatIP(dimension)
    index.add(doc_embeddings)

    # Save index and metadata
    index_path = os.path.join(INDEX_DIR, "dense.faiss")
    faiss.write_index(index, index_path)

    with open(os.path.join(INDEX_DIR, "dense_doc_ids.json"), "w", encoding="utf-8") as f:
        json.dump(doc_ids, f, indent=4)

    # Save legacy config for backwards compatibility
    with open(os.path.join(INDEX_DIR, "dense_model_config.json"), "w", encoding="utf-8") as f:
        json.dump({
            "model": best_model_name,
            "dim": dimension,
            "normalize": True,
            "similarity_metric": "cosine",
            "indexed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "document_count": len(doc_ids)
        }, f, indent=4)

    print(f"Dense indexing complete. Indexed {len(doc_ids)} docs. Saved to {index_path}.")


if __name__ == "__main__":
    main()
