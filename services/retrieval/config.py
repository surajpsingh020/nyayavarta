"""
NyayaVarta Retrieval Model Configuration
Single source of truth for embedding model selection and settings.
"""
import json
import os

CONFIG_PATH = "data/indexes/retrieval_config.json"

DEFAULT_CONFIG = {
    "embedding": {
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "dimension": 384,
        "normalize": True,
        "similarity_metric": "cosine",
        "backend": "fastembed-onnx",
        "batch_size": 32,
        "max_seq_length": 512
    },
    "bm25": {
        "tokenizer": "porter unicode61",
        "default_top_k": 10,
        "query_mode": "AND",
        "db_path": "data/indexes/bm25.db"
    },
    "hybrid": {
        "rrf_k": 60,
        "bm25_fetch_multiplier": 3,
        "dense_fetch_multiplier": 3
    },
    "reranker": {
        "enabled": False,
        "model_name": "jinaai/jina-reranker-v1-turbo-en",
        "backend": "fastembed-onnx",
        "max_candidates": 30,
        "max_passage_length": 2048
    },
    "selection_rule": {
        "primary_metric": "recall_10",
        "tiebreaker_metric": "query_latency_ms",
        "tiebreaker_direction": "lower_is_better"
    },
    "version": "3.1.0"
}


def load_config():
    """Load retrieval config, creating default if missing."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_CONFIG.copy()


def save_config(config):
    """Save retrieval config."""
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)


def get_embedding_model():
    """Return the configured embedding model name."""
    return load_config()["embedding"]["model_name"]


def get_embedding_dimension():
    """Return the configured embedding dimension."""
    return load_config()["embedding"]["dimension"]


if __name__ == "__main__":
    save_config(DEFAULT_CONFIG)
    print(f"Config saved to {CONFIG_PATH}")
    print(json.dumps(DEFAULT_CONFIG, indent=2))
