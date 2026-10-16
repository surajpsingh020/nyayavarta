"""
FastAPI Router for Evidence-Grounded Legal Question Answering (Milestone 5A).
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from services.rag.models import RAGResult
from services.rag.pipeline import RAGPipeline
from services.rag.providers import get_llm_provider

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/rag", tags=["RAG"])

# Global or lazily initialized pipeline instance
_pipeline_instance: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = RAGPipeline()
    return _pipeline_instance


class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, description="Legal question or inquiry")
    top_k_judgments: int = Field(default=3, ge=1, le=10, description="Number of candidate judgments to retrieve")
    max_passages: int = Field(default=5, ge=1, le=10, description="Maximum evidence passages to provide to LLM")
    enable_graph: bool = Field(default=False, description="Whether to enable Knowledge Graph expansion (disabled by default)")
    provider_type: str = Field(default="mock", description="LLM provider: 'mock' or 'ollama'")
    structured_output: bool = Field(default=False, description="Whether to use structured JSON schema constrained output (Milestone 7)")
    enable_compression: bool = Field(default=False, description="Whether to enable extractive sentence compression (Milestone 8)")


@router.post("/query", response_model=RAGResult)
def query_rag(
    request: RAGQueryRequest,
    pipeline: RAGPipeline = Depends(get_rag_pipeline)
) -> RAGResult:
    """
    Execute evidence-grounded legal question answering over the Supreme Court corpus (Milestone 5B, 7 & 8).
    Returns generated answer with validated citations, claim attribution, and source passages.
    """
    if request.provider_type.lower() not in ["mock", "mock_partial", "ollama", "local"]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid provider_type '{request.provider_type}'. Supported providers are: 'mock', 'mock_partial', 'ollama'."
        )

    try:
        provider = get_llm_provider(request.provider_type)
        result = pipeline.query(
            query_text=request.query,
            top_k_judgments=request.top_k_judgments,
            max_passages=request.max_passages,
            enable_graph=request.enable_graph,
            provider=provider,
            enable_compression=request.enable_compression,
            structured_output=request.structured_output
        )
        return result
    except TimeoutError as te:
        logger.warning(f"RAG query timeout: {te}")
        raise HTTPException(status_code=504, detail="Local LLM inference timed out. Please retry or use mock provider.")
    except RuntimeError as re:
        logger.error(f"RAG provider unavailable: {re}")
        raise HTTPException(
            status_code=503,
            detail="Local LLM service is currently unavailable. Ensure Ollama daemon is running or specify provider_type='mock'."
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in query_rag: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during RAG query processing.")
