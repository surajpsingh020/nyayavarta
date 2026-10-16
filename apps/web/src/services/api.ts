import { RAGQueryRequest, RAGResult } from '../types/rag';

// Default to relative /v1 (proxied by Vite) or full URL from env
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');

export class ApiError extends Error {
  status: number;
  badge?: string;

  constructor(message: string, status: number, badge?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.badge = badge;
  }
}

/**
 * Execute RAG query against the backend API endpoint (POST /v1/rag/query)
 */
export async function queryRag(params: RAGQueryRequest): Promise<RAGResult> {
  const endpoint = `${API_BASE_URL}/v1/rag/query`;

  const payload = {
    query: params.query.trim(),
    top_k_judgments: params.top_k_judgments ?? 3,
    max_passages: params.max_passages ?? 5,
    enable_graph: params.enable_graph ?? false,
    provider_type: params.provider_type ?? 'mock',
    structured_output: params.structured_output ?? false,
    enable_compression: params.enable_compression ?? false,
  };

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      let detail = '';
      try {
        const errorJson = await response.json();
        detail = errorJson.detail || JSON.stringify(errorJson);
      } catch {
        detail = await response.text();
      }

      if (response.status === 504) {
        throw new ApiError(
          detail || 'Local LLM inference timed out after deadline (HTTP 504). Please retry or select the deterministic mock provider.',
          504,
          'system_error'
        );
      } else if (response.status === 503) {
        throw new ApiError(
          detail || 'Local LLM service is currently unavailable (HTTP 503). Ensure the Ollama daemon is running or select the mock provider.',
          503,
          'system_error'
        );
      } else if (response.status === 400) {
        throw new ApiError(detail || 'Invalid query parameters (HTTP 400).', 400);
      } else {
        throw new ApiError(detail || `API request failed with HTTP ${response.status}`, response.status, 'system_error');
      }
    }

    const data: RAGResult = await response.json();

    // Invariant check: verify that response contains required fields
    if (!data.verification_badge || !data.status) {
      throw new ApiError('Malformed response: backend returned missing verification fields.', 500, 'system_error');
    }

    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    // Network / connection error
    throw new ApiError(
      `Unable to connect to NyayaVarta API server at ${endpoint || 'local host'}. Please verify the FastAPI backend is running (uvicorn apps.api.main:app).`,
      0,
      'system_error'
    );
  }
}

/**
 * Health check endpoint (GET /v1/health)
 */
export async function checkHealth(): Promise<{ status: string; environment: string }> {
  const endpoint = `${API_BASE_URL}/v1/health`;
  try {
    const response = await fetch(endpoint);
    if (!response.ok) {
      throw new Error(`Health check returned HTTP ${response.status}`);
    }
    return await response.json();
  } catch (err: any) {
    throw new Error(`Backend unavailable: ${err.message}`);
  }
}
