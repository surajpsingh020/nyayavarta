import os
import json
import time
import psutil
import faiss
import numpy as np
from fastembed import TextEmbedding

PROCESSED_DIR = "data/processed/aws_sc"
EVAL_DIR = "evaluation"
MODELS = [
    "sentence-transformers/all-MiniLM-L6-v2",
    "BAAI/bge-small-en-v1.5"
]

def load_data():
    docs = []
    doc_ids = []
    for file in os.listdir(PROCESSED_DIR):
        if file.endswith('.json'):
            with open(os.path.join(PROCESSED_DIR, file), "r", encoding="utf-8") as f:
                doc = json.load(f)
                docs.append(doc.get("full_text", ""))
                doc_ids.append(doc["document_id"])
                
    with open(os.path.join(EVAL_DIR, "queries", "queries.json"), "r") as f:
        queries = json.load(f)
        
    with open(os.path.join(EVAL_DIR, "gold", "gold.json"), "r") as f:
        gold = json.load(f)
        
    return docs, doc_ids, queries, gold

def evaluate_model(model_name, docs, doc_ids, queries, gold):
    print(f"\n--- Evaluating {model_name} ---")
    
    # Track RAM before model load
    process = psutil.Process(os.getpid())
    ram_before = process.memory_info().rss
    
    # Load model
    model = TextEmbedding(model_name=model_name)
    
    # Track RAM after model load
    ram_after = process.memory_info().rss
    model_ram_mb = (ram_after - ram_before) / (1024 * 1024)
    print(f"Model RAM usage: {model_ram_mb:.2f} MB")
    
    # Indexing
    print("Encoding documents...")
    start_time = time.time()
    doc_embeddings = list(model.embed(docs, batch_size=32))
    doc_embeddings = np.array(doc_embeddings, dtype="float32")
    index_time = time.time() - start_time
    print(f"Indexing time: {index_time:.2f} seconds")
    
    dimension = doc_embeddings.shape[1]
    
    # Build FAISS index
    index = faiss.IndexFlatIP(dimension)
    index.add(doc_embeddings)
    
    # Querying
    print("Evaluating queries...")
    latencies = []
    recall_at_5 = 0
    recall_at_10 = 0
    mrr = 0.0
    
    gold_dict = {g["query_id"]: g["relevant_document_ids"] for g in gold}
    
    for q in queries:
        start_q = time.time()
        q_emb = list(model.embed([q["query_text"]]))[0]
        q_emb = np.array([q_emb], dtype="float32")
        distances, indices = index.search(q_emb, 10)
        latencies.append(time.time() - start_q)
        
        retrieved_ids = [doc_ids[idx] for idx in indices[0]]
        relevant_ids = gold_dict.get(q["query_id"], [])
        
        # Calculate Metrics
        hit_ranks = [i+1 for i, r_id in enumerate(retrieved_ids) if r_id in relevant_ids]
        if hit_ranks:
            first_hit = hit_ranks[0]
            mrr += 1.0 / first_hit
            if first_hit <= 5: recall_at_5 += 1
            if first_hit <= 10: recall_at_10 += 1
            
    num_queries = len(queries)
    avg_latency = sum(latencies) / num_queries
    recall_5_val = recall_at_5 / num_queries
    recall_10_val = recall_at_10 / num_queries
    mrr_val = mrr / num_queries
    
    print(f"Recall@5: {recall_5_val:.4f}")
    print(f"Recall@10: {recall_10_val:.4f}")
    print(f"MRR: {mrr_val:.4f}")
    print(f"Avg Query Latency: {avg_latency*1000:.2f} ms")
    
    return {
        "model": model_name,
        "dimension": dimension,
        "index_time_s": index_time,
        "query_latency_ms": avg_latency * 1000,
        "recall_5": recall_5_val,
        "recall_10": recall_10_val,
        "mrr": mrr_val,
        "ram_usage_mb": model_ram_mb
    }

def main():
    docs, doc_ids, queries, gold = load_data()
    results = []
    
    for model_name in MODELS:
        res = evaluate_model(model_name, docs, doc_ids, queries, gold)
        results.append(res)
        
    with open("docs/retrieval/EMBEDDING_BENCHMARK.json", "w") as f:
        json.dump(results, f, indent=4)
        
    # Write Markdown
    md = "# Embedding Model Benchmark\n\n"
    md += "| Model | Dim | RAM (MB) | Index Time (s) | Latency (ms) | Recall@5 | Recall@10 | MRR |\n"
    md += "|---|---|---|---|---|---|---|---|\n"
    for r in results:
        md += f"| {r['model']} | {r['dimension']} | {r['ram_usage_mb']:.1f} | {r['index_time_s']:.1f} | {r['query_latency_ms']:.1f} | {r['recall_5']:.3f} | {r['recall_10']:.3f} | {r['mrr']:.3f} |\n"
        
    with open("docs/retrieval/EMBEDDING_BENCHMARK.md", "w") as f:
        f.write(md)
        
    print("Benchmarking complete.")

if __name__ == "__main__":
    main()
