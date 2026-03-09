"use client";

import { useCallback, useRef, useState } from "react";
import { postQuery, type RAGResponse } from "@/lib/api-client";
import { QueryForm } from "@/components/QueryForm";
import { QueryResults } from "@/components/QueryResults";

export default function QueryPage() {
  const [result, setResult] = useState<RAGResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleSubmit = useCallback(
    async (query: string, threadId: string, topK: number, maxHops: number) => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      setError(null);
      setResult(null);
      setLoading(true);

      try {
        const res = await postQuery(
          { query, thread_id: threadId, top_k: topK, max_hops: maxHops },
          ctrl.signal,
        );
        setResult(res);
      } catch (e: unknown) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "Query failed");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Search / Query</h1>

      <QueryForm onSubmit={handleSubmit} loading={loading} />

      {loading && (
        <div className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded p-3 text-sm text-blue-700">
          <span className="shrink-0 animate-spin inline-block w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full" />
          <span>Ricerca semantica e arricchimento grafo in corso…</span>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 text-sm">
          {error}
        </div>
      )}

      <QueryResults result={result} />
    </div>
  );
}
