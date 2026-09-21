// Central typed API client. Token persisted in localStorage; session cookie also sent.
export const API_BASE: string =
  (import.meta as unknown as { env: Record<string, string | undefined> }).env.VITE_API_URL ??
  'http://localhost:8000';

const TOKEN_KEY = 'clauseradar.token';

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage unavailable (private mode) — session cookie still works */
  }
}

export interface ApiErrorShape {
  detail?: string;
  code?: string;
  errors?: Record<string, string[] | string>;
}

export function getErrorMessage(err: unknown, fallback = 'Something went wrong.'): string {
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

export function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') q.set(k, String(v));
  }
  const s = q.toString();
  return s ? `?${s}` : '';
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Token ${token}` } : {}),
      ...(init?.headers ?? {}),
    },
    ...init,
  });
  if (res.status === 204) return undefined as unknown as T;
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  if (!res.ok) {
    const shape = (body ?? {}) as ApiErrorShape;
    const fieldErrors = shape.errors
      ? Object.entries(shape.errors)
          .map(([f, e]) => `${f}: ${Array.isArray(e) ? e.join(', ') : e}`)
          .join(' ')
      : '';
    const message = [shape.detail, fieldErrors].filter(Boolean).join(' ') || `Request failed (${res.status})`;
    const err = new Error(message) as Error & { status?: number; code?: string };
    err.status = res.status;
    err.code = shape.code;
    throw err;
  }
  return body as T;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface User {
  id: string;
  email: string;
  display_name: string;
  is_staff: boolean;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  role: string | null;
  created_at: string;
}

export interface Workspace {
  id: string;
  organization: string;
  organization_slug: string;
  name: string;
  slug: string;
  workspace_type: string;
  description: string;
  role: string | null;
  created_at: string;
}

export interface Contract {
  id: string;
  workspace: string;
  workspace_slug: string;
  title: string;
  counterparty: string;
  description: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  renewal_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditEvent {
  id: string;
  actor: string | null;
  actor_email: string | null;
  organization: string | null;
  workspace: string | null;
  entity_type: string;
  entity_id: string;
  action: string;
  metadata: Record<string, unknown>;
  created_at: string;
}

export interface Document {
  id: string;
  workspace: string;
  workspace_slug: string;
  contract: string;
  file: string;
  original_filename: string;
  mime: string;
  size_bytes: number;
  sha256: string;
  status: 'UPLOADED' | 'PROCESSING' | 'READY' | 'FAILED';
  page_count: number;
  error_message: string;
  ocr_used: boolean;
  processed_at: string | null;
  created_at: string;
}

export interface DocumentPage {
  id: string;
  page_number: number;
  text: string;
  char_count: number;
}

export interface Clause {
  id: string;
  workspace: string;
  contract: string;
  contract_title: string;
  document: string;
  document_name: string;
  page: string | null;
  page_number: number;
  heading: string;
  text: string;
  clause_type: string;
  start_offset: number;
  end_offset: number;
  confidence: number;
  extraction_method: string;
  created_at: string;
}

export interface Obligation {
  id: string;
  workspace: string;
  contract: string;
  contract_title: string;
  document: string | null;
  clause: string | null;
  page_number: number;
  source_text: string;
  title: string;
  obligation_type: string;
  actor: string;
  action: string;
  requirement: string;
  frequency: string;
  evidence_required: string;
  status: string;
  confidence: number;
  extraction_method: string;
  owner: string | null;
  owner_email: string | null;
  reviewer: string | null;
  reviewer_email: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export const api = {
  health: () => request<{ status: string; service: string; version: string }>('/api/health/'),
  ready: () => request<{ ready: boolean }>('/api/ready/'),

  register: (input: { email: string; password: string; display_name?: string }) =>
    request<{ user: User; token: string }>('/api/v1/auth/register/', {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  login: (input: { email: string; password: string }) =>
    request<{ user: User; token: string }>('/api/v1/auth/login/', {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  logout: () => request<{ detail: string }>('/api/v1/auth/logout/', { method: 'POST' }),
  me: () => request<User>('/api/v1/auth/me/'),

  organizations: () => request<Paginated<Organization>>('/api/v1/organizations/'),
  createOrganization: (input: { name: string }) =>
    request<Organization>('/api/v1/organizations/', { method: 'POST', body: JSON.stringify(input) }),

  workspaces: () => request<Paginated<Workspace>>('/api/v1/workspaces/'),
  createWorkspace: (input: { organization: string; name: string; description?: string }) =>
    request<Workspace>('/api/v1/workspaces/', { method: 'POST', body: JSON.stringify(input) }),

  contracts: (query = '') => request<Paginated<Contract>>(`/api/v1/contracts/${query}`),
  contract: (id: string) => request<Contract>(`/api/v1/contracts/${id}/`),
  createContract: (input: Partial<Contract>) =>
    request<Contract>('/api/v1/contracts/', { method: 'POST', body: JSON.stringify(input) }),
  updateContract: (id: string, input: Partial<Contract>) =>
    request<Contract>(`/api/v1/contracts/${id}/`, { method: 'PATCH', body: JSON.stringify(input) }),

  audit: (query = '') => request<Paginated<AuditEvent>>(`/api/v1/audit/${query}`),

  documents: (query = '') => request<Paginated<Document>>(`/api/v1/documents/${query}`),
  documentPages: (id: string) => request<Paginated<DocumentPage> | DocumentPage[]>(`/api/v1/documents/${id}/pages/`),
  reprocessDocument: (id: string) =>
    request<Document>(`/api/v1/documents/${id}/reprocess/`, { method: 'POST' }),
  deleteDocument: async (id: string): Promise<void> => {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/v1/documents/${id}/`, {
      method: 'DELETE',
      credentials: 'include',
      headers: token ? { Authorization: `Token ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Delete failed (${res.status})`);
  },
  uploadDocument: async (contractId: string, file: File): Promise<Document> => {
    const token = getToken();
    const form = new FormData();
    form.append('contract', contractId);
    form.append('file', file, file.name);
    const res = await fetch(`${API_BASE}/api/v1/documents/`, {
      method: 'POST',
      credentials: 'include',
      headers: token ? { Authorization: `Token ${token}` } : {},
      body: form,
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) {
      const detail = (body as { detail?: string })?.detail ?? `Upload failed (${res.status})`;
      const err = new Error(detail) as Error & { status?: number; existing_id?: string };
      err.status = res.status;
      err.existing_id = (body as { existing_id?: string })?.existing_id;
      throw err;
    }
    return body as Document;
  },
  obligations: (query = '') => request<Paginated<Obligation>>(`/api/v1/obligations/${query}`),
  obligation: (id: string) => request<Obligation>(`/api/v1/obligations/${id}/`),
  updateObligation: (id: string, input: Partial<Obligation>) =>
    request<Obligation>(`/api/v1/obligations/${id}/`, { method: 'PATCH', body: JSON.stringify(input) }),
  confirmObligation: (id: string) => request<Obligation>(`/api/v1/obligations/${id}/confirm/`, { method: 'POST' }),
  rejectObligation: (id: string, reason?: string) =>
    request<Obligation>(`/api/v1/obligations/${id}/reject/`, { method: 'POST', body: JSON.stringify({ reason: reason ?? '' }) }),
  activateObligation: (id: string) => request<Obligation>(`/api/v1/obligations/${id}/activate/`, { method: 'POST' }),
  clauses: (query = '') => request<Paginated<Clause>>(`/api/v1/clauses/${query}`),
  downloadDocument: async (id: string, filename: string): Promise<void> => {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/v1/documents/${id}/download/`, {
      credentials: 'include',
      headers: token ? { Authorization: `Token ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Download failed (${res.status})`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};
