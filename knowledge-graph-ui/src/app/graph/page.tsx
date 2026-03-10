"use client";

import { GraphView } from "@/components/GraphView";
import { Stack, Text } from "@chakra-ui/react";

export default function GraphPage() {
  return (
    <Stack gap={4}>
      <div>
        <Text fontSize="3xl" fontWeight={700}>Graph View</Text>
        <Text color="gray.500" fontSize="sm" mt={1}>
          Query the knowledge graph and visualize entities and their relationships.
        </Text>
      </div>
      <GraphView />
    </Stack>
  );
}
