"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { postQuery, type RAGResponse } from "@/lib/api-client";

interface GraphNode {
  id: string;
  label: string;
}

interface GraphLink {
  source: string;
  target: string;
  label: string;
}

interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

function buildGraphData(result: RAGResponse): GraphData {
  const nodeSet = new Map<string, GraphNode>();
  const links: GraphLink[] = [];

  for (const nodeId of result.nodes_used) {
    if (!nodeSet.has(nodeId)) {
      nodeSet.set(nodeId, { id: nodeId, label: nodeId });
    }
  }

  for (const edge of result.edges_used) {
    // edges come as "source --RELATION--> target" format typically
    const match = edge.match(/^(.+?)\s*--(\w+)-->\s*(.+)$/);
    if (match) {
      const [, src, rel, tgt] = match;
      if (!nodeSet.has(src)) nodeSet.set(src, { id: src, label: src });
      if (!nodeSet.has(tgt)) nodeSet.set(tgt, { id: tgt, label: tgt });
      links.push({ source: src, target: tgt, label: rel });
    }
  }

  return { nodes: Array.from(nodeSet.values()), links };
}

export function GraphView() {
  const [query, setQuery] = useState("");
  const [threadId, setThreadId] = useState("default");
  const [graphData, setGraphData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<any>(null);

  const handleSearch = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const result = await postQuery({ query: query.trim(), thread_id: threadId, top_k: 10, max_hops: 2 });
      const data = buildGraphData(result);
      if (data.nodes.length === 0) {
        setError("No graph nodes returned for this query.");
        setGraphData(null);
      } else {
        setGraphData(data);
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to fetch graph data");
    } finally {
      setLoading(false);
    }
  }, [query, threadId]);

  useEffect(() => {
    if (!graphData || !canvasRef.current) return;

    let cancelled = false;

    (async () => {
      try {
        const ForceGraph = (await import("react-force-graph-2d")).default;
        if (cancelled) return;
        // react-force-graph-2d expects a container element, we render it imperatively
        const container = canvasRef.current!.parentElement!;
        if (graphRef.current) {
          // cleanup previous
          container.innerHTML = '<canvas></canvas>';
        }

        const div = document.createElement("div");
        div.style.width = "100%";
        div.style.height = "500px";
        container.innerHTML = "";
        container.appendChild(div);

        const { createRoot } = await import("react-dom/client");
        const { createElement } = await import("react");

        const root = createRoot(div);
        root.render(
          createElement(ForceGraph, {
            graphData,
            nodeLabel: "label",
            linkLabel: "label",
            nodeAutoColorBy: "label",
            linkDirectionalArrowLength: 4,
            linkDirectionalArrowRelPos: 1,
            width: container.clientWidth,
            height: 500,
          }),
        );
        graphRef.current = root;
      } catch {
        if (!cancelled) setError("Failed to render graph visualization");
      }
    })();

    return () => { cancelled = true; };
  }, [graphData]);

  return (
    <div className="space-y-4">
      <div className="flex gap-3 items-end">
        <div className="flex-1">
          <label className="block text-sm font-medium mb-1">Query to explore</label>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            className="w-full border rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
            placeholder="Enter a topic to visualize its knowledge graph..."
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Thread ID</label>
          <input
            value={threadId}
            onChange={(e) => setThreadId(e.target.value)}
            className="border rounded px-2 py-1 text-sm w-32"
          />
        </div>
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Loading..." : "Explore"}
        </button>
      </div>

      {error && <div className="bg-red-50 border border-red-200 text-red-700 rounded p-3 text-sm">{error}</div>}

      <div className="bg-white rounded-lg border overflow-hidden" style={{ minHeight: 500 }}>
        {graphData ? (
          <div ref={(el) => { if (el && !el.querySelector("canvas")) el.innerHTML = '<canvas></canvas>'; }}>
            <canvas ref={canvasRef} />
          </div>
        ) : (
          <div className="flex items-center justify-center h-[500px] text-gray-400 text-sm">
            Enter a query above to explore the knowledge graph
          </div>
        )}
      </div>
    </div>
  );
}
