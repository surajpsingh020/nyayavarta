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
from typing import Optional, Dict
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.models.schemas import ChatRequest, ChatResponse, TranslateRequest, TranslateResponse, UserProfile
from app.routers.auth import get_optional_user
from app.services.auth_db import get_auth_db
from app.services.bhashini_utils import (
    detect_language_heuristic,
    generate_mock_wav_base64,
    get_bhashini_service,
)
from app.services.llm_service import LLMService
from app.services.guardrails_service import GuardrailsEngine
from app.services.tracing_service import LLMTrace, get_tracing_service

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory turn tracker for active chat sessions: session_key -> message_count
_SESSION_TURNS: Dict[str, int] = {}


@router.post("/chat", response_model=ChatResponse, summary="Process multilingual legal consultation query")
async def chat_endpoint(
    request: Request,
    payload: ChatRequest,
    user: Optional[dict] = Depends(get_optional_user)
):
    """Multilingual legal consultation endpoint with GraphRAG and multi-model synthesis."""
    settings = getattr(request.app.state, "settings", None)
    rag_pipeline = getattr(request.app.state, "rag_pipeline", None)
    bhashini = get_bhashini_service()
    llm_service = LLMService(settings)
    auth_db = get_auth_db()

    current_thread_id = payload.thread_id

    # ---------------------------------------------------------
    # LLMOps Tracing Initialization
    # ---------------------------------------------------------
    tracing_service = get_tracing_service()
    trace = LLMTrace(
        user_id=user["id"] if user else None,
        thread_id=current_thread_id,
        query=payload.text or ""
    )

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

        trace.query = user_text

        # ---------------------------------------------------------
        # Step 1.5: Security Guardrails & Data Leak Prevention (DLP)
        # ---------------------------------------------------------
        guard_span = trace.start_span("guardrails")
        guard_result = GuardrailsEngine.sanitize_input(user_text)
        trace.guardrail_status = guard_result.violation_type
        trace.guardrail_redactions = guard_result.redactions
        trace.sanitized_query = guard_result.sanitized_text
        guard_span.stop({
            "is_safe": guard_result.is_safe,
            "violation_type": guard_result.violation_type,
            "redactions": len(guard_result.redactions)
        })

        if not guard_result.is_safe:
            refusal_text = GuardrailsEngine.get_security_refusal_response(guard_result.violation_type, language=target_output_lang)
            trace.response_text = refusal_text
            tracing_service.record_trace(trace)
            return ChatResponse(
                original_query=user_text,
                english_query=user_text,
                regional_response=refusal_text,
                english_response=refusal_text,
                citations=[],
                audio_base64=None,
                detected_language=target_output_lang,
                thread_id=current_thread_id,
            )

        # Proceed with sanitized text (PII redacted)
        sanitized_user_text = guard_result.sanitized_text

        # Detect the actual script/language of the input text
        detected_input_lang = detect_language_heuristic(sanitized_user_text)
        if detected_input_lang != "en" and (target_output_lang in ("auto", "en") or payload.source_language == "auto"):
            target_output_lang = detected_input_lang
        elif detected_input_lang == "en" and target_output_lang in ("auto", "en"):
            target_output_lang = "en"

        if target_output_lang == "auto":
            target_output_lang = detected_input_lang

        # Persist user message to consultation thread if user is authenticated
        if user:
            try:
                if not current_thread_id:
                    thread_title = sanitized_user_text[:60] if sanitized_user_text else "Legal Consultation"
                    created_th = auth_db.create_thread(user_id=user["id"], title=thread_title)
                    current_thread_id = created_th["id"]
                    trace.thread_id = current_thread_id

                auth_db.add_message(
                    user_id=user["id"],
                    thread_id=current_thread_id,
                    sender="user",
                    original_query=user_text,
                    detected_language=detected_input_lang,
                )
            except Exception as pe:
                logger.warning(f"Could not persist user message to DB: {pe}")

        # ---------------------------------------------------------
        # Step 2: Translation to English for Legal Search
        # ---------------------------------------------------------
        english_query = sanitized_user_text
        if detected_input_lang != "en":
            logger.info(f"Translating query from '{detected_input_lang}' to 'en'")
            try:
                trans_span = trace.start_span("input_translation")
                english_query = await llm_service.translate_with_llm(
                    sanitized_user_text, source_lang=detected_input_lang, target_lang="en"
                )
                trans_span.stop({"source": detected_input_lang, "target": "en"})
            except Exception as le:
                logger.warning(f"LLM translation to English failed ({le}). Trying Bhashini...")
                try:
                    english_query = await bhashini.translate_text(
                        sanitized_user_text, source_lang=detected_input_lang, target_lang="en"
                    )
                except Exception:
                    english_query = sanitized_user_text

        logger.info(f"Normalized English Query: {english_query}")

        # ---------------------------------------------------------
        # Step 3: GraphRAG Search (Neo4j Cypher Traversal + BM25)
        # ---------------------------------------------------------
        top_k = getattr(settings, "TOP_K_RESULTS", 5) if settings else 5
        retrieved_docs = []
        retrieval_span = trace.start_span("retrieval")
        if rag_pipeline:
            try:
                retrieved_docs = rag_pipeline.search(
                    english_query,
                    top_k=top_k,
                    document_name=payload.document_name
                )
                logger.info(f"Retrieved {len(retrieved_docs)} documents from GraphRAG (doc_filter: {payload.document_name}).")
            except Exception as e:
                logger.error(f"Error during RAG search: {e}")
                retrieved_docs = []
        retrieval_span.stop({
            "results_count": len(retrieved_docs),
            "doc_filter": payload.document_name,
            "sections": [d.get("linked_section") for d in retrieved_docs if d.get("linked_section")]
        })
        trace.retrieved_sections = [str(d.get("linked_section")) for d in retrieved_docs if d.get("linked_section")]

        # ---------------------------------------------------------
        # Step 4: Gemini LLM Generation (Context + Scope + Citations)
        # ---------------------------------------------------------
        # Determine whether to include greeting (only on turn 1 of a new chat)
        client_ip = request.client.host if request.client else "default_client"
        session_key = payload.thread_id or request.headers.get("x-session-id") or client_ip

        if payload.is_first_message is False:
            is_first_turn = False
            _SESSION_TURNS[session_key] = _SESSION_TURNS.get(session_key, 1) + 1
        elif payload.is_first_message is True:
            is_first_turn = True
            _SESSION_TURNS[session_key] = 1
        else:
            # When is_first_message is None (e.g. legacy client or older cached frontend)
            prior_count = _SESSION_TURNS.get(session_key, 0)
            if prior_count > 0:
                is_first_turn = False
                _SESSION_TURNS[session_key] = prior_count + 1
            else:
                is_first_turn = True
                if current_thread_id and user:
                    try:
                        thread_msgs = auth_db.get_thread_messages(current_thread_id)
                        if any(m.get("sender") == "assistant" for m in thread_msgs):
                            is_first_turn = False
                    except Exception:
                        pass
                _SESSION_TURNS[session_key] = 1

        logger.info(f"Chat turn: is_first_turn={is_first_turn} (session_key={session_key}, turns={_SESSION_TURNS.get(session_key)})")

        gen_span = trace.start_span("llm_generation")
        try:
            llm_result = await llm_service.generate_legal_response(
                query=english_query,
                retrieved_context=retrieved_docs,
                user_profile=payload.user_profile,
                is_first_message=is_first_turn,
            )
            english_response = llm_result.get("english_response", "")
            citations = llm_result.get("citations", [])
        except Exception as ge:
            logger.error(f"LLM generation failed: {ge}. Using internal fallback.")
            english_response = llm_service._generate_fallback_response(
                english_query, retrieved_docs, payload.user_profile, is_first_message=is_first_turn
            )
            citations = llm_service._extract_citations_from_text(english_response)

        if not english_response:
            english_response = llm_service._generate_fallback_response(
                english_query, retrieved_docs, payload.user_profile, is_first_message=is_first_turn
            )
            citations = llm_service._extract_citations_from_text(english_response)

        gen_span.stop({
            "response_length": len(english_response),
            "citations_count": len(citations)
        })
        trace.citations = citations
        trace.response_text = english_response

        # ---------------------------------------------------------
        # Step 5: Translate Legal Response into Selected Output Language
        # ---------------------------------------------------------
        regional_response = english_response
        if target_output_lang != "en":
            logger.info(f"Translating legal response into user target language '{target_output_lang}'")
            try:
                resp_trans_span = trace.start_span("response_translation")
                translated_response = await llm_service.translate_with_llm(
                    english_response, source_lang="en", target_lang=target_output_lang
                )
                if (
                    translated_response
                    and translated_response != english_response
                    and not translated_response.startswith("[")
                ):
                    regional_response = translated_response
                resp_trans_span.stop({"target_language": target_output_lang})
            except Exception as trans_err:
                logger.warning(f"Translation to '{target_output_lang}' failed: {trans_err}")

        # ---------------------------------------------------------
        # Step 6: Text-to-Speech (TTS)
        # ---------------------------------------------------------
        audio_base64: Optional[str] = None
        try:
            tts_span = trace.start_span("tts_synthesis")
            audio_base64 = await bhashini.text_to_speech(regional_response, language=target_output_lang)
            tts_span.stop({"language": target_output_lang})
        except Exception as e:
            logger.debug(f"TTS synthesis notice: {e}")

        # Record LLMOps Telemetry Trace
        tracing_service.record_trace(trace)

        # ---------------------------------------------------------
        # Step 7: Return Structured Response & Persist Assistant Message
        # ---------------------------------------------------------
        if user and current_thread_id:
            try:
                auth_db.add_message(
                    user_id=user["id"],
                    thread_id=current_thread_id,
                    sender="assistant",
                    original_query=user_text,
                    english_query=english_query,
                    regional_response=regional_response,
                    english_response=english_response,
                    citations=citations,
                    audio_base64=audio_base64,
                    detected_language=target_output_lang,
                )
            except Exception as pe:
                logger.warning(f"Could not persist assistant message to DB: {pe}")

        return ChatResponse(
            original_query=user_text,
            english_query=english_query,
            regional_response=regional_response,
            english_response=english_response,
            citations=citations,
            audio_base64=audio_base64,
            detected_language=target_output_lang,
            thread_id=current_thread_id,
        )

    except HTTPException:
        raise
    except Exception as exc:
        trace.error = str(exc)
        tracing_service.record_trace(trace)
        logger.error(f"Unhandled error in chat endpoint: {exc}", exc_info=True)
        fallback_en = llm_service._generate_fallback_response(
            payload.text or "Legal query", [], payload.user_profile
        )
        citations_fb = llm_service._extract_citations_from_text(fallback_en)
        mock_audio = generate_mock_wav_base64()

        if user and current_thread_id:
            try:
                auth_db.add_message(
                    user_id=user["id"],
                    thread_id=current_thread_id,
                    sender="assistant",
                    original_query=payload.text or "",
                    english_query=payload.text or "",
                    regional_response=fallback_en,
                    english_response=fallback_en,
                    citations=citations_fb,
                    audio_base64=mock_audio,
                    detected_language="hi",
                )
            except Exception as pe:
                logger.warning(f"Could not persist fallback assistant message to DB: {pe}")

        return ChatResponse(
            original_query=payload.text or "",
            english_query=payload.text or "",
            regional_response=fallback_en,
            english_response=fallback_en,
            citations=citations_fb,
            audio_base64=mock_audio,
            detected_language="hi",
            thread_id=current_thread_id,
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


# -------------------------------------------------------------
# LLMOps Observability & Telemetry Endpoints
# -------------------------------------------------------------

@router.get("/llmops/metrics", summary="Get aggregate LLMOps telemetry metrics")
async def get_llmops_metrics():
    """Retrieve online performance metrics, average latency, and guardrail interception statistics."""
    tracing_service = get_tracing_service()
    return tracing_service.get_telemetry_metrics()


@router.get("/llmops/traces", summary="Get recent LLMOps consultation traces")
async def get_llmops_traces(limit: int = 25):
    """Retrieve detailed execution traces, guardrail redactions, and span timings."""
    tracing_service = get_tracing_service()
    return tracing_service.get_recent_traces(limit=limit)
