"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { postQuery, type RAGResponse } from "@/lib/api-client";
import { Alert, Box, Button, Center, HStack, Input, Stack, Text } from "@chakra-ui/react";

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
        const container = canvasRef.current!.parentElement!;
        if (graphRef.current) {
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
    <Stack gap={4}>
      <HStack align="flex-end" gap={3}>
        <Box flex={1}>
          <Box as="label" fontSize="sm" fontWeight={500} mb={1} display="block">Query to explore</Box>
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Enter a topic to visualize its knowledge graph..."
          />
        </Box>
        <Box>
          <Box as="label" fontSize="sm" fontWeight={500} mb={1} display="block">Thread ID</Box>
          <Input
            value={threadId}
            onChange={(e) => setThreadId(e.target.value)}
            w="140px"
          />
        </Box>
        <Button
          onClick={handleSearch}
          loading={loading}
          disabled={!query.trim()}
          colorPalette="blue"
        >
          Explore
        </Button>
      </HStack>

      {error && (
        <Alert.Root status="error">
          <Alert.Description>{error}</Alert.Description>
        </Alert.Root>
      )}

      <Box borderWidth="1px" borderRadius="md" minH="500px" overflow="hidden">
        {graphData ? (
          <div ref={(el) => { if (el && !el.querySelector("canvas")) el.innerHTML = '<canvas></canvas>'; }}>
            <canvas ref={canvasRef} />
          </div>
        ) : (
          <Center h="500px">
            <Text color="gray.500" fontSize="sm">Enter a query above to explore the knowledge graph</Text>
          </Center>
        )}
      </Box>
    </Stack>
  );
}
