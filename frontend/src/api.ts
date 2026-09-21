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
  priority: string;
  notes: string;
  reviewer: string | null;
  reviewer_email: string | null;
  reviewed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Deadline {
  id: string;
  workspace: string;
  contract: string;
  contract_title: string;
  obligation: string | null;
  obligation_title: string | null;
  title: string;
  kind: string;
  due_date: string;
  anchor_date: string | null;
  offset_days: number | null;
  business_days: boolean;
  rule: string;
  status: 'UPCOMING' | 'DUE_SOON' | 'OVERDUE' | 'COMPLETED' | 'WAIVED';
  completed: boolean;
  waived: boolean;
  completed_at: string | null;
  created_at: string;
}

export interface RiskFinding {
  id: string;
  workspace: string;
  contract: string;
  contract_title: string;
  obligation: string | null;
  obligation_title: string | null;
  rule: string;
  points: number;
  severity: string;
  title: string;
  explanation: string;
  evidence: Record<string, unknown>;
  created_at: string;
}

export interface RiskSummary {
  contract: string;
  score: number;
  level: string;
  findings: RiskFinding[];
}

export interface WorkspaceMember {
  id: string;
  user: string;
  user_email: string;
  role: string;
  created_at: string;
}

export interface Comment {
  id: string;
  workspace: string;
  contract: string | null;
  obligation: string | null;
  author: string | null;
  author_email: string | null;
  body: string;
  created_at: string;
}

export interface EvidenceItem {
  id: string;
  workspace: string;
  obligation: string;
  file: string;
  original_filename: string;
  mime: string;
  size_bytes: number;
  note: string;
  uploaded_by_email: string | null;
  created_at: string;
}

export interface TaskItem {
  id: string;
  workspace: string;
  contract: string | null;
  obligation: string | null;
  title: string;
  status: string;
  assignee: string | null;
  assignee_email: string | null;
  due_date: string | null;
  created_at: string;
}

export interface SearchHit {
  type: string;
  id: string;
  title: string;
  subtitle: string;
  snippet: string;
  rank: number;
  contract_id: string | null;
  document_id?: string;
}

export interface SearchResponse {
  query: string;
  count: number;
  counts: Record<string, number>;
  results: SearchHit[];
}

export interface ContractVersion {
  id: string;
  contract: string;
  version_number: number;
  document: string | null;
  document_name: string | null;
  notes: string;
  created_at: string;
}

export interface VersionDiff {
  contract: string;
  from_version: number;
  to_version: number;
  counts: { added: number; removed: number; modified: number; unchanged: number };
  added: Array<{ id: string; clause_type: string; heading: string; text: string; page_number: number }>;
  removed: Array<{ old: { text: string; clause_type: string; page_number: number }; affected_obligations: Array<{ id: string; title: string; status: string }>; impact: string }>;
  modified: Array<{
    old: { text: string; clause_type: string; page_number: number };
    new: { text: string; clause_type: string; page_number: number };
    similarity: number; impact: string;
    affected_obligations: Array<{ id: string; title: string; status: string }>;
  }>;
  unchanged: Array<unknown>;
}

export interface QACitation {
  document_id: string | null;
  document_name: string | null;
  page_number: number | null;
  clause_id: string | null;
  obligation_id: string | null;
  source_text: string;
  contract_id?: string;
  deadline_id?: string;
}

