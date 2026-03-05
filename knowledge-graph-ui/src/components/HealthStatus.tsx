"use client";

import { useEffect, useState } from "react";
import { getHealth, type HealthResponse } from "@/lib/api-client";

export function HealthStatus() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const ctrl = new AbortController();
    getHealth(ctrl.signal)
      .then(setHealth)
      .catch((e) => {
        if (!ctrl.signal.aborted) setError(e.message);
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, []);

  if (loading) return <div className="text-sm text-gray-500">Checking services...</div>;
  if (error) return <div className="text-sm text-red-600">API unreachable: {error}</div>;
  if (!health) return null;

  const services = [
    { name: "Neo4j", ok: health.neo4j },
    { name: "Redis", ok: health.redis },
    { name: "Ollama", ok: health.ollama },
  ];

  return (
    <div className="flex gap-4 items-center">
      <span
        className={`text-sm font-medium ${
          health.status === "healthy" ? "text-green-600" : "text-yellow-600"
        }`}
      >
        {health.status === "healthy" ? "All services healthy" : "Degraded"}
      </span>
      {services.map((s) => (
        <span key={s.name} className="flex items-center gap-1 text-xs text-gray-600">
          <span className={`inline-block w-2 h-2 rounded-full ${s.ok ? "bg-green-500" : "bg-red-500"}`} />
          {s.name}
        </span>
      ))}
    </div>
  );
}
