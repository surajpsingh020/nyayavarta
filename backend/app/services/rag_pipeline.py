"""Neo4j Knowledge Graph & GraphRAG Pipeline for Nyayavarta.

Integrates LangChain's Neo4jGraph to perform graph traversal over Indian criminal law
transitions (IPC -> BNS, CrPC -> BNSS, Evidence Act -> BSA), statutory relationships,
and dynamic document chunk connections.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


def simple_tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase alphanumeric tokens.

    Preserves legal codes like '302', 'bns', 'ipc', '420', 'fir'.
    """
    if not text:
        return []
    return re.findall(r"\b\w+\b", text.lower())


def extract_section_numbers(text: str) -> List[str]:
    """Extract legal section numbers like 302, 103, 420, 318, 65B, 3(5), etc."""
    if not text:
        return []
    # Match standalone numbers, lettered sections (65B, 498A), or subsections (3(5))
    matches = re.findall(r"\b(\d+[A-Za-z]?|\d+\(\d+\))\b", text)
    return list(set(matches))


# ==============================================================================
# Cypher Schema & Seeding Templates
# ==============================================================================

CYPHER_SCHEMA_OUTLINE = """
// ==========================================
// Nyayavarta Neo4j GraphRAG Schema Definition
// ==========================================

// Node Labels & Properties:
// (:Act {code: STRING (Unique), title: STRING, era: 'OLD'|'NEW', year: INTEGER})
// (:Section {id: STRING (Unique), section_number: STRING, act_code: STRING, subject: STRING, description: STRING, key_changes: STRING})
// (:Offence {name: STRING (Unique), category: STRING})
// (:LegalAid {name: STRING (Unique), helpline: STRING, type: STRING})
// (:DocumentChunk {id: STRING (Unique), filename: STRING, page: INTEGER, chunk_index: INTEGER, text: STRING, source: STRING})

// Relationship Types:
// (:Section)-[:BELONGS_TO]->(:Act)
// (:Section)-[:REPLACED_BY {notes: STRING, transition_date: '2024-07-01'}]->(:Section)
// (:Section)-[:REPLACES]->(:Section)
// (:Section)-[:COVERS_OFFENCE]->(:Offence)
// (:Section)-[:ROUTES_TO_AID]->(:LegalAid)
// (:DocumentChunk)-[:REFERENCES_SECTION]->(:Section)
"""

CYPHER_CONSTRAINTS = [
    "CREATE CONSTRAINT act_code_unique IF NOT EXISTS FOR (a:Act) REQUIRE a.code IS UNIQUE",
    "CREATE CONSTRAINT section_id_unique IF NOT EXISTS FOR (s:Section) REQUIRE s.id IS UNIQUE",
    "CREATE CONSTRAINT offence_name_unique IF NOT EXISTS FOR (o:Offence) REQUIRE o.name IS UNIQUE",
    "CREATE CONSTRAINT aid_name_unique IF NOT EXISTS FOR (aid:LegalAid) REQUIRE aid.name IS UNIQUE",
    "CREATE CONSTRAINT doc_chunk_unique IF NOT EXISTS FOR (d:DocumentChunk) REQUIRE d.id IS UNIQUE",
]

CYPHER_SEED_ACTS = """
MERGE (ipc:Act {code: 'IPC'})
  SET ipc.title = 'Indian Penal Code, 1860', ipc.era = 'OLD', ipc.year = 1860
MERGE (bns:Act {code: 'BNS'})
  SET bns.title = 'Bharatiya Nyaya Sanhita, 2023', bns.era = 'NEW', bns.year = 2023
MERGE (crpc:Act {code: 'CrPC'})
  SET crpc.title = 'Code of Criminal Procedure, 1973', crpc.era = 'OLD', crpc.year = 1973
MERGE (bnss:Act {code: 'BNSS'})
  SET bnss.title = 'Bharatiya Nagarik Suraksha Sanhita, 2023', bnss.era = 'NEW', bnss.year = 2023
MERGE (iea:Act {code: 'IEA'})
  SET iea.title = 'Indian Evidence Act, 1872', iea.era = 'OLD', iea.year = 1872
MERGE (bsa:Act {code: 'BSA'})
  SET bsa.title = 'Bharatiya Sakshya Adhiniyam, 2023', bsa.era = 'NEW', bsa.year = 2023
MERGE (aid:LegalAid {name: 'NALSA / DLSA'})
  SET aid.helpline = '15100', aid.type = 'Free Legal Aid & Representation'
"""

