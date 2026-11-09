"""Chat Router (/api/chat) for Nyayavarta Multilingual Legal Assistant.

Implements the complete Phase 3 orchestration flow:
1. Receive user text or base64 audio + profile + language.
2. Transcribe voice queries via BHASHINI ASR.
3. Translate regional text into English via BHASHINI NMT.
4. Retrieve relevant legal context using Hybrid RAG (FAISS + BM25).
5. Generate profile-tailored legal response with Gemini LLM,
   including old/new law mappings, citations, and NALSA/DLSA legal aid routing.
6. Translate response back to user's regional language.
7. Synthesize regional speech audio via BHASHINI TTS.
8. Return structured ChatResponse payload.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, status

from app.models.schemas import ChatRequest, ChatResponse, UserProfile
from app.services.bhashini_utils import (
    detect_language_heuristic,
    generate_mock_wav_base64,
    get_bhashini_service,
)
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", response_model=ChatResponse, summary="Process multilingual legal consultation query")
async def chat_endpoint(request: Request, payload: ChatRequest):
    """Multilingual, profile-aware legal consultation endpoint with Hybrid RAG and voice synthesis."""
    settings = getattr(request.app.state, "settings", None)
    rag_pipeline = getattr(request.app.state, "rag_pipeline", None)
    bhashini = get_bhashini_service()
    llm_service = LLMService(settings)

    # ---------------------------------------------------------
    # Step 1: Input Validation & Audio Transcription (ASR)
    # ---------------------------------------------------------
    user_text = payload.text.strip() if payload.text else ""
    source_lang = (payload.source_language or "hi").strip().lower()

    if not user_text and payload.audio_base64:
        logger.info(f"Received audio query in language '{source_lang}', performing speech-to-text transcription")
        user_text = await bhashini.speech_to_text(payload.audio_base64, language=source_lang)

    if not user_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either text or audio_base64 must be provided."
        )

    # Auto-detect language if source_language is generic or needs verification
    detected = detect_language_heuristic(user_text)
    if source_lang == "en" and detected != "en":
        source_lang = detected

    # ---------------------------------------------------------
    # Step 2: Translation to English (NMT)
    # ---------------------------------------------------------
    if source_lang != "en":
        logger.info(f"Translating query from '{source_lang}' to 'en'")
        english_query = await bhashini.translate_text(user_text, source_lang=source_lang, target_lang="en")
        # If BHASHINI returned mock tag or identical text, leverage Gemini for high-fidelity translation
        if english_query.startswith("[") or english_query == user_text:
            english_query = await llm_service.translate_with_llm(user_text, source_lang=source_lang, target_lang="en")
    else:
        english_query = user_text

    logger.info(f"English Query: {english_query}")

    # ---------------------------------------------------------
    # Step 3: Hybrid RAG Search (FAISS + BM25)
    # ---------------------------------------------------------
    top_k = getattr(settings, "TOP_K_RESULTS", 5) if settings else 5
    retrieved_docs = []
    if rag_pipeline:
        try:
            retrieved_docs = rag_pipeline.search(english_query, top_k=top_k)
            logger.info(f"Retrieved {len(retrieved_docs)} documents from hybrid RAG.")
        except Exception as e:
            logger.error(f"Error during RAG search: {e}")
            retrieved_docs = []

    # ---------------------------------------------------------
    # Step 4: Gemini LLM Generation (Persona + Citations + Aid)
    # ---------------------------------------------------------
    llm_result = await llm_service.generate_legal_response(
        query=english_query,
        retrieved_context=retrieved_docs,
        user_profile=payload.user_profile,
    )
    english_response = llm_result.get("english_response", "")
    citations = llm_result.get("citations", [])

    # ---------------------------------------------------------
    # Step 5: Translate Response to Regional Language
    # ---------------------------------------------------------
    if source_lang != "en":
        logger.info(f"Translating legal response from 'en' to '{source_lang}'")
        regional_response = await bhashini.translate_text(
            english_response, source_lang="en", target_lang=source_lang
        )
        # Use LLM translation fallback if BHASHINI returns mock placeholder
        if regional_response.startswith("[") or regional_response == english_response:
            regional_response = await llm_service.translate_with_llm(
                english_response, source_lang="en", target_lang=source_lang
            )
    else:
        regional_response = english_response

    # ---------------------------------------------------------
    # Step 6: Text-to-Speech (TTS)
    # ---------------------------------------------------------
    audio_base64: Optional[str] = None
    try:
        audio_base64 = await bhashini.text_to_speech(regional_response, language=source_lang)
    except Exception as e:
        logger.warning(f"TTS synthesis failed ({e}). Generating fallback audio.")
        audio_base64 = generate_mock_wav_base64()

    if not audio_base64:
        audio_base64 = generate_mock_wav_base64()

    # ---------------------------------------------------------
    # Step 7: Return Structured Response
    # ---------------------------------------------------------
    return ChatResponse(
        original_query=user_text,
        english_query=english_query,
        regional_response=regional_response,
        english_response=english_response,
        citations=citations,
        audio_base64=audio_base64,
    )
