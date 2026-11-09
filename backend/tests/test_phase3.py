"""Comprehensive tests for Phase 3: Core Logic, LLM Orchestration, and /api/chat endpoint.
"""

import base64
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import UserProfile
from app.services.bhashini_utils import generate_mock_wav_base64
from app.services.llm_service import LLMService


# ==========================================
# 1. LLM Service Tests
# ==========================================

@pytest.mark.asyncio
async def test_llm_service_fallback_generation():
    service = LLMService()
    # Force client to None to test local deterministic generator
    original_client = service.client
    service.client = None

    result = await service.generate_legal_response(
        query="What is the punishment for cheating under Section 420 IPC?",
        retrieved_context=[{
            "text": "Old Law: IPC 420\nNew Law: BNS 318\nSubject: Cheating\nDescription: Cheating provisions.",
            "metadata": {"old_law": "IPC 420", "new_law": "BNS 318", "subject": "Cheating"},
            "score": 0.85
        }],
        user_profile=UserProfile.GENERAL
    )

    service.client = original_client

    assert "english_response" in result
    resp_text = result["english_response"]
    assert "420" in resp_text or "318" in resp_text
    assert "15100" in resp_text
    assert len(result["citations"]) > 0


@pytest.mark.asyncio
async def test_llm_service_profile_personas():
    service = LLMService()
    original_client = service.client
    service.client = None

    for profile in [UserProfile.STUDENT, UserProfile.PROFESSIONAL, UserProfile.SENIOR_CITIZEN]:
        result = await service.generate_legal_response(
            query="How to file an FIR?",
            retrieved_context=[],
            user_profile=profile
        )
        assert result["user_profile"] == profile.value
        assert len(result["english_response"]) > 100

    service.client = original_client


# ==========================================
# 2. /api/chat Integration Tests
# ==========================================

def test_chat_endpoint_text_query_hindi():
    with TestClient(app) as client:
        payload = {
            "text": "एफआईआर कैसे दर्ज करें?",
            "source_language": "hi",
            "user_profile": "general"
        }
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["original_query"] == "एफआईआर कैसे दर्ज करें?"
        assert len(data["english_query"]) > 0
        assert len(data["english_response"]) > 0
        assert len(data["regional_response"]) > 0
        assert isinstance(data["citations"], list)
        assert data["audio_base64"] is not None

        # Verify audio is valid base64
        audio_bytes = base64.b64decode(data["audio_base64"])
        assert len(audio_bytes) > 20


def test_chat_endpoint_text_query_english_student():
    with TestClient(app) as client:
        payload = {
            "text": "Explain Section 302 IPC transition to Section 103 BNS for murder.",
            "source_language": "en",
            "user_profile": "student"
        }
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert data["original_query"] == payload["text"]
        assert data["english_query"] == payload["text"]
        assert "103" in data["english_response"] or "302" in data["english_response"]
        assert len(data["citations"]) > 0


def test_chat_endpoint_senior_citizen_profile():
    with TestClient(app) as client:
        payload = {
            "text": "How can an elderly person seek protection from cruelty?",
            "source_language": "en",
            "user_profile": "senior_citizen"
        }
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert len(data["english_response"]) > 0
        # Check that legal aid helpline is mentioned
        assert "15100" in data["english_response"] or "legal aid" in data["english_response"].lower()


def test_chat_endpoint_audio_query():
    with TestClient(app) as client:
        audio_b64 = generate_mock_wav_base64(duration_seconds=0.2)
        payload = {
            "audio_base64": audio_b64,
            "source_language": "hi",
            "user_profile": "general"
        }
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert len(data["original_query"]) > 0
        assert len(data["english_response"]) > 0
        assert data["audio_base64"] is not None


def test_chat_endpoint_empty_input_validation():
    with TestClient(app) as client:
        payload = {
            "text": "",
            "source_language": "hi",
            "user_profile": "general"
        }
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 400
        assert "either text or audio_base64" in response.json()["detail"].lower()


def test_chat_endpoint_empty_rag_graceful_handling():
    with TestClient(app) as client:
        # A query completely unrelated to the seeded criminal laws
        payload = {
            "text": "What are the rules regarding maritime admiralty jurisdiction in outer continental shelf?",
            "source_language": "en",
            "user_profile": "professional"
        }
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert len(data["english_response"]) > 0
