import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import App from '../App';
import * as api from '../services/api';
import { RAGResult } from '../types/rag';

// Mock API functions
vi.mock('../services/api', async () => {
  const actual = await vi.importActual<typeof api>('../services/api');
  return {
    ...actual,
    queryRag: vi.fn(),
    checkHealth: vi.fn().mockResolvedValue({ status: 'ok', environment: 'development' }),
  };
});

const mockBaseResult: RAGResult = {
  query: 'Can the rules of selection be changed after recruitment commences?',
  answer: 'Courts have consistently frowned upon tinkering with the rules of the game once recruitment commences. [E1]',
  status: 'answered',
  grounding_status: 'sufficient_evidence',
  verification_badge: 'verified_supported',
  evidence_passages: [
    {
      evidence_id: 'E1',
      document_id: '2024_12_28_67',
      case_title: 'Tej Prakash Pathak v. Rajasthan High Court',
      citation: '[2024] 12 SCR 28',
      case_number: 'C.A. No. 2634/2013',
      decision_date: '2024-11-07',
      passage_text: 'The rules of the game cannot be changed once the recruitment process commences.',
      start_char: 1200,
      end_char: 1285,
      judgment_rank: 1,
      judgment_score: 0.95,
      passage_score: 0.88,
      structural_label: 'operative_holding',
    },
  ],
  citation_validation: {
    is_valid: true,
    validation_status: 'valid',
    citation_syntax_valid: true,
    citation_existence_valid: true,
    attribution_complete: true,
    evidence_integrity_valid: true,
    semantic_support_status: 'supported',
    contradicted_claims_count: 0,
    unsupported_claims_count: 0,
    partially_supported_claims_count: 0,
    supported_claims_count: 1,
    unverified_claims_count: 0,
    cited_source_ids: ['E1'],
    valid_source_ids: ['E1'],
    invalid_source_ids: [],
    unsupported_sentences: [],
    has_invalid_citations: false,
    validation_notes: [],
    verification_notes: ['Claim directly entailed by passage holding.'],
  },
  claims: [
    {
      sentence: 'Courts have consistently frowned upon tinkering with the rules of the game once recruitment commences. [E1]',
      cited_evidence_ids: ['E1'],
      citation_syntax_valid: true,
      citation_existence_valid: true,
      is_attributed: true,
      semantic_support_status: 'supported',
      verification_status: 'supported',
      verification_method: 'direct_holding_entailment',
      verification_reason: 'Entailed by Tej Prakash Pathak holding without contradiction.',
    },
  ],
  retrieval_metadata: {},
  timing_ms: { retrieval_ms: 25.4, validation_ms: 12.1, total_ms: 380.5 },
  legal_disclaimer: 'Citations reflect observational text in retrieved Supreme Court judgments.',
};

