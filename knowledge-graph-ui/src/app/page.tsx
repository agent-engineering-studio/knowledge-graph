import Link from "next/link";
import { HealthStatus } from "@/components/HealthStatus";

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

export default function DashboardPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const mcpUrl = process.env.NEXT_PUBLIC_MCP_URL ?? "http://localhost:8080";
  const agentsUrl = process.env.NEXT_PUBLIC_AGENTS_URL ?? "http://localhost:8002";

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Knowledge Graph Lab</h1>
        <p className="text-gray-600 mt-1">
          RAG pipeline with Neo4j graph DB, Redis vector store, and Ollama LLM inference.
        </p>
      </div>

      {/* Health */}
      <section className="bg-white rounded-lg border p-5">
        <h2 className="font-semibold mb-3">Service Health</h2>
        <HealthStatus />
      </section>

      {/* Feature cards */}
      <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Link
          href="/query"
          className="bg-white rounded-lg border p-5 hover:border-blue-400 transition-colors"
        >
          <h3 className="font-semibold text-blue-700">Search / Query</h3>
          <p className="text-sm text-gray-600 mt-1">
            Ask natural language questions. Uses hybrid vector + graph RAG pipeline.
          </p>
        </Link>
        <Link
          href="/graph"
          className="bg-white rounded-lg border p-5 hover:border-blue-400 transition-colors"
        >
          <h3 className="font-semibold text-blue-700">Graph View</h3>
          <p className="text-sm text-gray-600 mt-1">
            Explore entities and relationships extracted from your documents.
          </p>
        </Link>
        <Link
          href="/ingest"
          className="bg-white rounded-lg border p-5 hover:border-green-400 transition-colors"
        >
          <h3 className="font-semibold text-green-700">Document Ingestion</h3>
          <p className="text-sm text-gray-600 mt-1">
            Add PDF, DOCX, or TXT files to the knowledge graph. View and manage ingested documents.
          </p>
        </Link>
        <Link
          href="/chat"
          className="bg-white rounded-lg border p-5 hover:border-purple-400 transition-colors"
        >
          <h3 className="font-semibold text-purple-700">Agent Chat</h3>
          <p className="text-sm text-gray-600 mt-1">
            Chat with the multi-agent orchestration layer. Requests are routed through specialist agents.
          </p>
        </Link>
      </section>

      {/* MCP Server */}
      <section className="bg-white rounded-lg border p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold">MCP Server</h2>
          <a
            href={`${mcpUrl}/sse`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-xs text-blue-600 hover:underline"
          >
            {mcpUrl}/sse
          </a>
        </div>
        <p className="text-sm text-gray-600 mb-4">
          The MCP server exposes the knowledge graph as tools for Claude Desktop and Claude Code.
          Connect via SSE transport at <code className="bg-gray-100 px-1 rounded">{mcpUrl}/sse</code>.
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {MCP_TOOLS.map((tool) => (
            <div key={tool.name} className="flex items-start gap-2 text-sm">
              <code className="bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded text-xs shrink-0">
                {tool.name}
              </code>
              <span className="text-gray-500">{tool.desc}</span>
            </div>
          ))}
        </div>
        <div className="mt-4 bg-gray-50 rounded p-3 text-xs text-gray-500 font-mono">
          <p className="font-semibold text-gray-600 mb-1">claude_desktop_config.json</p>
          <pre>{`{
  "mcpServers": {
    "knowledge-graph": {
      "type": "sse",
      "url": "${mcpUrl}/sse"
    }
  }
}`}</pre>
        </div>
      </section>

      {/* Quick Links */}
      <section className="bg-white rounded-lg border p-5 text-sm text-gray-600 space-y-2">
        <h2 className="font-semibold text-gray-900">Quick Links</h2>
        <ul className="list-disc list-inside space-y-1">
          <li>
            API Docs (Swagger):{" "}
            <a href={`${apiUrl}/docs`} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">
              {apiUrl}/docs
            </a>
          </li>
          <li>
            Agents API Docs:{" "}
            <a href={`${agentsUrl}/docs`} target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">
              {agentsUrl}/docs
            </a>
          </li>
          <li>
            Neo4j Browser:{" "}
            <a href="http://localhost:7474" target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">
              localhost:7474
            </a>
          </li>
          <li>
            RedisInsight:{" "}
            <a href="http://localhost:5540" target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">
              localhost:5540
            </a>
          </li>
        </ul>
      </section>
    </div>
  );
}
