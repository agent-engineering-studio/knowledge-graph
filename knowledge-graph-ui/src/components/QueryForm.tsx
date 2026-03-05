"use client";

import { useState } from "react";

interface Props {
  onSubmit: (query: string, threadId: string, topK: number, maxHops: number) => void;
  loading: boolean;
}

export function QueryForm({ onSubmit, loading }: Props) {
  const [query, setQuery] = useState("");
  const [threadId, setThreadId] = useState("default");
  const [topK, setTopK] = useState(10);
  const [maxHops, setMaxHops] = useState(2);

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (query.trim()) onSubmit(query.trim(), threadId, topK, maxHops);
      }}
      className="bg-white rounded-lg border p-5 space-y-4"
    >
      <div>
        <label className="block text-sm font-medium mb-1">Query</label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={3}
          className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          placeholder="Ask a question about your knowledge graph..."
        />
      </div>
      <div className="flex gap-4 items-end flex-wrap">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Thread ID</label>
          <input
            value={threadId}
            onChange={(e) => setThreadId(e.target.value)}
            className="border rounded px-2 py-1 text-sm w-32"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Top K</label>
          <input
            type="number"
            value={topK}
            onChange={(e) => setTopK(Number(e.target.value))}
            min={1}
            max={50}
            className="border rounded px-2 py-1 text-sm w-20"
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Max Hops</label>
          <input
            type="number"
            value={maxHops}
            onChange={(e) => setMaxHops(Number(e.target.value))}
            min={1}
            max={5}
            className="border rounded px-2 py-1 text-sm w-20"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !query.trim()}
          className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Querying..." : "Search"}
        </button>
      </div>
    </form>
  );
}
