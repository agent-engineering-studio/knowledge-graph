"use client";

import { useState } from "react";
import type { RAGResponse } from "@/lib/api-client";

interface Props {
  result: RAGResponse | null;
  streamedAnswer: string;
  streaming: boolean;
}

function Collapsible({ title, count, children }: { title: string; count: number; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  if (count === 0) return null;
  return (
    <div className="bg-white rounded-lg border">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-5 py-3 text-sm font-semibold hover:bg-gray-50 transition-colors"
      >
        <span>{title} <span className="font-normal text-gray-500">({count})</span></span>
        <span className="text-gray-400 text-xs">{open ? "▲" : "▼"}</span>
      </button>
      {open && <div className="px-5 pb-4">{children}</div>}
    </div>
  );
}

export function QueryResults({ result, streamedAnswer, streaming }: Props) {
  const answer = streaming || streamedAnswer ? streamedAnswer : result?.answer;

  if (!answer && !streaming) return null;

  return (
    <div className="space-y-4">
      {/* Answer */}
      <div className="bg-white rounded-lg border p-5">
        <h3 className="font-semibold mb-2">Answer</h3>
        <p className="text-sm whitespace-pre-wrap">
          {answer}
          {streaming && <span className="animate-pulse">|</span>}
        </p>
      </div>

      {result && (
        <>
          {/* Sources */}
          {result.sources.length > 0 && (
            <Collapsible title="Sources" count={result.sources.length}>
              <div className="space-y-2 mt-1">
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
            </Collapsible>
          )}

          {/* Graph nodes */}
          {result.nodes_used.length > 0 && (
            <Collapsible title="Graph Nodes" count={result.nodes_used.length}>
              <ul className="mt-1 space-y-1">
                {result.nodes_used.map((node, i) => (
                  <li key={i} className="text-xs bg-blue-50 text-blue-800 rounded px-2 py-1 font-mono">
                    {node}
                  </li>
                ))}
              </ul>
            </Collapsible>
          )}

          {/* Graph relationships */}
          {result.edges_used.length > 0 && (
            <Collapsible title="Relationships" count={result.edges_used.length}>
              <ul className="mt-1 space-y-1">
                {result.edges_used.map((edge, i) => (
                  <li key={i} className="text-xs bg-purple-50 text-purple-800 rounded px-2 py-1 font-mono">
                    {edge}
                  </li>
                ))}
              </ul>
            </Collapsible>
          )}

          {/* Metadata bar */}
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
