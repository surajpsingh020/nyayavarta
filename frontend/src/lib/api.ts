/**
 * Client API services and TypeScript definitions for Nyayavarta.
 */

export type UserProfileType = 'general' | 'student' | 'senior_citizen' | 'professional';

export interface Citation {
  section: string;
  subject: string;
  key_changes?: string;
  act?: string;
}

export interface ChatRequest {
  text?: string;
  audio_base64?: string;
  source_language: string;
  user_profile: UserProfileType;
}

export interface ChatResponse {
  original_query: string;
  english_query: string;
  regional_response: string;
  english_response: string;
  citations: Citation[];
  audio_base64?: string | null;
}

export interface UploadResponse {
  filename: string;
  chunks_created: number;
  message: string;
}

export interface MessageItem {
  id: string;
  sender: 'user' | 'assistant';
  originalQuery?: string;
  englishQuery?: string;
  regionalResponse?: string;
  englishResponse?: string;
  citations?: Citation[];
  audioBase64?: string | null;
  timestamp: string;
  isAudioQuery?: boolean;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

/**
 * Send a multilingual text or audio query to /api/chat.
 */
export async function sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      // Keep default error text
    }
    throw new Error(errorDetail || `Request failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Upload legal document (PDF, Word, TXT) to /api/upload.
 */
export async function uploadDocument(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/api/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      // Keep default error text
    }
    throw new Error(errorDetail || `Upload failed with status ${response.status}`);
  }

  return response.json();
}

/**
 * Check backend health status.
 */
export async function checkHealth(): Promise<{ status: string; service: string }> {
  try {
    const response = await fetch(`${API_BASE}/health`);
    if (response.ok) {
      return response.json();
    }
  } catch {
    // Return offline status
  }
  return { status: 'offline', service: 'nyayavarta-api' };
}
