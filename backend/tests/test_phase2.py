"""Comprehensive tests for Phase 2: Backend APIs, BHASHINI Utilities, Document Ingestion, and Hybrid RAG.
"""

import io
import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.config import Settings, get_settings
from app.services.bhashini_utils import (
    BhashiniService,
    detect_language,
    detect_language_heuristic,
    generate_mock_wav_base64,
    is_dummy_or_empty_key,
    speech_to_text,
    text_to_speech,
    translate_text,
)
from app.services.rag_pipeline import RAGPipeline, simple_tokenize
from app.routers.upload import (
    chunk_text,
    extract_text_from_docx,
    extract_text_from_pdf,
    extract_text_from_txt,
    sanitize_filename,
)


# ==========================================
# 1. BHASHINI Utilities Tests
# ==========================================

def test_is_dummy_key():
    assert is_dummy_or_empty_key("") is True
    assert is_dummy_or_empty_key(None) is True
    assert is_dummy_or_empty_key("your_bhashini_udyat_api_key_here") is True
    assert is_dummy_or_empty_key("placeholder") is True
    assert is_dummy_or_empty_key("abc") is True
    assert is_dummy_or_empty_key("valid_production_secret_key_12345") is False


def test_detect_language_heuristic():
    assert detect_language_heuristic("नमस्ते आप कैसे हैं?") == "hi"
    assert detect_language_heuristic("வணக்கம் எப்படி இருக்கிறீர்கள்?") == "ta"
    assert detect_language_heuristic("నమస్కారం ఎలా ఉన్నారు?") == "te"
    assert detect_language_heuristic("নমস্কার আপনি কেমন আছেন?") == "bn"
    assert detect_language_heuristic("What is the penalty for murder in BNS?") == "en"
    assert detect_language_heuristic("") == "en"


def test_generate_mock_wav():
    wav_b64 = generate_mock_wav_base64(duration_seconds=0.2, sample_rate=8000)
    assert isinstance(wav_b64, str)
    assert len(wav_b64) > 50
    # Decode and check RIFF / WAVE headers
    import base64
    raw_bytes = base64.b64decode(wav_b64)
    assert raw_bytes[:4] == b"RIFF"
    assert raw_bytes[8:12] == b"WAVE"
    assert raw_bytes[12:16] == b"fmt "


@pytest.mark.asyncio
async def test_bhashini_service_fallbacks(monkeypatch):
    # Temporarily clear BHASHINI environment variables specifically for this fallback test
    monkeypatch.setenv("BHASHINI_UDYAT_KEY", "")
    monkeypatch.setenv("BHASHINI_INFERENCE_KEY", "")
    get_settings.cache_clear()

    svc = BhashiniService(settings=get_settings())
    assert svc.is_configured() is False

    # Detection
    lang = await svc.detect_language("चोरी की सजा क्या है?")
    assert lang == "hi"

    # Translation
    hi_to_en = await svc.translate_text("चोरी की सजा क्या है?", "hi", "en")
    assert hi_to_en == "What is the punishment for theft?"

    en_to_hi = await svc.translate_text("Hello", "en", "hi")
    assert en_to_hi == "नमस्ते"

    same_lang = await svc.translate_text("Same language", "en", "en")
    assert same_lang == "Same language"

    # TTS
    audio_b64 = await svc.text_to_speech("कानूनी सलाह", "hi")
    assert audio_b64 is not None
    assert len(audio_b64) > 40

    # ASR
    transcription = await svc.speech_to_text(audio_b64, "hi")
    assert "कानूनी" in transcription or len(transcription) > 0

    get_settings.cache_clear()


# ==========================================
# 2. Text Extraction & Chunking Tests
# ==========================================

