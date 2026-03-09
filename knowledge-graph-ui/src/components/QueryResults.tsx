"use client";

import type { RAGResponse } from "@/lib/api-client";

interface Props {
  result: RAGResponse | null;
  streamedAnswer: string;
  streaming: boolean;
}

export function QueryResults({ result, streamedAnswer, streaming }: Props) {
  const answer = streaming || streamedAnswer ? streamedAnswer : result?.answer;

  if (!answer && !streaming) return null;

  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border p-5">
        <h3 className="font-semibold mb-2">Answer</h3>
        <p className="text-sm whitespace-pre-wrap">{answer}{streaming && <span className="animate-pulse">|</span>}</p>
      </div>

      {result && (
        <>
          {result.sources.length > 0 && (
            <div className="bg-white rounded-lg border p-5">
              <h3 className="font-semibold mb-2">Sources ({result.sources.length})</h3>
              <div className="space-y-2">
                {result.sources.map((s, i) => (
                  <div key={i} className="text-xs bg-gray-50 rounded p-2">
                    <div className="flex flex-wrap items-center gap-2">
                      {s.document_name && (
                        <span className="font-medium text-gray-800">{s.document_name}</span>
                      )}
                      {s.page_number != null && (
                        <span className="text-gray-500">
                          p.{s.page_number + 1}
                          {s.total_pages ? `/${s.total_pages}` : ""}
                        </span>
                      )}
                      {s.score != null && (
                        <span className="text-gray-400">score: {s.score.toFixed(3)}</span>
                      )}
                      <span className="text-gray-400 font-mono">{s.doc_id.slice(0, 8)}…</span>
                    </div>
                    <p className="text-gray-600 mt-1">{s.text_preview}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-4 text-xs text-gray-500">
            <span>Intent: {result.query_intent}</span>
            <span>Nodes: {result.nodes_used.length}</span>
            <span>Edges: {result.edges_used.length}</span>
            <span>Time: {result.processing_time_ms.toFixed(0)}ms</span>
          </div>
        </>
      )}
    </div>
  );
}