CYPHER_SEED_LAW = """
MERGE (oldSec:Section {id: $old_id})
  SET oldSec.section_number = $old_sec_num,
      oldSec.act_code = $old_act_code,
      oldSec.subject = $subject,
      oldSec.description = $description

MERGE (newSec:Section {id: $new_id})
  SET newSec.section_number = $new_sec_num,
      newSec.act_code = $new_act_code,
      newSec.subject = $subject,
      newSec.description = $description,
      newSec.key_changes = $key_changes

MERGE (off:Offence {name: $subject})

WITH oldSec, newSec, off
MATCH (oldAct:Act {code: $old_act_code})
MERGE (oldSec)-[:BELONGS_TO]->(oldAct)

WITH oldSec, newSec, off
MATCH (newAct:Act {code: $new_act_code})
MERGE (newSec)-[:BELONGS_TO]->(newAct)

WITH oldSec, newSec, off
MERGE (oldSec)-[r:REPLACED_BY]->(newSec)
  SET r.notes = $key_changes, r.transition_date = '2024-07-01'
MERGE (newSec)-[:REPLACES]->(oldSec)
MERGE (oldSec)-[:COVERS_OFFENCE]->(off)
MERGE (newSec)-[:COVERS_OFFENCE]->(off)

WITH newSec
MATCH (aid:LegalAid {name: 'NALSA / DLSA'})
MERGE (newSec)-[:ROUTES_TO_AID]->(aid)
"""

CYPHER_GRAPH_TRAVERSAL = """
MATCH (oldSec:Section)-[r:REPLACED_BY]->(newSec:Section)
OPTIONAL MATCH (oldSec)-[:BELONGS_TO]->(oldAct:Act)
OPTIONAL MATCH (newSec)-[:BELONGS_TO]->(newAct:Act)
OPTIONAL MATCH (newSec)-[:COVERS_OFFENCE]->(off:Offence)
OPTIONAL MATCH (newSec)-[:ROUTES_TO_AID]->(aid:LegalAid)
WHERE
  oldSec.section_number IN $sections
  OR newSec.section_number IN $sections
  OR ANY(term IN $terms WHERE
       toLower(oldSec.subject) CONTAINS term
       OR toLower(newSec.subject) CONTAINS term
       OR toLower(off.name) CONTAINS term
       OR toLower(oldSec.description) CONTAINS term
       OR toLower(newSec.description) CONTAINS term
       OR toLower(r.notes) CONTAINS term
  )
RETURN
  oldSec.id AS old_id,
  oldSec.section_number AS old_section,
  oldAct.code AS old_act,
  oldSec.subject AS subject,
  oldSec.description AS old_description,
  newSec.id AS new_id,
  newSec.section_number AS new_section,
  newAct.code AS new_act,
  newSec.description AS new_description,
  r.notes AS key_changes,
  off.name AS offence,
  aid.name AS legal_aid_name,
  aid.helpline AS helpline
LIMIT $limit
"""

CYPHER_DOC_CHUNK_SEARCH = """
MATCH (doc:DocumentChunk)
WHERE ANY(term IN $terms WHERE toLower(doc.text) CONTAINS term)
OPTIONAL MATCH (doc)-[:REFERENCES_SECTION]->(s:Section)
RETURN
  doc.id AS id,
  doc.filename AS filename,
  doc.page AS page,
  doc.text AS text,
  s.section_number AS linked_section
LIMIT $limit
"""

CYPHER_INSERT_DOC_CHUNK = """
MERGE (doc:DocumentChunk {id: $chunk_id})
  SET doc.filename = $filename,
      doc.page = $page,
      doc.chunk_index = $chunk_index,
      doc.text = $text,
      doc.source = 'upload'
WITH doc
UNWIND $mentioned_sections AS secNum
MATCH (s:Section) WHERE s.section_number = secNum
MERGE (doc)-[:REFERENCES_SECTION]->(s)
"""


