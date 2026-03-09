"use client";

import { useState } from "react";
import type { RAGResponse } from "@/lib/api-client";

interface Props {
  result: RAGResponse | null;
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

export function QueryResults({ result }: Props) {
  if (!result) return null;

  return (
    <div className="space-y-4">
      {/* Semantic search results */}
      {result.sources.length > 0 && (
        <div className="bg-white rounded-lg border p-5">
          <h3 className="font-semibold mb-3">Risultati ricerca semantica ({result.sources.length})</h3>
          <div className="space-y-3">
            {result.sources.map((s, i) => (
              <div key={i} className="bg-gray-50 rounded p-3 text-sm">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  {s.document_name && (
                    <span className="font-medium text-gray-800">{s.document_name}</span>
                  )}
                  {s.page_number != null && (
                    <span className="text-gray-500 text-xs">
                      p.{s.page_number + 1}{s.total_pages ? `/${s.total_pages}` : ""}
                    </span>
                  )}
                  <span className="text-gray-400 text-xs font-mono">{s.doc_id.slice(0, 8)}…</span>
                </div>
                <p className="text-gray-700 whitespace-pre-wrap">{s.text_preview}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Graph nodes */}
      {result.nodes_used.length > 0 && (
        <Collapsible title="Nodi del grafo" count={result.nodes_used.length}>
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
        <Collapsible title="Relazioni" count={result.edges_used.length}>
          <ul className="mt-1 space-y-1">
            {result.edges_used.map((edge, i) => (
              <li key={i} className="text-xs bg-purple-50 text-purple-800 rounded px-2 py-1 font-mono">
                {edge}
              </li>
            ))}
          </ul>
        </Collapsible>
      )}

      {/* No results */}
      {result.sources.length === 0 && result.nodes_used.length === 0 && (
        <div className="bg-yellow-50 border border-yellow-200 text-yellow-800 rounded p-4 text-sm">
          {result.answer}
        </div>
      )}

      {/* Metadata */}
      <div className="flex gap-4 text-xs text-gray-400">
        <span>Intent: {result.query_intent}</span>
        <span>Documenti: {result.sources.length}</span>
        <span>Nodi: {result.nodes_used.length}</span>
        <span>Relazioni: {result.edges_used.length}</span>
        <span>Tempo: {result.processing_time_ms.toFixed(0)}ms</span>
      </div>
    </div>
  );
}
