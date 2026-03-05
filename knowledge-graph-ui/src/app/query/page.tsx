"use client";

import { useCallback, useRef, useState } from "react";
import { postQuery, streamQuery, type RAGResponse } from "@/lib/api-client";
import { QueryForm } from "@/components/QueryForm";
import { QueryResults } from "@/components/QueryResults";

const STREAMING_ENABLED = process.env.NEXT_PUBLIC_ENABLE_STREAMING !== "false";

export default function QueryPage() {
  const [result, setResult] = useState<RAGResponse | null>(null);
  const [streamedAnswer, setStreamedAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleSubmit = useCallback(
    async (query: string, threadId: string, topK: number, maxHops: number) => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      setError(null);
      setResult(null);
      setStreamedAnswer("");
      setLoading(true);

      const body = { query, thread_id: threadId, top_k: topK, max_hops: maxHops };

      try {
        if (STREAMING_ENABLED) {
          setStreaming(true);
          let answer = "";
          for await (const token of streamQuery(body, ctrl.signal)) {
            answer += token;
            setStreamedAnswer(answer);
          }
          setStreaming(false);
          // Also fetch structured result for sources/metadata
          const structured = await postQuery(body, ctrl.signal);
          setResult(structured);
          setStreamedAnswer(structured.answer);
        } else {
          const res = await postQuery(body, ctrl.signal);
          setResult(res);
        }
      } catch (e: unknown) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "Query failed");
        setStreaming(false);
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

      {error && <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 text-sm">{error}</div>}

      <QueryResults result={result} streamedAnswer={streamedAnswer} streaming={streaming} />
    </div>
  );
}