# ==============================================================================
# In-Memory Graph Fallback (Resilient when Neo4j container is offline)
# ==============================================================================

class InMemoryLegalGraph:
    """In-memory Knowledge Graph simulating Neo4j node/edge traversal for testing and offline development."""

    def __init__(self):
        self.sections: Dict[str, dict] = {}       # id -> section dict
        self.acts: Dict[str, dict] = {}           # code -> act dict
        self.offences: Dict[str, dict] = {}       # name -> offence dict
        self.replacements: Dict[str, str] = {}     # old_id -> new_id
        self.key_changes: Dict[str, str] = {}      # (old_id, new_id) -> notes
        self.doc_chunks: List[dict] = []

    def seed_law(
        self,
        old_id: str,
        old_sec_num: str,
        old_act_code: str,
        new_id: str,
        new_sec_num: str,
        new_act_code: str,
        subject: str,
        description: str,
        key_changes: str,
    ):
        self.sections[old_id] = {
            "id": old_id,
            "section_number": old_sec_num,
            "act_code": old_act_code,
            "subject": subject,
            "description": description,
        }
        self.sections[new_id] = {
            "id": new_id,
            "section_number": new_sec_num,
            "act_code": new_act_code,
            "subject": subject,
            "description": description,
            "key_changes": key_changes,
        }
        self.offences[subject] = {"name": subject}
        self.replacements[old_id] = new_id
        self.key_changes[(old_id, new_id)] = key_changes

    def add_doc_chunk(self, chunk_id: str, filename: str, page: int, chunk_index: int, text: str, mentioned_sections: List[str], metadata: Optional[dict] = None):
        self.doc_chunks.append({
            "id": chunk_id,
            "filename": filename,
            "page": page,
            "chunk_index": chunk_index,
            "text": text,
            "mentioned_sections": mentioned_sections,
            "metadata": metadata or {},
        })

    def search(self, sections: List[str], terms: List[str], limit: int = 5) -> List[dict]:
        matched_items = []
        seen_pairs = set()
        upper_sections = {s.upper() for s in sections}

        # 1. Match section transitions and score by relevance
        for old_id, new_id in self.replacements.items():
            old_sec = self.sections.get(old_id, {})
            new_sec = self.sections.get(new_id, {})
            pair_key = (old_id, new_id)

            score = 0.0
            old_snum = str(old_sec.get("section_number", "")).upper()
            new_snum = str(new_sec.get("section_number", "")).upper()

            # Exact section match is highest priority (+10 points)
            if old_snum in upper_sections or new_snum in upper_sections:
                score += 10.0

            # Keyword matching score
            full_text = f"{old_sec.get('subject', '')} {old_sec.get('description', '')} {new_sec.get('description', '')} {self.key_changes.get(pair_key, '')}".lower()
            matching_terms = sum(1 for term in terms if len(term) > 2 and term in full_text)
            if matching_terms > 0:
                score += matching_terms

            if score > 0 and pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                matched_items.append((score, {
                    "old_id": old_id,
                    "old_section": old_sec.get("section_number"),
                    "old_act": old_sec.get("act_code"),
                    "subject": old_sec.get("subject"),
                    "old_description": old_sec.get("description"),
                    "new_id": new_id,
                    "new_section": new_sec.get("section_number"),
                    "new_act": new_sec.get("act_code"),
                    "new_description": new_sec.get("description"),
                    "key_changes": self.key_changes.get(pair_key, ""),
                    "offence": old_sec.get("subject"),
                    "legal_aid_name": "NALSA / DLSA",
                    "helpline": "15100",
                }))

        # Sort descending by match score
        matched_items.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in matched_items[:limit]]

    def search_docs(self, terms: List[str], limit: int = 5) -> List[dict]:
        results = []
        for doc in self.doc_chunks:
            text_lower = doc["text"].lower()
            if any(term in text_lower for term in terms if len(term) > 2):
                results.append({
                    "id": doc["id"],
                    "filename": doc["filename"],
                    "page": doc["page"],
                    "text": doc["text"],
                    "linked_section": doc["mentioned_sections"][0] if doc["mentioned_sections"] else None,
                    "metadata": doc.get("metadata", {}),
                })
                if len(results) >= limit:
                    break
        return results


