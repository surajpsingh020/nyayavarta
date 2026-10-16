class HybridRetriever:
    def __init__(self, k=60):
        self.k = k
        
    def combine(self, bm25_results, dense_results, top_k=10):
        # bm25_results and dense_results are lists of {"document_id": id, "score": score}
        scores = {}
        
        # Rank BM25
        for rank, res in enumerate(bm25_results):
            doc_id = res["document_id"]
            if doc_id not in scores:
                scores[doc_id] = 0.0
            scores[doc_id] += 1.0 / (self.k + rank + 1)
            
        # Rank Dense
        for rank, res in enumerate(dense_results):
            doc_id = res["document_id"]
            if doc_id not in scores:
                scores[doc_id] = 0.0
            scores[doc_id] += 1.0 / (self.k + rank + 1)
            
        # Sort by hybrid RRF score
        sorted_results = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        
        return [{"document_id": doc_id, "score": score} for doc_id, score in sorted_results[:top_k]]
