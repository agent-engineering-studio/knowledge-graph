"use client";

import type { RAGResponse } from "@/lib/api-client";
import {
  Accordion,
  Alert,
  Badge,
  Box,
  Code,
  HStack,
  Stack,
  Text,
} from "@chakra-ui/react";

interface Props {
  result: RAGResponse | null;
}

export function QueryResults({ result }: Props) {
  if (!result) return null;

  return (
    <Stack gap={4}>
      {/* Semantic search results */}
      {result.sources.length > 0 && (
        <Box borderWidth="1px" borderRadius="md" p={4}>
          <Text fontWeight={600} mb={3}>
            Risultati ricerca semantica ({result.sources.length})
          </Text>
          <Stack gap={3}>
            {result.sources.map((s, i) => (
              <Box key={i} borderWidth="1px" borderRadius="md" p={3} bg="gray.50">
                <HStack gap={2} mb={1} flexWrap="wrap">
                  {s.document_name && (
                    <Text fontSize="sm" fontWeight={500}>{s.document_name}</Text>
                  )}
                  {s.page_number != null && (
                    <Text fontSize="xs" color="gray.500">
                      p.{s.page_number + 1}{s.total_pages ? `/${s.total_pages}` : ""}
                    </Text>
                  )}
                  <Code fontSize="xs">{s.doc_id.slice(0, 8)}…</Code>
                </HStack>
                <Text fontSize="sm" style={{ whiteSpace: "pre-wrap" }}>{s.text_preview}</Text>
              </Box>
            ))}
          </Stack>
        </Box>
      )}

      {/* Graph nodes & edges */}
      {(result.nodes_used.length > 0 || result.edges_used.length > 0) && (
        <Accordion.Root collapsible variant="outline">
          {result.nodes_used.length > 0 && (
            <Accordion.Item value="nodes">
              <Accordion.ItemTrigger>
                <HStack gap={2}>
                  <Text fontSize="sm" fontWeight={600}>Nodi del grafo</Text>
                  <Badge size="sm" colorPalette="blue" variant="subtle">{result.nodes_used.length}</Badge>
                </HStack>
              </Accordion.ItemTrigger>
              <Accordion.ItemContent>
                <Stack gap={1} p={2}>
                  {result.nodes_used.map((node, i) => (
                    <Code key={i} colorPalette="blue">{node}</Code>
                  ))}
                </Stack>
              </Accordion.ItemContent>
            </Accordion.Item>
          )}
          {result.edges_used.length > 0 && (
            <Accordion.Item value="edges">
              <Accordion.ItemTrigger>
                <HStack gap={2}>
                  <Text fontSize="sm" fontWeight={600}>Relazioni</Text>
                  <Badge size="sm" colorPalette="purple" variant="subtle">{result.edges_used.length}</Badge>
                </HStack>
              </Accordion.ItemTrigger>
              <Accordion.ItemContent>
                <Stack gap={1} p={2}>
                  {result.edges_used.map((edge, i) => (
                    <Code key={i} colorPalette="purple">{edge}</Code>
                  ))}
                </Stack>
              </Accordion.ItemContent>
            </Accordion.Item>
          )}
        </Accordion.Root>
      )}

      {/* No results */}
      {result.sources.length === 0 && result.nodes_used.length === 0 && (
        <Alert.Root status="warning">
          <Alert.Description>{result.answer}</Alert.Description>
        </Alert.Root>
      )}

      {/* Metadata */}
      <HStack gap={6} flexWrap="wrap">
        <Text fontSize="xs" color="gray.500">Intent: {result.query_intent}</Text>
        <Text fontSize="xs" color="gray.500">Documenti: {result.sources.length}</Text>
        <Text fontSize="xs" color="gray.500">Nodi: {result.nodes_used.length}</Text>
        <Text fontSize="xs" color="gray.500">Relazioni: {result.edges_used.length}</Text>
        <Text fontSize="xs" color="gray.500">Tempo: {result.processing_time_ms.toFixed(0)}ms</Text>
      </HStack>
    </Stack>
  );
}
