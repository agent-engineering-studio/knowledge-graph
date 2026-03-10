"use client";

import { useCallback, useRef, useState } from "react";
import { postQuery, type RAGResponse } from "@/lib/api-client";
import { QueryForm } from "@/components/QueryForm";
import { QueryResults } from "@/components/QueryResults";
import { Alert, HStack, Spinner, Stack, Text } from "@chakra-ui/react";

export default function QueryPage() {
  const [result, setResult] = useState<RAGResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const handleSubmit = useCallback(
    async (query: string, threadId: string, topK: number, maxHops: number) => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      setError(null);
      setResult(null);
      setLoading(true);

      try {
        const res = await postQuery(
          { query, thread_id: threadId, top_k: topK, max_hops: maxHops },
          ctrl.signal,
        );
        setResult(res);
      } catch (e: unknown) {
        if (e instanceof DOMException && e.name === "AbortError") return;
        setError(e instanceof Error ? e.message : "Query failed");
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return (
    <Stack gap={4}>
      <Text fontSize="3xl" fontWeight={700}>Search / Query</Text>

      <QueryForm onSubmit={handleSubmit} loading={loading} />

      {loading && (
        <Alert.Root status="info">
          <Alert.Description>
            <HStack gap={2}>
              <Spinner size="sm" />
              <Text fontSize="sm">Ricerca semantica e arricchimento grafo in corso…</Text>
            </HStack>
          </Alert.Description>
        </Alert.Root>
      )}

      {error && (
        <Alert.Root status="error">
          <Alert.Description>{error}</Alert.Description>
        </Alert.Root>
      )}

      <QueryResults result={result} />
    </Stack>
  );
}
