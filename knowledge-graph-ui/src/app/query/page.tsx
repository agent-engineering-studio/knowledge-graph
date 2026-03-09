"use client";

import { useCallback, useRef, useState } from "react";
import { postQuery, streamQuery, type RAGResponse } from "@/lib/api-client";
import { QueryForm } from "@/components/QueryForm";
import { QueryResults } from "@/components/QueryResults";

const STREAMING_ENABLED = process.env.NEXT_PUBLIC_ENABLE_STREAMING !== "false";

type QueryPhase = "idle" | "analyzing" | "streaming" | "loading-metadata";

const PHASE_LABELS: Record<QueryPhase, string> = {
  idle: "",
  analyzing: "Analyzing query — intent classification, vector search, graph enrichment…",
  streaming: "Generating answer…",
  "loading-metadata": "Loading sources and metadata…",
};

export default function QueryPage() {
  const [result, setResult] = useState<RAGResponse | null>(null);
  const [streamedAnswer, setStreamedAnswer] = useState("");
  const [phase, setPhase] = useState<QueryPhase>("idle");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loading = phase !== "idle";
  const streaming = phase === "streaming";

  const handleSubmit = useCallback(
    async (query: string, threadId: string, topK: number, maxHops: number) => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      setError(null);
      setResult(null);
      setStreamedAnswer("");
      setPhase("analyzing");

      const body = { query, thread_id: threadId, top_k: topK, max_hops: maxHops };

      try {
        if (STREAMING_ENABLED) {
          let answer = "";
          let firstToken = true;
          for await (const token of streamQuery(body, ctrl.signal)) {
            if (firstToken) {
              setPhase("streaming");
              firstToken = false;
            }
            answer += token;
            setStreamedAnswer(answer);
          }
          setPhase("loading-metadata");
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
      } finally {
        setPhase("idle");
      }
    },
    [],
  );

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Search / Query</h1>

      <QueryForm onSubmit={handleSubmit} loading={loading} />

      {/* Phase status bar */}
      {phase !== "idle" && (
        <div className="flex items-center gap-3 bg-blue-50 border border-blue-200 rounded p-3 text-sm text-blue-700">
          <span className="shrink-0 animate-spin inline-block w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full" />
          <span>{PHASE_LABELS[phase]}</span>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 text-sm">
          {error}
        </div>
      )}

      <QueryResults result={result} streamedAnswer={streamedAnswer} streaming={streaming} />
    </div>
  );
}