# ==============================================================================
# Helper Parsing Functions
# ==============================================================================

def parse_law_identifier(law_str: str) -> tuple[str, str, str]:
    """Parse 'Indian Penal Code (IPC), 1860 - Section 302' into (id, act_code, section_number)."""
    law_clean = law_str.strip()

    # Determine act code
    if "IPC" in law_clean or "Indian Penal Code" in law_clean:
        act_code = "IPC"
    elif "BNS" in law_clean or "Bharatiya Nyaya Sanhita" in law_clean:
        act_code = "BNS"
    elif "CrPC" in law_clean or "Code of Criminal Procedure" in law_clean:
        act_code = "CrPC"
    elif "BNSS" in law_clean or "Bharatiya Nagarik Suraksha Sanhita" in law_clean:
        act_code = "BNSS"
    elif "Evidence" in law_clean or "BSA" in law_clean or "Bharatiya Sakshya" in law_clean:
        act_code = "BSA" if "BSA" in law_clean or "Bharatiya Sakshya" in law_clean else "IEA"
    else:
        act_code = "LAW"

    # Extract section number (e.g. 302, 103, 65B, 3(5))
    sec_match = re.search(r"Section\s+([0-9A-Za-z\(\)]+)", law_clean, re.IGNORECASE)
    sec_num = sec_match.group(1) if sec_match else "0"
    node_id = f"{act_code}_{sec_num}".replace("(", "_").replace(")", "")
    return node_id, act_code, sec_num


# ==============================================================================
# Main GraphRAG Pipeline
# ==============================================================================