def test_sanitize_filename():
    assert sanitize_filename("../../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("legal file (1).docx") == "legal_file__1_.docx"
    assert sanitize_filename("test.pdf") == "test.pdf"


def test_chunk_text():
    text = (
        "Paragraph 1 contains important legal context about criminal law. "
        "It sets out the general principles of liability and justice.\n\n"
        "Paragraph 2 discusses procedural requirements such as filing an FIR under BNSS Section 173. "
        "Every citizen has the right to file an FIR at any police station (Zero FIR).\n\n"
        "Paragraph 3 covers bail conditions and rights of the accused upon arrest."
    )
    chunks = chunk_text(text, chunk_size=120, chunk_overlap=20)
    assert len(chunks) >= 3
    for c in chunks:
        assert len(c) > 0

    # Empty text
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_extract_text_from_txt():
    content = "Legal Aid Service guidelines for rural citizens.".encode("utf-8")
    extracted = extract_text_from_txt(content)
    assert len(extracted) == 1
    assert "Legal Aid Service" in extracted[0][0]
    assert extracted[0][1] == 1


def test_extract_text_from_docx():
    import docx
    doc = docx.Document()
    doc.add_paragraph("First paragraph regarding Consumer Protection Act.")
    doc.add_paragraph("Second paragraph regarding grievance redressal.")
    table = doc.add_table(rows=1, cols=2)
    table.rows[0].cells[0].text = "Form 1"
    table.rows[0].cells[1].text = "Application for Bail"

    bio = io.BytesIO()
    doc.save(bio)
    bio.seek(0)

    extracted = extract_text_from_docx(bio.read(), "test.docx")
    assert len(extracted) == 1
    text = extracted[0][0]
    assert "Consumer Protection Act" in text
    assert "Application for Bail" in text


def test_extract_text_from_pdf():
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Bharatiya Sakshya Adhiniyam section 63 electronic records.")
    pdf_bytes = doc.tobytes()
    doc.close()

    extracted = extract_text_from_pdf(pdf_bytes, "test_evidence.pdf")
    assert len(extracted) == 1
    assert "Bharatiya Sakshya Adhiniyam" in extracted[0][0]
    assert extracted[0][1] == 1


# ==========================================
# 3. Hybrid RAG Pipeline Tests
# ==========================================

def test_simple_tokenize():
    tokens = simple_tokenize("FIR under Section 154 CrPC / 173 BNSS!")
    assert "fir" in tokens
    assert "section" in tokens
    assert "154" in tokens
    assert "crpc" in tokens
    assert "173" in tokens
    assert "bnss" in tokens


def test_rag_pipeline_initialization_and_search():
    pipeline = RAGPipeline()
    pipeline.initialize()

    assert pipeline.initialized is True
    assert len(pipeline.documents) >= 10

    # Search for murder (IPC 302 -> BNS 103)
    results_murder = pipeline.search("murder punishment death section 302", top_k=3)
    assert len(results_murder) > 0
    top_murder = results_murder[0]
    assert "103" in top_murder["text"] or "302" in top_murder["text"]
    assert top_murder["score"] > 0
    assert "dense_score" in top_murder
    assert "bm25_score" in top_murder

    # Search for cheating (IPC 420 -> BNS 318)
    results_cheating = pipeline.search("cheating dishonestly inducing property 420", top_k=3)
    assert len(results_cheating) > 0
    top_cheating = results_cheating[0]
    assert "420" in top_cheating["text"] or "318" in top_cheating["text"]

    # Search for electronic records (Evidence Act 65B -> BSA 63)
    results_evidence = pipeline.search("electronic records evidence emails server logs 65B", top_k=3)
    assert len(results_evidence) > 0
    top_evidence = results_evidence[0]
    assert "65B" in top_evidence["text"] or "63" in top_evidence["text"]

    # Empty query should return empty list gracefully
    assert pipeline.search("") == []
    assert pipeline.search("   ") == []


def test_rag_pipeline_dynamic_ingestion():
    pipeline = RAGPipeline()
    pipeline.initialize()
    initial_count = len(pipeline.documents)

    custom_text = (
        "The Lok Adalat (People's Court) is an alternative dispute resolution mechanism in India. "
        "Disputes pending in court or at pre-litigation stage can be settled amicably with no court fees."
    )
    added = pipeline.add_documents(
        texts=[custom_text],
        metadatas=[{"source": "test_upload", "type": "adjudication"}]
    )
    assert added == 1
    assert len(pipeline.documents) == initial_count + 1

    # Search specifically for the added text
    results = pipeline.search("Lok Adalat alternative dispute resolution amicable", top_k=1)
    assert len(results) > 0
    assert "Lok Adalat" in results[0]["text"]
    assert results[0]["metadata"]["source"] == "test_upload"


# ==========================================
# 4. FastAPI Endpoint Integration Tests
# ==========================================

def test_api_health():
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy", "service": "nyayavarta-api"}


def test_api_upload_txt():
    with TestClient(app) as client:
        content = (
            "Right to Information Act (RTI), 2005 empowers Indian citizens to request information "
            "from public authorities to promote transparency and accountability in governance."
        ).encode("utf-8")

        response = client.post(
            "/api/upload",
            files={"file": ("rti_handbook.txt", io.BytesIO(content), "text/plain")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "rti_handbook.txt"
        assert data["chunks_created"] >= 1
        assert "Successfully extracted and indexed" in data["message"]


def test_api_upload_invalid_extension():
    with TestClient(app) as client:
        response = client.post(
            "/api/upload",
            files={"file": ("script.exe", io.BytesIO(b"binary data"), "application/octet-stream")}
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]


def test_api_upload_empty_file():
    with TestClient(app) as client:
        response = client.post(
            "/api/upload",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")}
        )
        assert response.status_code == 400
        assert "empty" in response.json()["detail"].lower()


def test_api_upload_pdf():
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Consumer Protection Act provides consumer dispute redressal commissions.")
    pdf_bytes = doc.tobytes()
    doc.close()

    with TestClient(app) as client:
        response = client.post(
            "/api/upload",
            files={"file": ("consumer_rights.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == "consumer_rights.pdf"
        assert data["chunks_created"] >= 1
        assert "Successfully extracted and indexed" in data["message"]
