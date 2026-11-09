"""Unit and integration tests for Neo4j GraphRAG pipeline in Nyayavarta.
"""

import pytest
from app.services.rag_pipeline import (
    RAGPipeline,
    InMemoryLegalGraph,
    extract_section_numbers,
    parse_law_identifier,
    CYPHER_SCHEMA_OUTLINE,
)


def test_extract_section_numbers():
    text = "What is the punishment under Section 302 of IPC compared to Section 103 of BNS?"
    secs = extract_section_numbers(text)
    assert "302" in secs
    assert "103" in secs

    text2 = "Admissibility under Section 65B and arrest memo in Section 41"
    secs2 = extract_section_numbers(text2)
    assert "65B" in secs2
    assert "41" in secs2


def test_parse_law_identifier():
    node_id, act_code, sec_num = parse_law_identifier("Indian Penal Code (IPC), 1860 - Section 302")
    assert act_code == "IPC"
    assert sec_num == "302"
    assert "IPC_302" in node_id

    node_id2, act_code2, sec_num2 = parse_law_identifier("Bharatiya Nyaya Sanhita (BNS), 2023 - Section 103")
    assert act_code2 == "BNS"
    assert sec_num2 == "103"
    assert "BNS_103" in node_id2


def test_in_memory_legal_graph_traversal():
    graph = InMemoryLegalGraph()
    graph.seed_law(
        old_id="IPC_302",
        old_sec_num="302",
        old_act_code="IPC",
        new_id="BNS_103",
        new_sec_num="103",
        new_act_code="BNS",
        subject="Murder",
        description="Whoever commits murder shall be punished with death or life imprisonment.",
        key_changes="Section number changed from 302 to 103.",
    )

    # Search by section number
    results = graph.search(sections=["302"], terms=["murder"], limit=1)
    assert len(results) == 1
    res = results[0]
    assert res["old_section"] == "302"
    assert res["new_section"] == "103"
    assert res["subject"] == "Murder"
    assert res["helpline"] == "15100"


def test_graph_rag_pipeline_search_and_schema():
    pipeline = RAGPipeline()
    pipeline.initialize()

    schema = pipeline.get_cypher_schema()
    assert "Act" in schema
    assert "Section" in schema
    assert "REPLACED_BY" in schema

    # Search murder transition
    results = pipeline.search("What is Section 302 in the new criminal law?", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert "103" in top["text"]
    assert "302" in top["text"]
    assert top["metadata"]["source"] in ["neo4j_knowledge_graph", "in_memory_knowledge_graph"]
    assert "score" in top
    assert "graph_score" in top

    # Search cheating transition
    results_cheat = pipeline.search("cheating Section 420 IPC to BNS", top_k=2)
    assert len(results_cheat) > 0
    assert "318" in results_cheat[0]["text"]

    # Search FIR transition
    results_fir = pipeline.search("How to file zero FIR under CrPC 154 or BNSS 173?", top_k=2)
    assert len(results_fir) > 0
    assert "173" in results_fir[0]["text"] or "154" in results_fir[0]["text"]


def test_graph_rag_dynamic_document_ingestion():
    pipeline = RAGPipeline()
    pipeline.initialize()
    initial_docs = len(pipeline.documents)

    custom_text = (
        "Bail application filed under Section 437 CrPC / Section 480 BNSS for a non-bailable offence. "
        "The accused must demonstrate lack of flight risk."
    )
    added = pipeline.add_documents(
        texts=[custom_text],
        metadatas=[{"filename": "bail_petition.pdf", "page": 1, "source": "user_petition"}]
    )
    assert added == 1
    assert len(pipeline.documents) == initial_docs + 1

    search_res = pipeline.search("bail application Section 480 BNSS flight risk", top_k=1)
    assert len(search_res) > 0
    assert "bail application" in search_res[0]["text"].lower()
