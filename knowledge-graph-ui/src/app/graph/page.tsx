"use client";

import { GraphView } from "@/components/GraphView";

export default function GraphPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Graph View</h1>
        <p className="text-gray-600 text-sm mt-1">
          Query the knowledge graph and visualize entities and their relationships.
        </p>
      </div>
      <GraphView />
    </div>
  );
}
