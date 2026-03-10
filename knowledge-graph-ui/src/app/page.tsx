import Link from "next/link";
import { HealthStatus } from "@/components/HealthStatus";
import { Badge, Box, Code, HStack, SimpleGrid, Stack, Text } from "@chakra-ui/react";

const MCP_TOOLS = [
  { name: "kg_health", desc: "Check status of all services" },
  { name: "kg_query", desc: "Hybrid RAG query (vector + graph)" },
  { name: "kg_ingest", desc: "Add a document to the knowledge graph" },
  { name: "kg_cypher", desc: "Run read-only Cypher on Neo4j" },
  { name: "kg_traverse", desc: "Explore node neighbours" },
  { name: "kg_search_nodes", desc: "Find a node by name" },
  { name: "kg_list_documents", desc: "List documents in a namespace" },
  { name: "kg_delete_document", desc: "Delete a document from the vector store" },
];

const FEATURE_CARDS = [
  { href: "/query", title: "Search / Query", desc: "Ask natural language questions. Uses hybrid vector + graph RAG pipeline.", color: "blue.700" },
  { href: "/graph", title: "Graph View", desc: "Explore entities and relationships extracted from your documents.", color: "blue.700" },
  { href: "/ingest", title: "Document Ingestion", desc: "Add PDF, DOCX, or TXT files to the knowledge graph.", color: "green.700" },
  { href: "/chat", title: "Agent Chat", desc: "Chat with the multi-agent orchestration layer.", color: "purple.700" },
];

export default function DashboardPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const mcpUrl = process.env.NEXT_PUBLIC_MCP_URL ?? "http://localhost:8080";
  const agentsUrl = process.env.NEXT_PUBLIC_AGENTS_URL ?? "http://localhost:8002";

  return (
    <Stack gap={6}>
      <div>
        <Text fontSize="3xl" fontWeight={700}>Knowledge Graph Lab</Text>
        <Text color="gray.500" mt={1}>
          RAG pipeline with Neo4j graph DB, Redis vector store, and Ollama LLM inference.
        </Text>
      </div>

      <Box borderWidth="1px" borderRadius="md" p={4}>
        <Text fontWeight={600} mb={3}>Service Health</Text>
        <HealthStatus />
      </Box>

      <SimpleGrid columns={{ base: 1, sm: 2 }} gap={4}>
        {FEATURE_CARDS.map((card) => (
          <Link key={card.href} href={card.href} style={{ textDecoration: "none" }}>
            <Box borderWidth="1px" borderRadius="md" p={4} h="100%" _hover={{ shadow: "md" }}>
              <Text fontWeight={600} color={card.color} mb={1}>{card.title}</Text>
              <Text fontSize="sm" color="gray.500">{card.desc}</Text>
            </Box>
          </Link>
        ))}
      </SimpleGrid>

      <Box borderWidth="1px" borderRadius="md" p={4}>
        <HStack justify="space-between" mb={3}>
          <Text fontWeight={600}>MCP Server</Text>
          <a href={`${mcpUrl}/sse`} target="_blank" rel="noreferrer" style={{ fontSize: "12px", color: "#3182ce" }}>
            {mcpUrl}/sse
          </a>
        </HStack>
        <Text fontSize="sm" color="gray.500" mb={3}>
          The MCP server exposes the knowledge graph as tools for Claude Desktop and Claude Code.
          Connect via SSE at <Code>{mcpUrl}/sse</Code>.
        </Text>
        <SimpleGrid columns={{ base: 1, sm: 2 }} gap={2} mb={4}>
          {MCP_TOOLS.map((tool) => (
            <HStack key={tool.name} gap={2} align="flex-start">
              <Badge variant="subtle" colorPalette="gray" size="sm" style={{ fontFamily: "monospace", flexShrink: 0 }}>
                {tool.name}
              </Badge>
              <Text fontSize="xs" color="gray.500">{tool.desc}</Text>
            </HStack>
          ))}
        </SimpleGrid>
        <Code display="block" whiteSpace="pre" p={3} borderRadius="md">
          {`{
  "mcpServers": {
    "knowledge-graph": {
      "type": "sse",
      "url": "${mcpUrl}/sse"
    }
  }
}`}
        </Code>
      </Box>

      <Box borderWidth="1px" borderRadius="md" p={4}>
        <Text fontWeight={600} mb={3}>Quick Links</Text>
        <Stack gap={1}>
          <Text fontSize="sm">API Docs: <a href={`${apiUrl}/docs`} target="_blank" rel="noreferrer" style={{ color: "#3182ce" }}>{apiUrl}/docs</a></Text>
          <Text fontSize="sm">Agents API Docs: <a href={`${agentsUrl}/docs`} target="_blank" rel="noreferrer" style={{ color: "#3182ce" }}>{agentsUrl}/docs</a></Text>
          <Text fontSize="sm">Neo4j Browser: <a href="http://localhost:7474" target="_blank" rel="noreferrer" style={{ color: "#3182ce" }}>localhost:7474</a></Text>
          <Text fontSize="sm">RedisInsight: <a href="http://localhost:5540" target="_blank" rel="noreferrer" style={{ color: "#3182ce" }}>localhost:5540</a></Text>
        </Stack>
      </Box>
    </Stack>
  );
}