class RAGPipeline:
    """GraphRAG pipeline powered by LangChain's Neo4jGraph and sparse BM25 search."""

    def __init__(self, settings=None):
        from app.config import get_settings
        self.settings = settings or get_settings()

        self.graph = None               # LangChain Neo4jGraph instance
        self.is_connected = False        # Neo4j connection status
        self.in_memory_graph = InMemoryLegalGraph()

        # Hybrid BM25 sparse index over entity text and uploaded chunks
        self.bm25 = None
        self.tokenized_corpus: List[List[str]] = []
        self.corpus_docs: List[dict] = []

        self.initialized = False

    def _init_neo4j(self):
        """Attempt connection to Neo4j database using LangChain's Neo4jGraph."""
        uri = getattr(self.settings, "NEO4J_URI", "bolt://localhost:7687")
        username = getattr(self.settings, "NEO4J_USERNAME", "neo4j")
        password = getattr(self.settings, "NEO4J_PASSWORD", "nyayavarta_secret")
        database = getattr(self.settings, "NEO4J_DATABASE", "neo4j")

        try:
            from langchain_community.graphs import Neo4jGraph
            logger.info(f"Attempting connection to Neo4j Knowledge Graph at {uri}...")
            self.graph = Neo4jGraph(
                url=uri,
                username=username,
                password=password,
                database=database,
                timeout=3.0,
            )
            self.is_connected = True
            logger.info("Successfully connected to Neo4j Knowledge Graph via LangChain Neo4jGraph.")

            # Create Constraints
            for constraint in CYPHER_CONSTRAINTS:
                try:
                    self.graph.query(constraint)
                except Exception as ce:
                    logger.debug(f"Constraint notice ({constraint}): {ce}")

            # Seed Acts and Legal Aid
            self.graph.query(CYPHER_SEED_ACTS)

        except Exception as e:
            self.is_connected = False
            self.graph = None
            logger.warning(
                f"Neo4j Knowledge Graph not reachable at {uri} ({e}). "
                "Operating in in-memory GraphRAG mode. "
                "Start your local Neo4j Docker container to enable live Cypher graph queries."
            )

    def _init_bm25(self):
        """Build BM25 keyword index over all indexed graph entities and document chunks."""
        if not self.tokenized_corpus:
            self.bm25 = None
            return

        try:
            from rank_bm25 import BM25Okapi
            self.bm25 = BM25Okapi(self.tokenized_corpus)
        except Exception as e:
            logger.warning(f"Could not initialize BM25Okapi ({e}).")
            self.bm25 = None

    def initialize(self, knowledge_base_path: Optional[str] = None):
        """Initialize the Knowledge Graph with the 10 core Indian law mappings."""
        self._init_neo4j()

        # Locate seed knowledge_base.json
        if not knowledge_base_path:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            knowledge_base_path = os.path.join(base_dir, "data", "knowledge_base.json")

        if os.path.exists(knowledge_base_path):
            try:
                with open(knowledge_base_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                laws = data.get("laws", [])

                for law in laws:
                    old_law_str = law.get("old_law", "")
                    new_law_str = law.get("new_law", "")
                    subject = law.get("subject", "")
                    description = law.get("description", "")
                    key_changes = law.get("key_changes", "")

                    old_id, old_act, old_sec = parse_law_identifier(old_law_str)
                    new_id, new_act, new_sec = parse_law_identifier(new_law_str)

                    # 1. Seed In-Memory Fallback Graph
                    self.in_memory_graph.seed_law(
                        old_id=old_id,
                        old_sec_num=old_sec,
                        old_act_code=old_act,
                        new_id=new_id,
                        new_sec_num=new_sec,
                        new_act_code=new_act,
                        subject=subject,
                        description=description,
                        key_changes=key_changes,
                    )

                    # 2. Seed Live Neo4j Graph if connected
                    if self.is_connected and self.graph:
                        try:
                            self.graph.query(
                                CYPHER_SEED_LAW,
                                params={
                                    "old_id": old_id,
                                    "old_sec_num": old_sec,
                                    "old_act_code": old_act,
                                    "new_id": new_id,
                                    "new_sec_num": new_sec,
                                    "new_act_code": new_act,
                                    "subject": subject,
                                    "description": description,
                                    "key_changes": key_changes,
                                }
                            )
                        except Exception as qe:
                            logger.error(f"Error seeding law {old_id}->{new_id} in Neo4j: {qe}")

                    # 3. Add to BM25 Corpus
                    formatted_text = (
                        f"Old Law: {old_law_str}\n"
                        f"New Law: {new_law_str}\n"
                        f"Subject: {subject}\n"
                        f"Description: {description}\n"
                        f"Key Changes: {key_changes}"
                    )
                    self._add_to_corpus(
                        text=formatted_text,
                        metadata={
                            "old_law": old_law_str,
                            "new_law": new_law_str,
                            "subject": subject,
                            "key_changes": key_changes,
                            "source": "knowledge_graph",
                            "type": "law_mapping",
                        }
                    )

                self._init_bm25()
                logger.info(f"Seeded {len(laws)} criminal law mappings into GraphRAG pipeline.")
            except Exception as e:
                logger.error(f"Failed to load seed knowledge base from {knowledge_base_path}: {e}")
        else:
            logger.warning(f"Knowledge base file not found at {knowledge_base_path}")

        # Refresh schema on Neo4jGraph
        if self.is_connected and self.graph:
            try:
                self.graph.refresh_schema()
                logger.info("Neo4jGraph schema successfully refreshed.")
            except Exception as se:
                logger.debug(f"Schema refresh notice: {se}")

        self.initialized = True

    def _add_to_corpus(self, text: str, metadata: dict):
        """Append an entity or document to the BM25 search corpus."""
        doc_id = len(self.corpus_docs)
        self.corpus_docs.append({
            "id": doc_id,
            "text": text,
            "metadata": metadata,
        })
        self.tokenized_corpus.append(simple_tokenize(text))

    def add_documents(self, texts: List[str], metadatas: Optional[List[dict]] = None) -> int:
        """Dynamically ingest uploaded document chunks into the Knowledge Graph and BM25 index."""
        if not texts:
            return 0

        if metadatas is None:
            metadatas = [{} for _ in texts]

        for i, (text, meta) in enumerate(zip(texts, metadatas)):
            filename = meta.get("filename", "user_upload")
            page = meta.get("page", 1)
            chunk_idx = meta.get("chunk_index", i)
            chunk_id = f"chunk_{filename}_{page}_{chunk_idx}".replace(" ", "_")
            mentioned_secs = extract_section_numbers(text)

            chunk_meta = {
                "filename": filename,
                "page": page,
                "chunk_index": chunk_idx,
                "source": meta.get("source", "upload"),
                "type": meta.get("type", "user_document"),
            }
            chunk_meta.update(meta)

            # 1. In-memory graph addition
            self.in_memory_graph.add_doc_chunk(
                chunk_id=chunk_id,
                filename=filename,
                page=page,
                chunk_index=chunk_idx,
                text=text,
                mentioned_sections=mentioned_secs,
                metadata=chunk_meta,
            )

            # 2. Neo4j Cypher insertion if connected
            if self.is_connected and self.graph:
                try:
                    self.graph.query(
                        CYPHER_INSERT_DOC_CHUNK,
                        params={
                            "chunk_id": chunk_id,
                            "filename": filename,
                            "page": page,
                            "chunk_index": chunk_idx,
                            "text": text,
                            "mentioned_sections": mentioned_secs,
                        }
                    )
                except Exception as ge:
                    logger.error(f"Failed to insert DocumentChunk {chunk_id} into Neo4j: {ge}")

            # 3. Add to BM25 search corpus
            self._add_to_corpus(
                text=text,
                metadata=chunk_meta,
            )

        self._init_bm25()
        return len(texts)

    def search(self, query: str, top_k: Optional[int] = None) -> List[dict]:
        """Perform GraphRAG search combining Cypher knowledge graph traversal and BM25 relevance."""
        if not query or not query.strip():
            return []

        k = top_k or getattr(self.settings, "TOP_K_RESULTS", 5)
        sections = extract_section_numbers(query)
        tokens = simple_tokenize(query)

        # Filter out common short stopwords
        stopwords = {"what", "is", "the", "under", "for", "and", "or", "in", "to", "of", "a", "an", "how", "can"}
        search_terms = [t for t in tokens if t not in stopwords and len(t) > 2]

        graph_results = []

        # -------------------------------------------------------------
        # 1. Cypher Graph Traversal (Neo4j or In-Memory Graph Fallback)
        # -------------------------------------------------------------
        if self.is_connected and self.graph:
            try:
                # Query section transitions in Neo4j
                neo_records = self.graph.query(
                    CYPHER_GRAPH_TRAVERSAL,
                    params={
                        "sections": sections,
                        "terms": search_terms,
                        "limit": k,
                    }
                )
                for rec in neo_records:
                    old_law = f"{rec.get('old_act', 'Act')} - Section {rec.get('old_section', '')}"
                    new_law = f"{rec.get('new_act', 'Act')} - Section {rec.get('new_section', '')}"
                    subject = rec.get("subject", "")
                    formatted_text = (
                        f"Old Law: {old_law}\n"
                        f"New Law: {new_law}\n"
                        f"Subject: {subject}\n"
                        f"Description: {rec.get('new_description', rec.get('old_description', ''))}\n"
                        f"Key Changes: {rec.get('key_changes', '')}\n"
                        f"Legal Aid: {rec.get('legal_aid_name', 'NALSA / DLSA')} (Helpline: {rec.get('helpline', '15100')})"
                    )
                    graph_results.append({
                        "text": formatted_text,
                        "metadata": {
                            "old_law": old_law,
                            "new_law": new_law,
                            "subject": subject,
                            "key_changes": rec.get("key_changes", ""),
                            "source": "neo4j_knowledge_graph",
                            "type": "law_mapping",
                        },
                        "score": 1.0,
                    })

                # Query uploaded document chunks in Neo4j
                doc_records = self.graph.query(
                    CYPHER_DOC_CHUNK_SEARCH,
                    params={
                        "terms": search_terms,
                        "limit": k,
                    }
                )
                for d in doc_records:
                    graph_results.append({
                        "text": d.get("text", ""),
                        "metadata": {
                            "filename": d.get("filename", ""),
                            "page": d.get("page", 1),
                            "source": "neo4j_document_chunk",
                            "type": "user_document",
                        },
                        "score": 0.9,
                    })

            except Exception as ge:
                logger.warning(f"Error querying Neo4j Knowledge Graph ({ge}). Using in-memory graph.")
                self.is_connected = False
                graph_results = []

        # Fallback to In-Memory Graph if Neo4j is offline or returned no results
        if not graph_results:
            mem_law_records = self.in_memory_graph.search(sections, search_terms, limit=k)
            for rec in mem_law_records:
                old_law = f"{rec['old_act']} - Section {rec['old_section']}"
                new_law = f"{rec['new_act']} - Section {rec['new_section']}"
                formatted_text = (
                    f"Old Law: {old_law}\n"
                    f"New Law: {new_law}\n"
                    f"Subject: {rec['subject']}\n"
                    f"Description: {rec.get('new_description', rec.get('old_description', ''))}\n"
                    f"Key Changes: {rec['key_changes']}\n"
                    f"Legal Aid: {rec['legal_aid_name']} (Helpline: {rec['helpline']})"
                )
                graph_results.append({
                    "text": formatted_text,
                    "metadata": {
                        "old_law": old_law,
                        "new_law": new_law,
                        "subject": rec["subject"],
                        "key_changes": rec["key_changes"],
                        "source": "in_memory_knowledge_graph",
                        "type": "law_mapping",
                    },
                    "score": 0.95,
                })

            mem_doc_records = self.in_memory_graph.search_docs(search_terms, limit=k)
            for d in mem_doc_records:
                graph_results.append({
                    "text": d["text"],
                    "metadata": d.get("metadata") or {
                        "filename": d["filename"],
                        "page": d["page"],
                        "source": "upload",
                        "type": "user_document",
                    },
                    "score": 0.85,
                })

        # -------------------------------------------------------------
        # 2. Sparse BM25 Keyword Scoring
        # -------------------------------------------------------------
        bm25_results = []
        if self.bm25 and tokens:
            try:
                raw_scores = self.bm25.get_scores(tokens)
                max_bm25 = max(raw_scores) if len(raw_scores) > 0 else 0.0
                if max_bm25 > 0:
                    ranked_indices = sorted(range(len(raw_scores)), key=lambda i: raw_scores[i], reverse=True)
                    for idx in ranked_indices[:k]:
                        if raw_scores[idx] > 0:
                            doc = self.corpus_docs[idx]
                            bm25_results.append({
                                "text": doc["text"],
                                "metadata": doc["metadata"],
                                "score": float(raw_scores[idx] / max_bm25),
                            })
            except Exception as be:
                logger.debug(f"BM25 search error: {be}")

        # -------------------------------------------------------------
        # 3. Hybrid Fusion: Merge Graph Traversal + BM25
        # -------------------------------------------------------------
        combined: Dict[str, dict] = {}

        # Prioritize Graph Traversal (weight 0.7) and BM25 (weight 0.3)
        for item in graph_results:
            key = item["metadata"].get("new_law") or item["metadata"].get("filename") or item["text"][:60]
            g_score = float(item["score"])
            combined[key] = {
                "text": item["text"],
                "metadata": item["metadata"],
                "score": round(0.7 * g_score, 4),
                "graph_score": round(g_score, 4),
                "dense_score": round(g_score, 4),  # for backward compatibility
                "bm25_score": 0.0,
            }

        for item in bm25_results:
            key = item["metadata"].get("new_law") or item["metadata"].get("filename") or item["text"][:60]
            b_score = float(item["score"])
            if key in combined:
                combined[key]["score"] = round(combined[key]["score"] + (0.3 * b_score), 4)
                combined[key]["bm25_score"] = round(b_score, 4)
            else:
                combined[key] = {
                    "text": item["text"],
                    "metadata": item["metadata"],
                    "score": round(0.5 * b_score, 4),
                    "graph_score": 0.0,
                    "dense_score": 0.0,
                    "bm25_score": round(b_score, 4),
                }

        results = list(combined.values())
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:k]

    @property
    def documents(self) -> List[dict]:
        """Backward-compatibility property for existing test assertions."""
        return self.corpus_docs

    def get_cypher_schema(self) -> str:
        """Return the Graph schema definition or live schema string from Neo4j."""
        if self.is_connected and self.graph:
            try:
                return self.graph.schema
            except Exception:
                pass
        return CYPHER_SCHEMA_OUTLINE
