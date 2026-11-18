"""Chat Router (/api/chat) for Nyayavarta Multilingual Legal Assistant.

Implements the complete GraphRAG orchestration flow:
1. Receive user text or base64 audio + profile + language.
2. Transcribe voice queries via BHASHINI ASR or browser Web Speech.
3. Translate regional text into English via Gemini cascade.
4. Retrieve relevant legal context using GraphRAG (Neo4j Cypher Traversal + BM25).
5. Generate accurate, profile-tailored legal response with Gemini LLM,
   including old/new law mappings, relevant statutory citations, and NALSA/DLSA legal aid routing.
6. Translate response cleanly into user's selected target language (Odia, Hindi, Marathi, etc.).
7. Synthesize speech audio.
8. Return structured ChatResponse payload.
"""

import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request, status

from app.models.schemas import ChatRequest, ChatResponse, TranslateRequest, TranslateResponse, UserProfile
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
    """Multilingual legal consultation endpoint with GraphRAG and multi-model synthesis."""
    settings = getattr(request.app.state, "settings", None)
    rag_pipeline = getattr(request.app.state, "rag_pipeline", None)
    bhashini = get_bhashini_service()
    llm_service = LLMService(settings)

    try:
        # ---------------------------------------------------------
        # Step 1: Input Validation & Audio Transcription
        # ---------------------------------------------------------
        user_text = payload.text.strip() if payload.text else ""
        target_output_lang = (payload.source_language or "auto").strip().lower()

        if not user_text and payload.audio_base64:
            logger.info("Received audio query, performing multimodal speech recognition & language identification")
            try:
                asr_data = await llm_service.transcribe_and_detect_audio(payload.audio_base64)
                if asr_data.get("transcription"):
                    user_text = asr_data["transcription"]
                    detected_audio_lang = asr_data.get("detected_language")
                    if detected_audio_lang and (target_output_lang in ("auto", "hi", "en") or payload.source_language == "auto"):
                        target_output_lang = detected_audio_lang
                        logger.info(f"Auto-recognized speech language as '{target_output_lang}' from audio input")
            except Exception as e:
                logger.warning(f"Multimodal ASR failed ({e}). Trying Bhashini...")

            if not user_text:
                try:
                    user_text = await bhashini.speech_to_text(payload.audio_base64, language=target_output_lang if target_output_lang != "auto" else "hi")
                except Exception as e:
                    logger.warning(f"Audio transcription error ({e}).")
                    user_text = "Legal consultation query"

        if not user_text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either text or audio_base64 must be provided."
            )

        # Detect the actual script/language of the input text
        detected_input_lang = detect_language_heuristic(user_text)
        if detected_input_lang != "en" and (target_output_lang in ("auto", "en") or payload.source_language == "auto"):
            target_output_lang = detected_input_lang

        if target_output_lang == "auto":
            target_output_lang = detected_input_lang if detected_input_lang != "en" else "hi"

        # ---------------------------------------------------------
        # Step 2: Translation to English for Legal Search
        # ---------------------------------------------------------
        english_query = user_text
        query_lang = detected_input_lang if detected_input_lang != "en" else target_output_lang

        if query_lang != "en":
            logger.info(f"Translating query from '{query_lang}' to 'en'")
            try:
                # Primary translation via Gemini model cascade
                english_query = await llm_service.translate_with_llm(
                    user_text, source_lang=query_lang, target_lang="en"
                )
            except Exception as le:
                logger.warning(f"LLM translation to English failed ({le}). Trying Bhashini...")
                try:
                    english_query = await bhashini.translate_text(
                        user_text, source_lang=query_lang, target_lang="en"
                    )
                except Exception:
                    english_query = user_text

        logger.info(f"Normalized English Query: {english_query}")

        # ---------------------------------------------------------
        # Step 3: GraphRAG Search (Neo4j Cypher Traversal + BM25)
        # ---------------------------------------------------------
        top_k = getattr(settings, "TOP_K_RESULTS", 5) if settings else 5
        retrieved_docs = []
        if rag_pipeline:
            try:
                retrieved_docs = rag_pipeline.search(english_query, top_k=top_k)
                logger.info(f"Retrieved {len(retrieved_docs)} documents from GraphRAG.")
            except Exception as e:
                logger.error(f"Error during RAG search: {e}")
                retrieved_docs = []

        # ---------------------------------------------------------
        # Step 4: Gemini LLM Generation (Context + Scope + Citations)
        # ---------------------------------------------------------
        try:
            llm_result = await llm_service.generate_legal_response(
                query=english_query,
                retrieved_context=retrieved_docs,
                user_profile=payload.user_profile,
            )
            english_response = llm_result.get("english_response", "")
            citations = llm_result.get("citations", [])
        except Exception as ge:
            logger.error(f"LLM generation failed: {ge}. Using internal fallback.")
            english_response = llm_service._generate_fallback_response(
                english_query, retrieved_docs, payload.user_profile
            )
            citations = llm_service._extract_citations_from_text(english_response)

        if not english_response:
            english_response = llm_service._generate_fallback_response(
                english_query, retrieved_docs, payload.user_profile
            )
            citations = llm_service._extract_citations_from_text(english_response)

        # ---------------------------------------------------------
        # Step 5: Translate Legal Response into Selected Output Language
        # ---------------------------------------------------------
        regional_response = english_response
        if target_output_lang != "en":
            logger.info(f"Translating legal response into user target language '{target_output_lang}'")
            try:
                translated_response = await llm_service.translate_with_llm(
                    english_response, source_lang="en", target_lang=target_output_lang
                )
                if (
                    translated_response
                    and translated_response != english_response
                    and not translated_response.startswith("[")
                ):
                    regional_response = translated_response
            except Exception as trans_err:
                logger.warning(f"Translation to '{target_output_lang}' failed: {trans_err}")

        # ---------------------------------------------------------
        # Step 6: Text-to-Speech (TTS)
        # ---------------------------------------------------------
        audio_base64: Optional[str] = None
        try:
            audio_base64 = await bhashini.text_to_speech(regional_response, language=target_output_lang)
        except Exception as e:
            logger.debug(f"TTS synthesis notice: {e}")
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
            detected_language=target_output_lang,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unhandled error in chat endpoint: {exc}", exc_info=True)
        fallback_en = llm_service._generate_fallback_response(
            payload.text or "Legal query", [], payload.user_profile
        )
        return ChatResponse(
            original_query=payload.text or "",
            english_query=payload.text or "",
            regional_response=fallback_en,
            english_response=fallback_en,
            citations=llm_service._extract_citations_from_text(fallback_en),
            audio_base64=generate_mock_wav_base64(),
            detected_language="hi",
        )


