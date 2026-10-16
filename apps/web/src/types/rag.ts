/**
 * NyayaVarta RAG Types (Aligned strictly with services/rag/models.py)
 */

export type VerificationBadge =
  | 'verified_supported'
  | 'qualified_answer'
  | 'unverified_answer'
  | 'rejected_answer'
  | 'insufficient_evidence'
  | 'system_error';

export type PipelineStatus =
  | 'answered'
  | 'answered_with_qualification'
  | 'insufficient_evidence'
  | 'empty_retrieval'
  | 'error'
  | 'validation_failed';

export type ClaimVerificationStatus =
  | 'supported'
  | 'partially_supported'
  | 'unsupported'
  | 'contradicted'
  | 'not_evaluated';

export interface EvidencePassage {
  evidence_id: string;
  document_id: string;
  case_title: string;
  citation?: string | null;
  case_number?: string | null;
  decision_date?: string | null;
  passage_text: string;
  start_char: number;
  end_char: number;
  judgment_rank: number;
  judgment_score: number;
  passage_score: number;
  structural_label?: string | null;
  structural_confidence?: number;
  detection_method?: string | null;
}

export interface ClaimAttribution {
  sentence: string;
  cited_evidence_ids: string[];
  citation_syntax_valid: boolean;
  citation_existence_valid: boolean;
  is_attributed: boolean;
  semantic_support_status: string;
  verification_status: ClaimVerificationStatus;
  verification_method: string;
  verification_reason: string;
  unresolved_uncertainty?: string | null;
  source_offsets?: Array<{
    evidence_id: string;
    document_id: string;
    start_char: number;
    end_char: number;
    case_title?: string;
  }>;
  structural_natures?: string[];
  relies_only_on_party_submissions?: boolean;
  omits_statutory_qualification?: boolean;
  claim_overgeneralizes_holding?: boolean;
}

export interface CitationValidationResult {
  is_valid: boolean;
  validation_status: string;
  citation_syntax_valid: boolean;
  citation_existence_valid: boolean;
  attribution_complete: boolean;
  evidence_integrity_valid: boolean;
  semantic_support_status: string;
  contradicted_claims_count: number;
  unsupported_claims_count: number;
  partially_supported_claims_count: number;
  supported_claims_count: number;
  unverified_claims_count: number;
  cited_source_ids: string[];
  valid_source_ids: string[];
  invalid_source_ids: string[];
  unsupported_sentences: string[];
  has_invalid_citations: boolean;
  validation_notes: string[];
  verification_notes: string[];
  shadow_nli_disagreements_count?: number;
}

export interface StructuredClaim {
  text: string;
  evidence_ids: string[];
}

export interface StructuredAnswer {
  status: 'answer' | 'abstain';
  claims: StructuredClaim[];
  abstention_reason?: string | null;
}

export interface RAGResult {
  query: string;
  answer: string;
  status: PipelineStatus;
  grounding_status: string;
  evidence_passages: EvidencePassage[];
  citation_validation: CitationValidationResult;
  claims: ClaimAttribution[];
  structured_answer?: StructuredAnswer | null;
  verification_badge: VerificationBadge;
  retrieval_metadata: Record<string, any>;
  timing_ms: Record<string, number>;
  grounding_decision?: Record<string, any> | null;
  legal_disclaimer: string;
}

export interface RAGQueryRequest {
  query: string;
  top_k_judgments?: number;
  max_passages?: number;
  enable_graph?: boolean;
  provider_type?: 'mock' | 'mock_partial' | 'ollama' | 'local';
  structured_output?: boolean;
  enable_compression?: boolean;
}
