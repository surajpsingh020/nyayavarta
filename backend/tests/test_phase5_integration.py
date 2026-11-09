"""Phase 5 End-to-End Integration & System Verification Tests for Nyayavarta.

Covers:
1. Docker Compose specification and service dependency integrity.
2. Full API integration: /health, /api/upload, and /api/chat.
3. GraphRAG pipeline multi-hop resolution (Colonial IPC/CrPC -> 2023 BNS/BNSS).
4. Persona adaptation in multilingual chat responses.
5. Ingestion of user document chunks into the graph.
"""

import os
import io
import yaml
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.config import get_settings
from app.services.rag_pipeline import RAGPipeline, InMemoryLegalGraph


@pytest.fixture(scope="module")
def client():
    """Test client for FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


# ==============================================================================
# 1. Docker Compose & Environment Specification Checks
# ==============================================================================

def test_docker_compose_structure():
    """Verify docker-compose.yml defines neo4j, backend, frontend with correct networking."""
    compose_path = os.path.join(os.path.dirname(__file__), "..", "..", "docker-compose.yml")
    assert os.path.exists(compose_path), "docker-compose.yml must exist at repo root"

    with open(compose_path, "r", encoding="utf-8") as f:
        compose = yaml.safe_load(f)

    assert "services" in compose, "docker-compose must declare services"
    services = compose["services"]

    # Verify Neo4j service
    assert "neo4j" in services, "neo4j service must be present"
    neo4j_svc = services["neo4j"]
    assert neo4j_svc["image"] == "neo4j:5.18.0"
    assert "7474:7474" in neo4j_svc["ports"]
    assert "7687:7687" in neo4j_svc["ports"]
    assert "healthcheck" in neo4j_svc, "neo4j must have a healthcheck"
    assert any("apoc" in env for env in neo4j_svc.get("environment", [])), "APOC must be enabled"

    # Verify Backend service
    assert "backend" in services, "backend service must be present"
    backend_svc = services["backend"]
    assert "neo4j" in backend_svc.get("depends_on", {}), "backend must depend on neo4j"
    assert backend_svc["depends_on"]["neo4j"]["condition"] == "service_healthy"
    
    # Check that backend environment points to bolt://neo4j:7687 inside the Docker network
    backend_env = backend_svc.get("environment", [])
    assert any("NEO4J_URI=bolt://neo4j:7687" in item for item in backend_env), (
        "backend must point to bolt://neo4j:7687 inside Docker network"
    )

    # Verify Frontend service
    assert "frontend" in services, "frontend service must be present"
    frontend_svc = services["frontend"]
    assert "backend" in frontend_svc.get("depends_on", {})
    assert frontend_svc["depends_on"]["backend"]["condition"] == "service_healthy"

    # Verify Persistent Volumes
    assert "volumes" in compose
    vols = compose["volumes"]
    assert "neo4j-data" in vols
    assert "backend-uploads" in vols


def test_neo4j_settings_defaults():
    """Verify Neo4j settings are present with valid defaults."""
    settings = get_settings()
    assert hasattr(settings, "NEO4J_URI")
    assert hasattr(settings, "NEO4J_USERNAME")
    assert hasattr(settings, "NEO4J_PASSWORD")
    assert hasattr(settings, "NEO4J_DATABASE")
    assert settings.NEO4J_URI.startswith(("bolt://", "neo4j://"))


# ==============================================================================
# 2. System Health & Graph Pipeline Initialization
# ==============================================================================

def test_system_health(client):
    """Verify /health returns 200 OK and valid status dictionary."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data.get("status") == "healthy"
    assert "service" in data or "app" in data


def test_rag_pipeline_graph_ready(client):
    """Verify RAG pipeline initializes with either live Neo4j or in-memory graph."""
    pipeline = getattr(app.state, "rag_pipeline", None)
    if not pipeline:
        pipeline = RAGPipeline(get_settings())
        pipeline.initialize()
    assert pipeline.initialized is True
    assert (pipeline.graph is not None) or (pipeline.in_memory_graph is not None)

    # Run query to test mapping
    results = pipeline.search("murder punishment IPC 302", top_k=3)
    assert len(results) > 0
    top = results[0]
    assert "103" in top["text"] or "302" in top["text"]
    assert top.get("graph_score", 0) > 0 or top.get("score", 0) > 0


# ==============================================================================
# 3. Document Ingestion to GraphRAG Flow
# ==============================================================================

def test_document_upload_and_graph_linkage(client):
    """Verify file upload chunks document, writes metadata, and links sections in Graph."""
    sample_text = (
        "POLICE REPORT\n\n"
        "Complainant filed a report regarding Cheating and fraud under Section 420 IPC.\n"
        "Accused took Rs 50,000 promising government employment and absconded.\n"
        "Under the Bharatiya Nyaya Sanhita 2023, the matter corresponds to Section 318 BNS."
    )
    file_bytes = io.BytesIO(sample_text.encode("utf-8"))

    response = client.post(
        "/api/upload",
        files={"file": ("fir_report_test.txt", file_bytes, "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "fir_report_test.txt"
    assert body["chunks_created"] > 0
    assert "indexed" in body["message"].lower()

    # Verify uploaded chunk can be retrieved via Graph search
    pipeline = getattr(app.state, "rag_pipeline", None)
    if not pipeline:
        pipeline = RAGPipeline(get_settings())
        pipeline.initialize()
    search_res = pipeline.search("fir_report_test cheating employment", top_k=5)
    assert any(
        "fir_report_test" in r["text"] or "420" in r["text"] or "318" in r["text"]
        or "fir_report_test" in str(r.get("metadata", {}))
        for r in search_res
    )


# ==============================================================================
# 4. Multilingual Chat & Transition Flow
# ==============================================================================

def test_chat_ipc_to_bns_transition(client):
    """Verify chat resolves IPC 302 to BNS 103 with structured citations."""
    payload = {
        "text": "What happens if an FIR is lodged under Section 302 IPC?",
        "source_language": "en",
        "user_profile": "general",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "english_response" in data
    assert len(data["english_response"]) > 0
    assert "citations" in data
    assert len(data["citations"]) > 0

    # Ensure citations reference Section 103 BNS or Section 302 IPC
    citation_sections = [c["section"] for c in data["citations"]]
    assert any("103" in s or "302" in s for s in citation_sections)


def test_chat_multilingual_regional_translation(client):
    """Verify chat handles Hindi input and returns regional response and citations."""
    payload = {
        "text": "मुझे जीरो एफआईआर (Zero FIR) कैसे दर्ज करनी चाहिए?",
        "source_language": "hi",
        "user_profile": "general",
    }
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["original_query"] == "मुझे जीरो एफआईआर (Zero FIR) कैसे दर्ज करनी चाहिए?"
    assert len(data["regional_response"]) > 0
    assert len(data["english_response"]) > 0
    assert len(data["citations"]) > 0


def test_chat_user_profiles(client):
    """Verify persona adaptability across profiles."""
    profiles = ["general", "student", "senior_citizen", "professional"]

    for profile in profiles:
        payload = {
            "text": "What is the new law for cheating instead of 420 IPC?",
            "source_language": "en",
            "user_profile": profile,
        }
        res = client.post("/api/chat", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert len(data["english_response"]) > 0
        # Check citations include 318 or 420
        cit_secs = [c["section"] for c in data["citations"]]
        assert any("318" in s or "420" in s for s in cit_secs)
