"use client";

import { useEffect, useState } from "react";
import { getHealth, type HealthResponse } from "@/lib/api-client";
import { Badge, Box, HStack, Spinner, Text } from "@chakra-ui/react";

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

  if (loading) {
    return (
      <HStack gap={2}>
        <Spinner size="sm" />
        <Text fontSize="sm" color="gray.500">Checking services...</Text>
      </HStack>
    );
  }
  if (error) return <Text fontSize="sm" color="red.500">API unreachable: {error}</Text>;
  if (!health) return null;

  const services = [
    { name: "Neo4j", ok: health.neo4j },
    { name: "Redis", ok: health.redis },
    { name: "Ollama", ok: health.ollama },
  ];

  return (
    <HStack gap={4} flexWrap="wrap">
      <Badge colorPalette={health.status === "healthy" ? "green" : "yellow"} variant="subtle" size="md">
        {health.status === "healthy" ? "All services healthy" : "Degraded"}
      </Badge>
      {services.map((s) => (
        <HStack key={s.name} gap={1}>
          <Box
            w={2}
            h={2}
            borderRadius="full"
            bg={s.ok ? "green.500" : "red.500"}
          />
          <Text fontSize="xs" color="gray.500">{s.name}</Text>
        </HStack>
      ))}
    </HStack>
  );
}