@router.post("/translate", response_model=TranslateResponse, summary="Translate legal guidance to another regional language on demand")
async def translate_endpoint(request: Request, payload: TranslateRequest):
    """Dynamically re-translate an answer and synthesize native audio for any Indian language."""
    settings = getattr(request.app.state, "settings", None)
    bhashini = get_bhashini_service()
    llm_service = LLMService(settings)

    text = (payload.text or "").strip()
    target_lang = (payload.target_language or "hi").strip().lower()
    source_lang = (payload.source_language or "en").strip().lower()

    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text to translate must not be empty."
        )

    if target_lang == source_lang:
        audio = await bhashini.text_to_speech(text, language=target_lang)
        return TranslateResponse(
            translated_text=text,
            target_language=target_lang,
            audio_base64=audio,
        )

    logger.info(f"On-demand translating text from '{source_lang}' to '{target_lang}'")
    translated_text = text
    try:
        translated_text = await llm_service.translate_with_llm(
            text, source_lang=source_lang, target_lang=target_lang
        )
    except Exception as e:
        logger.warning(f"On-demand translation failed ({e}). Returning original.")

    audio_base64 = None
    try:
        audio_base64 = await bhashini.text_to_speech(translated_text, language=target_lang)
    except Exception as e:
        logger.debug(f"Audio synthesis error on translate: {e}")

    return TranslateResponse(
        translated_text=translated_text,
        target_language=target_lang,
        audio_base64=audio_base64,
    )
