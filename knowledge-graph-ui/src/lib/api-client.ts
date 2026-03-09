/**
 * Typed API client for knowledge-graph-api and knowledge-graph-agents.
 * Mirrors the FastAPI schemas to ensure contract safety.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const AGENTS_URL = process.env.NEXT_PUBLIC_AGENTS_URL ?? "http://localhost:8002";

// ── Request types ──────────────────────────────────────────────────

export interface IngestRequest {
  file_path: string;
  thread_id: string;
  skip_existing?: boolean;
}

export interface QueryRequest {
  query: string;
  thread_id: string;
  top_k?: number;
  max_hops?: number;
}

// ── Response types ─────────────────────────────────────────────────

export interface HealthResponse {
  status: "healthy" | "degraded";
  neo4j: boolean;
  redis: boolean;
  ollama: boolean;
}

export interface IngestResult {
  document_id: string;
  chunks_processed: number;
  chunks_skipped: number;
  entities_extracted: number;
  relations_extracted: number;
  nodes_created: number;
  edges_created: number;
  processing_time_ms: number;
  errors: string[];
}

export interface Source {
  doc_id: string;
  text_preview: string;
  score: number | null;
  page_number: number | null;
  total_pages: number | null;
  document_name: string | null;
}

export interface RAGResponse {
  answer: string;
  sources: Source[];
  nodes_used: string[];
  edges_used: string[];
  graph_context: string;
  query_intent: string;
  processing_time_ms: number;
}

export interface DocumentRecord {
  base_document_id: string;
  name: string;
  mime_type: string | null;
  total_pages: number;
  created_at: string;
  chunk_count: number;
}

// ── Agents types ───────────────────────────────────────────────────

export interface AgentRunRequest {
  request: string;
  thread_id?: string;
  context?: Record<string, unknown>;
}

export interface AgentPlanStep {
  action: string;
  agent?: string;
  result?: string;
  [key: string]: unknown;
}

export interface AgentRunResponse {
  run_id: string;
  intent: string | null;
  output: string;
  plan: AgentPlanStep[];
  quality: Record<string, unknown> | null;
  duration_ms: number;
  error: string | null;
}

export interface AgentRunRecord {
  run_id: string;
  agent_name: string;
  intent: string;
  input_summary: string;
  output_summary: string;
  tool_calls: string[];
  duration_ms: number;
  status: "success" | "failed";
}

// ── API functions ──────────────────────────────────────────────────

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export function getHealth(signal?: AbortSignal) {
  return apiFetch<HealthResponse>("/health", { signal });
}

export function postQuery(body: QueryRequest, signal?: AbortSignal) {
  return apiFetch<RAGResponse>("/query", {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });
}

export function postIngest(body: IngestRequest, signal?: AbortSignal) {
  return apiFetch<IngestResult>("/ingest", {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });
}

export function deleteDocument(documentId: string, signal?: AbortSignal) {
  return apiFetch<{ deleted: string }>(`/documents/${encodeURIComponent(documentId)}`, {
    method: "DELETE",
    signal,
  });
}

export async function uploadAndIngest(
  file: File,
  threadId: string,
  skipExisting: boolean,
  signal?: AbortSignal,
): Promise<IngestResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("thread_id", threadId);
  form.append("skip_existing", String(skipExisting));
  // Do NOT set Content-Type: browser must set it with the multipart boundary
  const res = await fetch(`${API_URL}/ingest/upload`, { method: "POST", body: form, signal });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<IngestResult>;
}

export async function listDocuments(namespace: string, signal?: AbortSignal): Promise<DocumentRecord[]> {
  // API returns { documents: DocumentRecord[] }
  const res = await apiFetch<{ documents: DocumentRecord[] }>(
    `/documents/${encodeURIComponent(namespace)}`,
    { signal },
  );
  return res.documents ?? [];
}

// ── Agents API functions ───────────────────────────────────────────

async function agentsFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${AGENTS_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Agents API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export function postAgentRun(body: AgentRunRequest, signal?: AbortSignal) {
  return agentsFetch<AgentRunResponse>("/agents/run", {
    method: "POST",
    body: JSON.stringify(body),
    signal,
  });
}

export function getAgentRuns(limit = 10, signal?: AbortSignal) {
  return agentsFetch<AgentRunRecord[]>(`/agents/runs?limit=${limit}`, { signal });
}

export async function uploadAndRunAgent(
  file: File,
  threadId: string,
  message?: string,
  signal?: AbortSignal,
): Promise<AgentRunResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("thread_id", threadId);
  form.append("message", message || `Carica il documento: ${file.name}`);
  const res = await fetch(`${AGENTS_URL}/agents/run/upload`, {
    method: "POST",
    body: form,
    signal,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`Agents API ${res.status}: ${text}`);
  }
  return res.json() as Promise<AgentRunResponse>;
}

