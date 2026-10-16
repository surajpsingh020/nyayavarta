import os
import json
import time
from services.retrieval.bm25_retriever import BM25Retriever

PROCESSED_DIR = "data/processed/aws_sc"
INDEX_DIR = "data/indexes"

os.makedirs(INDEX_DIR, exist_ok=True)

def main():
    retriever = BM25Retriever(os.path.join(INDEX_DIR, "bm25.db"))
    
    # Remove existing index if it exists for a clean run
    if os.path.exists(os.path.join(INDEX_DIR, "bm25.db")):
        os.remove(os.path.join(INDEX_DIR, "bm25.db"))
        
    retriever.init_db()
    
    docs = []
    for file in os.listdir(PROCESSED_DIR):
        if file.endswith('.json'):
            with open(os.path.join(PROCESSED_DIR, file), "r", encoding="utf-8") as f:
                docs.append(json.load(f))
                
    print(f"Indexing {len(docs)} documents into BM25...")
    start_time = time.time()
    retriever.index_documents(docs)
    print(f"Indexing complete in {time.time() - start_time:.2f} seconds.")

if __name__ == "__main__":
    main()
