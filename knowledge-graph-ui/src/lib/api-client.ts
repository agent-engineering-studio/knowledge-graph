/**
 * Typed API client for knowledge-graph-api.
 * Mirrors the FastAPI schemas to ensure contract safety.
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
}

export interface RAGResponse {
  answer: string;
  sources: Source[];
  nodes_used: string[];
  edges_used: string[];
  query_intent: string;
  processing_time_ms: number;
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

/**
 * Stream a RAG query via SSE. Yields each token as it arrives.
 */
export async function* streamQuery(
  body: QueryRequest,
  signal?: AbortSignal,
): AsyncGenerator<string> {
  const res = await fetch(`${API_URL}/query/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok || !res.body) {
    throw new Error(`Stream failed: ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6);
        if (data === "[DONE]") return;
        if (data.startsWith("[ERROR]")) throw new Error(data);
        yield data;
      }
    }
  }
}
