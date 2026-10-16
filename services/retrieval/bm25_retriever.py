"""
BM25 Retriever using SQLite FTS5.

Milestone 3.1 improvements:
- Persistent connection with WAL mode, mmap (256MB), and cache pragmas
- AND-based queries with bounded fallback to OR for high recall without disjunctive blowup
- Legal term normalization (e.g., 'Cr.P.C.' -> 'CrPC', 'I.P.C.' -> 'IPC')
- Single-letter uppercase/digit preservation (e.g., 'Section 6A', 'Article 21A')
- Token limit to avoid massive disjunctive queries
- Median and p95 latency tracking
"""
import sqlite3
import json
import time
import re


class BM25Retriever:
    MAX_QUERY_TOKENS = 30  # Limit tokens to avoid slow OR-explosion

    def __init__(self, db_path="data/indexes/bm25.db"):
        self.db_path = db_path
        self._conn = None

    @property
    def conn(self):
        """Lazy persistent connection with optimized pragmas."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            # Performance pragmas
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA cache_size=-64000")  # 64 MB cache
            self._conn.execute("PRAGMA mmap_size=268435456")  # 256 MB mmap
            self._conn.execute("PRAGMA synchronous=NORMAL")
        return self._conn

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE VIRTUAL TABLE IF NOT EXISTS legal_docs USING fts5(
                document_id UNINDEXED,
                case_title,
                full_text,
                tokenize="porter unicode61"
            );
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS doc_metadata (
                document_id TEXT PRIMARY KEY,
                metadata_json TEXT
            );
        ''')
        conn.commit()
        conn.close()

    def index_documents(self, docs):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for doc in docs:
            cursor.execute('''
                INSERT INTO legal_docs (document_id, case_title, full_text)
                VALUES (?, ?, ?)
            ''', (doc["document_id"], doc.get("case_title", ""), doc.get("full_text", "")))

            cursor.execute('''
                INSERT OR REPLACE INTO doc_metadata (document_id, metadata_json)
                VALUES (?, ?)
            ''', (doc["document_id"], json.dumps(doc)))

        conn.commit()
        conn.close()

    QUERY_STOPWORDS = {
        "what", "are", "the", "and", "for", "to", "an", "of", "in", "is", "by", "on",
        "at", "with", "from", "that", "this", "which", "how", "does", "can", "as", "be",
        "or", "it", "its", "was", "were", "will", "would", "could", "should", "has", "have"
    }

    @staticmethod
    def sanitize_query(query):
        """
        Clean query for FTS5 syntax safety while preserving legal terms.
        - Normalizes acronyms with dots: 'Cr.P.C.' -> 'CrPC', 'I.P.C.' -> 'IPC'
        - Keeps alphanumeric, spaces, hyphens (for terms like 'anti-defection')
        - Preserves single uppercase letters/digits ('6A', '21A', 'Schedule 10')
        - Filters non-discriminative conversational query stopwords
        - Deduplicates tokens while maintaining original case for acronyms
        - Limits token count to MAX_QUERY_TOKENS
        """
        # 1. Collapse dotted legal abbreviations (e.g., Cr.P.C. -> CrPC, u/s. -> us)
        q = re.sub(r'(?<=[A-Za-z0-9])\.(?=[A-Za-z0-9])', '', query)

        # 2. Strip FTS5 operators and special punctuation, keep hyphens
        cleaned = re.sub(r'[^\w\s\-]', ' ', q)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()

        # 3. Tokenize, deduplicate, filter
        tokens = cleaned.split()
        seen = set()
        unique_tokens = []
        for t in tokens:
            t_lower = t.lower()
            if t_lower not in seen and (len(t) > 1 or t.isupper() or t.isdigit()):
                seen.add(t_lower)
                unique_tokens.append(t)

        # 4. Filter conversational query stopwords to keep substantive legal terms
        filtered = [t for t in unique_tokens if t.lower() not in BM25Retriever.QUERY_STOPWORDS]
        tokens_to_return = filtered if filtered else unique_tokens

        return tokens_to_return[:BM25Retriever.MAX_QUERY_TOKENS]

    def search(self, query, top_k=10, mode="AND"):
        """
        Search with FTS5.

        Args:
            query: Natural language query string
            top_k: Number of results to return
            mode: "AND" (default, precise & fast) or "OR" (broader recall)
        """
        start_time = time.time()

        tokens = self.sanitize_query(query)
        if not tokens:
            return [], time.time() - start_time

        # Build FTS5 query
        separator = " AND " if mode == "AND" else " OR "
        fts_query = separator.join(f'"{t}"' for t in tokens)

        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT document_id, bm25(legal_docs) as score
                FROM legal_docs
                WHERE legal_docs MATCH ?
                ORDER BY score
                LIMIT ?
            ''', (fts_query, top_k))
            results = cursor.fetchall()
        except sqlite3.OperationalError:
            if mode == "AND":
                return self.search(query, top_k, mode="OR")
            return [], time.time() - start_time

        # If AND returns fewer than top_k results, supplement with bounded OR
        if mode == "AND" and len(results) < top_k:
            existing_ids = {r[0] for r in results}
            or_results = self._search_or_fallback(tokens, top_k, existing_ids)
            results.extend(or_results)
            results = results[:top_k]

        latency = time.time() - start_time
        return [{"document_id": r[0], "score": r[1]} for r in results], latency

    def _search_or_fallback(self, tokens, top_k, exclude_ids):
        """Bounded OR fallback for supplementing AND results."""
        fts_query = " OR ".join(f'"{t}"' for t in tokens[:15])  # Cap at 15 tokens
        cursor = self.conn.cursor()
        try:
            cursor.execute('''
                SELECT document_id, bm25(legal_docs) as score
                FROM legal_docs
                WHERE legal_docs MATCH ?
                ORDER BY score
                LIMIT ?
            ''', (fts_query, top_k * 2))
            results = cursor.fetchall()
            return [r for r in results if r[0] not in exclude_ids][:top_k]
        except sqlite3.OperationalError:
            return []