export interface QAResponse {
  answer: string;
  citations: QACitation[];
  intent: string;
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
  risks: (query = '') => request<Paginated<RiskFinding>>(`/api/v1/risks/${query}`),
  riskSummary: (contractId: string) => request<RiskSummary>(`/api/v1/risks/summary/?contract=${contractId}`),
  assessRisks: (contractId: string) =>
    request<RiskSummary>('/api/v1/risks/assess/', { method: 'POST', body: JSON.stringify({ contract: contractId }) }),
  deadlines: (query = '') => request<Paginated<Deadline>>(`/api/v1/deadlines/${query}`),
  completeDeadline: (id: string) => request<Deadline>(`/api/v1/deadlines/${id}/complete/`, { method: 'POST' }),
  reopenDeadline: (id: string) => request<Deadline>(`/api/v1/deadlines/${id}/reopen/`, { method: 'POST' }),
  waiveDeadline: (id: string) => request<Deadline>(`/api/v1/deadlines/${id}/waive/`, { method: 'POST' }),
  generateDeadlines: (contractId: string) =>
    request<{ contract: string; deadlines: number }>('/api/v1/deadlines/generate/', { method: 'POST', body: JSON.stringify({ contract: contractId }) }),
  workspaceMembers: (workspaceId: string) =>
    request<WorkspaceMember[]>(`/api/v1/workspaces/${workspaceId}/members/`),
  aiStatus: () => request<{ provider: string; configured: boolean; model: string | null; note: string }>('/api/v1/ai/status/'),
  askQA: (input: { workspace?: string; contract?: string; question: string }) =>
    request<QAResponse>('/api/v1/ai/ask/', { method: 'POST', body: JSON.stringify(input) }),
  unifiedSearch: (params: string) => request<SearchResponse>(`/api/v1/search/${params}`),

  comments: (query = '') => request<Paginated<Comment>>(`/api/v1/comments/${query}`),
  createComment: (input: { obligation?: string; contract?: string; body: string }) =>
    request<Comment>('/api/v1/comments/', { method: 'POST', body: JSON.stringify(input) }),

  evidenceList: (query = '') => request<Paginated<EvidenceItem>>(`/api/v1/evidence/${query}`),
  uploadEvidence: async (obligationId: string, file: File, note?: string): Promise<EvidenceItem> => {
    const token = getToken();
    const form = new FormData();
    form.append('obligation', obligationId);
    form.append('file', file, file.name);
    if (note) form.append('note', note);
    const res = await fetch(`${API_BASE}/api/v1/evidence/`, {
      method: 'POST', credentials: 'include',
      headers: token ? { Authorization: `Token ${token}` } : {}, body: form,
    });
    const body = await res.json().catch(() => null);
    if (!res.ok) throw new Error((body as { detail?: string })?.detail ?? `Upload failed (${res.status})`);
    return body as EvidenceItem;
  },
  deleteEvidence: async (id: string): Promise<void> => {
    const token = getToken();
    const res = await fetch(`${API_BASE}/api/v1/evidence/${id}/`, {
      method: 'DELETE', credentials: 'include', headers: token ? { Authorization: `Token ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Delete failed (${res.status})`);
  },

  tasks: (query = '') => request<Paginated<TaskItem>>(`/api/v1/tasks/${query}`),
  createTask: (input: { contract?: string; obligation?: string; title: string; assignee?: string; due_date?: string }) =>
    request<TaskItem>('/api/v1/tasks/', { method: 'POST', body: JSON.stringify(input) }),
  updateTask: (id: string, input: Partial<TaskItem>) =>
    request<TaskItem>(`/api/v1/tasks/${id}/`, { method: 'PATCH', body: JSON.stringify(input) }),

  startObligation: (id: string) => request<Obligation>(`/api/v1/obligations/${id}/start/`, { method: 'POST' }),
  completeObligation: (id: string) => request<Obligation>(`/api/v1/obligations/${id}/complete/`, { method: 'POST' }),
  reopenObligation: (id: string) => request<Obligation>(`/api/v1/obligations/${id}/reopen/`, { method: 'POST' }),
  waiveObligation: (id: string, reason?: string) =>
    request<Obligation>(`/api/v1/obligations/${id}/waive/`, { method: 'POST', body: JSON.stringify({ reason: reason ?? '' }) }),
  assignObligation: (id: string, email: string) =>
    request<Obligation>(`/api/v1/obligations/${id}/assign/`, { method: 'POST', body: JSON.stringify({ email }) }),
  contractVersions: (contractId: string) =>
    request<ContractVersion[]>(`/api/v1/contracts/${contractId}/versions/`),
  compareVersions: (contractId: string, from: number, to: number) =>
    request<VersionDiff>(`/api/v1/contracts/${contractId}/compare/?from=${from}&to=${to}`),
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
