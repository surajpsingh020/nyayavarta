from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from apps.api.main import app
from apps.api.routers.rag import get_rag_pipeline

client = TestClient(app)

def test_health_check():
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "environment": "development"}


def test_rag_query_success_mock():
    payload = {
        "query": "What is the legal standard for bail under Section 45 of PMLA?",
        "top_k_judgments": 2,
        "max_passages": 2,
        "enable_graph": False,
        "provider_type": "mock"
    }
    response = client.post("/v1/rag/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "grounding_status" in data
    assert "citation_validation" in data
    assert "evidence_passages" in data
    assert data["grounding_status"] in ["sufficient_evidence", "abstain_out_of_corpus", "abstain_contradicted", "abstain_unanswerable"]


def test_rag_query_invalid_provider_400():
    payload = {
        "query": "What is the legal standard for bail under Section 45 of PMLA?",
        "provider_type": "invalid_provider_name"
    }
    response = client.post("/v1/rag/query", json=payload)
    assert response.status_code == 400
    data = response.json()
    assert "Invalid provider_type 'invalid_provider_name'" in data["detail"]


def test_rag_query_service_unavailable_503():
    payload = {
        "query": "What is the legal standard for bail under Section 45 of PMLA?",
        "provider_type": "ollama"
    }
    with patch("apps.api.routers.rag.get_llm_provider", side_effect=RuntimeError("Ollama unreachable")):
        response = client.post("/v1/rag/query", json=payload)
        assert response.status_code == 503
        data = response.json()
        assert "Local LLM service is currently unavailable" in data["detail"]
        assert "Ollama unreachable" not in data["detail"]  # Traceback / raw error masked


def test_rag_query_timeout_504():
    payload = {
        "query": "What is the legal standard for bail under Section 45 of PMLA?",
        "provider_type": "mock"
    }
    mock_pipeline = MagicMock()
    mock_pipeline.query.side_effect = TimeoutError("Inference timed out after 240s")
    app.dependency_overrides[get_rag_pipeline] = lambda: mock_pipeline
    try:
        response = client.post("/v1/rag/query", json=payload)
        assert response.status_code == 504
        assert "Local LLM inference timed out" in response.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_rag_pipeline, None)


def test_rag_query_unexpected_exception_500_masked():
    payload = {
        "query": "What is the legal standard for bail under Section 45 of PMLA?",
        "provider_type": "mock"
    }
    mock_pipeline = MagicMock()
    mock_pipeline.query.side_effect = Exception("Sensitive internal server failure details")
    app.dependency_overrides[get_rag_pipeline] = lambda: mock_pipeline
    try:
        response = client.post("/v1/rag/query", json=payload)
        assert response.status_code == 500
        data = response.json()
        assert data["detail"] == "Internal server error during RAG query processing."
        assert "Sensitive internal server failure details" not in data["detail"]
    finally:
        app.dependency_overrides.pop(get_rag_pipeline, None)