describe('NyayaVarta Frontend — Safe Answer Presentation Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders landing page with title, disclaimer, and preset buttons', async () => {
    render(<App />);
    expect(screen.getByRole('heading', { level: 1, name: /NyayaVarta/i })).toBeInTheDocument();
    expect(screen.getByText(/Academic Research Prototype — Not for Real-World Legal Practice/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Enter Legal Inquiry \/ Case Law Proposition/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Verify Legal Query/i })).toBeInTheDocument();
    expect(screen.getByText(/1\. Supported Rule/i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText(/API Connected/i)).toBeInTheDocument();
    });
  });

  it('populates query textarea when a preset button is clicked', async () => {
    render(<App />);

    const presetBtn = screen.getByText(/1\. Supported Rule/i);
    fireEvent.click(presetBtn);

    const textarea = screen.getByLabelText(/Enter Legal Inquiry/i) as HTMLTextAreaElement;
    expect(textarea.value).toContain('Rajasthan High Court rules');

    await waitFor(() => {
      expect(screen.getByText(/API Connected/i)).toBeInTheDocument();
    });
  });

  it('submits query and renders verified_supported badge with citation and passage', async () => {
    vi.mocked(api.queryRag).mockResolvedValueOnce(mockBaseResult);

    render(<App />);

    const textarea = screen.getByLabelText(/Enter Legal Inquiry/i);
    fireEvent.change(textarea, { target: { value: 'Valid legal test question' } });

    const submitBtn = screen.getByRole('button', { name: /Verify Legal Query/i });
    fireEvent.click(submitBtn);

    expect(screen.getByText(/Verifying Evidence.../i)).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId('badge-verified_supported')).toBeInTheDocument();
      expect(screen.getByText(/Verified Legal Authority/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Tej Prakash Pathak v. Rajasthan High Court/i)).toBeInTheDocument();
    expect(screen.getByText(/\[2024\] 12 SCR 28/i)).toBeInTheDocument();
    expect(screen.getByText(/operative_holding/i)).toBeInTheDocument();
  });

  it('renders qualified_answer badge with omission warning for partially supported case', async () => {
    const partialResult: RAGResult = {
      ...mockBaseResult,
      verification_badge: 'qualified_answer',
      status: 'answered_with_qualification',
      claims: [
        {
          sentence: 'Authorized officer can extend 15-day period without borrower consent. [E1]',
          cited_evidence_ids: ['E1'],
          citation_syntax_valid: true,
          citation_existence_valid: true,
          is_attributed: true,
          semantic_support_status: 'partially_supported',
          verification_status: 'partially_supported',
          verification_method: 'statutory_qualification_omission_check',
          verification_reason: 'Omits mandatory borrower written consent under SARFAESI Rule 9(4).',
          unresolved_uncertainty: 'Action conditioned upon borrower consent.',
        },
      ],
    };

    vi.mocked(api.queryRag).mockResolvedValueOnce(partialResult);

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Enter Legal Inquiry/i), { target: { value: 'SARFAESI test' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify Legal Query/i }));

    await waitFor(() => {
      expect(screen.getByTestId('badge-qualified_answer')).toBeInTheDocument();
      expect(screen.getByText(/Qualified Answer/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/Omits mandatory borrower written consent/i)).toBeInTheDocument();
  });

  it('renders unverified_answer badge with neutral treatment (never labelled verified)', async () => {
    const unverifiedResult: RAGResult = {
      ...mockBaseResult,
      verification_badge: 'unverified_answer',
      status: 'answered',
      claims: [
        {
          sentence: 'Hypothetical proposition with citation [E1].',
          cited_evidence_ids: ['E1'],
          citation_syntax_valid: true,
          citation_existence_valid: true,
          is_attributed: true,
          semantic_support_status: 'not_evaluated',
          verification_status: 'not_evaluated',
          verification_method: 'unverified',
          verification_reason: 'Semantic entailment could not be established by deterministic rules.',
        },
      ],
    };

    vi.mocked(api.queryRag).mockResolvedValueOnce(unverifiedResult);

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Enter Legal Inquiry/i), { target: { value: 'Unverified question' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify Legal Query/i }));

    await waitFor(() => {
      expect(screen.getByTestId('badge-unverified_answer')).toBeInTheDocument();
      expect(screen.getByText(/Unverified Legal Entailment/i)).toBeInTheDocument();
    });

    expect(screen.queryByText(/^Verified Legal Authority$/i)).not.toBeInTheDocument();
  });

  it('renders rejected_answer and suppresses output with explicit warning banner', async () => {
    const rejectedResult: RAGResult = {
      ...mockBaseResult,
      verification_badge: 'rejected_answer',
      status: 'validation_failed',
      answer: 'Contradicted assertion claiming seeds are patentable under Section 3(j). [E1]',
      claims: [
        {
          sentence: 'Seeds are patentable under Section 3(j). [E1]',
          cited_evidence_ids: ['E1'],
          citation_syntax_valid: true,
          citation_existence_valid: true,
          is_attributed: true,
          semantic_support_status: 'contradicted',
          verification_status: 'contradicted',
          verification_method: 'polarity_contradiction_check',
          verification_reason: 'Direct statutory negation: Section 3(j) explicitly excludes seeds.',
        },
      ],
    };

    vi.mocked(api.queryRag).mockResolvedValueOnce(rejectedResult);

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Enter Legal Inquiry/i), { target: { value: 'Patents 3(j) question' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify Legal Query/i }));

    await waitFor(() => {
      expect(screen.getByTestId('badge-rejected_answer')).toBeInTheDocument();
      expect(screen.getByText(/Unsafe Answer Suppressed by Verification Gate/i)).toBeInTheDocument();
    });

    // Inspect suppressed button allows audit inspection
    const auditToggle = screen.getByText(/Inspect Suppressed Output \(Audit Mode\)/i);
    expect(auditToggle).toBeInTheDocument();
    fireEvent.click(auditToggle);
    expect(screen.getByText(/Contradicted assertion claiming seeds/i)).toBeInTheDocument();
  });

  it('renders insufficient_evidence clean abstention without hallucinated text', async () => {
    const abstentionResult: RAGResult = {
      ...mockBaseResult,
      verification_badge: 'insufficient_evidence',
      status: 'insufficient_evidence',
      answer: 'INSUFFICIENT EVIDENCE: The retrieved judicial passages do not provide sufficient evidence.',
      evidence_passages: [],
      claims: [],
    };

    vi.mocked(api.queryRag).mockResolvedValueOnce(abstentionResult);

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Enter Legal Inquiry/i), { target: { value: 'Admiralty limitation query' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify Legal Query/i }));

    await waitFor(() => {
      expect(screen.getByTestId('badge-insufficient_evidence')).toBeInTheDocument();
      expect(screen.getByText(/Judicial Corpus Abstention \(Insufficient Grounding\)/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/No judicial evidence passages were retrieved for this query/i)).toBeInTheDocument();
  });

  it('handles HTTP 504 Gateway Timeout gracefully with actionable guidance', async () => {
    const timeoutError = new api.ApiError(
      'Local LLM inference timed out after deadline (HTTP 504). Please retry or select the deterministic mock provider.',
      504,
      'system_error'
    );
    vi.mocked(api.queryRag).mockRejectedValueOnce(timeoutError);

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Enter Legal Inquiry/i), { target: { value: 'Timeout inquiry' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify Legal Query/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/Request Timed Out \(HTTP 504\)/i)).toBeInTheDocument();
    });

    expect(screen.getAllByText(/Deterministic Mock \(Fast Baseline\)/i).length).toBeGreaterThan(1);
  });

  it('handles HTTP 503 Provider Unavailable gracefully', async () => {
    const unavailError = new api.ApiError(
      'Local LLM service is currently unavailable (HTTP 503). Ensure the Ollama daemon is running.',
      503,
      'system_error'
    );
    vi.mocked(api.queryRag).mockRejectedValueOnce(unavailError);

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Enter Legal Inquiry/i), { target: { value: 'Offline inquiry' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify Legal Query/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/Local LLM Unavailable \(HTTP 503\)/i)).toBeInTheDocument();
    });
  });

  it('handles backend connection failure when API server is offline', async () => {
    const connError = new api.ApiError(
      'Unable to connect to NyayaVarta API server at /v1/rag/query. Please verify the FastAPI backend is running.',
      0,
      'system_error'
    );
    vi.mocked(api.queryRag).mockRejectedValueOnce(connError);

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Enter Legal Inquiry/i), { target: { value: 'Connection query' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify Legal Query/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/Backend Connection Failed/i)).toBeInTheDocument();
    });
  });

  it('handles malformed backend response missing required badge', async () => {
    const malformedError = new api.ApiError(
      'Malformed response: backend returned missing verification fields.',
      500,
      'system_error'
    );
    vi.mocked(api.queryRag).mockRejectedValueOnce(malformedError);

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Enter Legal Inquiry/i), { target: { value: 'Malformed test' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify Legal Query/i }));

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText(/backend returned missing verification fields/i)).toBeInTheDocument();
    });
  });

  it('displays mock provider tag when retrieval_metadata.model_name is a mock model', async () => {
    const mockModelResult: RAGResult = {
      ...mockBaseResult,
      retrieval_metadata: { model_name: 'mock-grounded-cpu-v1' },
    };
    vi.mocked(api.queryRag).mockResolvedValueOnce(mockModelResult);

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Enter Legal Inquiry/i), { target: { value: 'Mock model test' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify Legal Query/i }));

    await waitFor(() => {
      const provenance = screen.getByTestId('model-provenance');
      expect(provenance).toBeInTheDocument();
      expect(provenance).toHaveTextContent(/Mock Provider \(mock-grounded-cpu-v1\)/i);
    });
  });

  it('displays live model tag when retrieval_metadata.model_name is a live local model', async () => {
    const liveModelResult: RAGResult = {
      ...mockBaseResult,
      retrieval_metadata: { model_name: 'llama3.2:1b' },
    };
    vi.mocked(api.queryRag).mockResolvedValueOnce(liveModelResult);

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Enter Legal Inquiry/i), { target: { value: 'Live model test' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify Legal Query/i }));

    await waitFor(() => {
      const provenance = screen.getByTestId('model-provenance');
      expect(provenance).toBeInTheDocument();
      expect(provenance).toHaveTextContent(/Live Model \(llama3.2:1b\)/i);
    });
  });

  it('displays model information unavailable when retrieval_metadata.model_name is missing', async () => {
    const missingMetadataResult: RAGResult = {
      ...mockBaseResult,
      retrieval_metadata: {},
    };
    vi.mocked(api.queryRag).mockResolvedValueOnce(missingMetadataResult);

    render(<App />);
    fireEvent.change(screen.getByLabelText(/Enter Legal Inquiry/i), { target: { value: 'Missing metadata test' } });
    fireEvent.click(screen.getByRole('button', { name: /Verify Legal Query/i }));

    await waitFor(() => {
      const provenance = screen.getByTestId('model-provenance');
      expect(provenance).toBeInTheDocument();
      expect(provenance).toHaveTextContent(/Model information unavailable/i);
    });
  });
});
