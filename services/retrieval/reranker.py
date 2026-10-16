"""
Reranker using fastembed cross-encoder.

Milestone 3.1: Fixed dead code, added passage truncation to reduce
latency on long legal judgments, disabled by default per config.
"""
from fastembed.rerank.cross_encoder import TextCrossEncoder


class Reranker:
    def __init__(self, model_name="jinaai/jina-reranker-v1-turbo-en",
                 max_passage_length=2048):
        self.model = TextCrossEncoder(model_name=model_name)
        self.max_passage_length = max_passage_length

    def rerank(self, query, candidates, doc_texts, top_k=10):
        """
        Rerank candidates using a cross-encoder.

        Args:
            query: The search query
            candidates: List of {"document_id": id, "score": score}
            doc_texts: Dict mapping document_id to full_text
            top_k: Number of results to return

        Returns:
            Reranked list of candidates with cross_score added
        """
        if not candidates:
            return []

        # Truncate passages to reduce latency on long judgments
        documents = []
        for cand in candidates:
            text = doc_texts.get(cand["document_id"], "")
            # Use first max_passage_length chars as the scoring passage
            if len(text) > self.max_passage_length:
                text = text[:self.max_passage_length]
            documents.append(text)

        # Score all pairs
        scores = list(self.model.rerank(query, documents))

        for i, cand in enumerate(candidates):
            cand["cross_score"] = float(scores[i])

        # Sort by cross-encoder score descending
        sorted_candidates = sorted(
            candidates, key=lambda x: x["cross_score"], reverse=True
        )
        return sorted_candidates[:top_k]
