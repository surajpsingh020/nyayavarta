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
  user_profile?: UserProfileType;
  thread_id?: string;
  document_name?: string;
  is_first_message?: boolean;
}

export interface ChatResponse {
  original_query: string;
  english_query: string;
  regional_response: string;
  english_response: string;
  citations: Citation[];
  audio_base64?: string | null;
  detected_language?: string;
  thread_id?: string;
}

export interface TranslateResponse {
  translated_text: string;
  target_language: string;
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
  detectedLanguage?: string;
  activeLanguage?: string;
  languageVersions?: Record<string, { text: string; audioBase64?: string | null }>;
}

export interface UserInfo {
  id: string;
  email: string;
  full_name: string;
}

export interface AuthResponse {
  token: string;
  user: UserInfo;
}

export interface ConsultationThread {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ThreadMessageItem {
  id: string;
  thread_id: string;
  sender: 'user' | 'assistant';
  original_query?: string | null;
  english_query?: string | null;
  regional_response?: string | null;
  english_response?: string | null;
  citations: Citation[];
  audio_base64?: string | null;
  detected_language?: string;
  created_at: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';
const TOKEN_KEY = 'nyayavarta_auth_token';

export function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setStoredToken(token: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TOKEN_KEY, token);
  }
}

export function clearStoredToken(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_KEY);
  }
}

/**
 * Send a multilingual text or audio query to /api/chat.
 */
export async function sendChatMessage(payload: ChatRequest): Promise<ChatResponse> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers,
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
 * Dynamically translate legal text into another Indian regional language with native audio.
 */
export async function translateLegalText(
  text: string,
  targetLanguage: string,
  sourceLanguage: string = 'en'
): Promise<TranslateResponse> {
  const response = await fetch(`${API_BASE}/api/translate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      text,
      target_language: targetLanguage,
      source_language: sourceLanguage,
    }),
  });

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {}
    throw new Error(errorDetail || `Translation failed with status ${response.status}`);
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

// -------------------------------------------------------------
// Authentication Client Methods
// -------------------------------------------------------------
export async function registerUser(email: string, password: string, fullName: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, full_name: fullName }),
  });

  if (!response.ok) {
    let detail = 'Registration failed';
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  const result: AuthResponse = await response.json();
  setStoredToken(result.token);
  return result;
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  const response = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    let detail = 'Login failed';
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  const result: AuthResponse = await response.json();
  setStoredToken(result.token);
  return result;
}

export async function getCurrentUser(): Promise<UserInfo | null> {
  const token = getStoredToken();
  if (!token) return null;

  try {
    const response = await fetch(`${API_BASE}/api/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      clearStoredToken();
      return null;
    }
    return response.json();
  } catch {
    return null;
  }
}

export async function logoutUser(): Promise<void> {
  const token = getStoredToken();
  if (token) {
    try {
      await fetch(`${API_BASE}/api/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      });
    } catch {}
  }
  clearStoredToken();
}

// -------------------------------------------------------------
// Consultation Threads Client Methods (Strictly Isolated)
// -------------------------------------------------------------
export async function getUserThreads(): Promise<ConsultationThread[]> {
  const token = getStoredToken();
  if (!token) return [];

  const response = await fetch(`${API_BASE}/api/chat/threads`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    if (response.status === 401) clearStoredToken();
    return [];
  }
  return response.json();
}

export async function createThread(title?: string): Promise<ConsultationThread> {
  const token = getStoredToken();
  if (!token) throw new Error('You must be logged in to create a consultation.');

  const response = await fetch(`${API_BASE}/api/chat/threads`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ title }),
  });

  if (!response.ok) {
    let detail = 'Failed to create consultation thread';
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  return response.json();
}

export async function getThreadMessages(threadId: string): Promise<ThreadMessageItem[]> {
  const token = getStoredToken();
  if (!token) return [];

  const response = await fetch(`${API_BASE}/api/chat/threads/${threadId}/messages`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    let detail = 'Failed to load thread messages';
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  return response.json();
}

export async function deleteThread(threadId: string): Promise<void> {
  const token = getStoredToken();
  if (!token) return;

  const response = await fetch(`${API_BASE}/api/chat/threads/${threadId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  });

  if (!response.ok) {
    let detail = 'Failed to delete thread';
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch {}
    throw new Error(detail);
  }
}

// -------------------------------------------------------------
// Law Transition Matrix & Landmark Precedents
// -------------------------------------------------------------
export interface LawTransition {
  id: string;
  subject: string;
  old_law: string;
  new_law: string;
  category: 'bns' | 'bnss' | 'bsa' | 'special';
  category_label: string;
  description: string;
  key_changes: string;
  suggested_query: string;
  punishment_comparison?: string;
  procedural_classification?: string;
  practical_citizen_advice?: string;
  full_statutory_text?: string;
}

export interface CasePrecedent {
  title: string;
  citation: string;
  neutral_citation: string;
  court: string;
  year: number;
  bench: string;
  headnote: string;
  ratio_decidendi: string;
  applied_sections: string[];
  suggested_query: string;
  significance?: string;
  practical_impact?: string;
}

export interface MatrixResponse {
  status: string;
  total_transitions: number;
  total_precedents: number;
  transitions: LawTransition[];
  precedents: CasePrecedent[];
}

export async function fetchLawMatrix(category?: string, search?: string): Promise<MatrixResponse> {
  const params = new URLSearchParams();
  if (category && category !== 'all') params.set('category', category);
  if (search) params.set('search', search);

  const qs = params.toString() ? `?${params.toString()}` : '';
  const response = await fetch(`${API_BASE}/api/matrix${qs}`);

  if (!response.ok) {
    throw new Error('Failed to load Law Transition Matrix');
  }

  return response.json();
}
