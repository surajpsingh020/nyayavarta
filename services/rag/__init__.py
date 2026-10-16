"""
NyayaVarta Evidence-Grounded RAG Subsystem (Milestone 5A).
"""
from services.rag.models import (
    EvidencePassage,
    ClaimAttribution,
    CitationValidationResult,
    RAGResult
)
from services.rag.evidence import EvidenceAssembler, verify_evidence_offsets
from services.rag.prompt import SYSTEM_PROMPT, build_rag_prompt
from services.rag.providers import (
    LLMProvider,
    LLMResponse,
    MockLLMProvider,
    LocalOllamaProvider,
    get_llm_provider
)
from services.rag.validator import CitationValidator
from services.rag.pipeline import RAGPipeline

__all__ = [
    "EvidencePassage",
    "ClaimAttribution",
    "CitationValidationResult",
    "RAGResult",
    "EvidenceAssembler",
    "verify_evidence_offsets",
    "SYSTEM_PROMPT",
    "build_rag_prompt",
    "LLMProvider",
    "LLMResponse",
    "MockLLMProvider",
    "LocalOllamaProvider",
    "get_llm_provider",
    "CitationValidator",
    "RAGPipeline",
]
