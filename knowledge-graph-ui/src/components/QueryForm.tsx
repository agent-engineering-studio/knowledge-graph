"use client";

import { useState } from "react";
import { Box, Button, HStack, Input, Stack, Textarea } from "@chakra-ui/react";

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
    <Box borderWidth="1px" borderRadius="md" p={4}>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (query.trim()) onSubmit(query.trim(), threadId, topK, maxHops);
        }}
      >
        <Stack gap={3}>
          <Box>
            <Box as="label" fontSize="sm" fontWeight={500} mb={1} display="block">Query</Box>
            <Textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              rows={3}
              placeholder="Ask a question about your knowledge graph..."
            />
          </Box>
          <HStack align="flex-end" gap={3}>
            <Box>
              <Box as="label" fontSize="sm" fontWeight={500} mb={1} display="block">Thread ID</Box>
              <Input
                value={threadId}
                onChange={(e) => setThreadId(e.target.value)}
                w="140px"
              />
            </Box>
            <Box>
              <Box as="label" fontSize="sm" fontWeight={500} mb={1} display="block">Top K</Box>
              <Input
                type="number"
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                min={1}
                max={50}
                w="90px"
              />
            </Box>
            <Box>
              <Box as="label" fontSize="sm" fontWeight={500} mb={1} display="block">Max Hops</Box>
              <Input
                type="number"
                value={maxHops}
                onChange={(e) => setMaxHops(Number(e.target.value))}
                min={1}
                max={5}
                w="90px"
              />
            </Box>
            <Button
              type="submit"
              loading={loading}
              disabled={!query.trim()}
              colorPalette="blue"
            >
              Search
            </Button>
          </HStack>
        </Stack>
      </form>
    </Box>
  );
}
