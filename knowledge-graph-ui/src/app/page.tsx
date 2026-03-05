import Link from "next/link";
import { HealthStatus } from "@/components/HealthStatus";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Knowledge Graph Lab</h1>
        <p className="text-gray-600 mt-1">
          RAG pipeline with Neo4j graph DB, Redis vector store, and Ollama LLM inference.
        </p>
      </div>

      <section className="bg-white rounded-lg border p-5">
        <h2 className="font-semibold mb-3">Service Health</h2>
        <HealthStatus />
      </section>

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
      </section>

      <section className="bg-white rounded-lg border p-5 text-sm text-gray-600 space-y-2">
        <h2 className="font-semibold text-gray-900">Quick Links</h2>
        <ul className="list-disc list-inside space-y-1">
          <li>
            API Docs (Swagger):{" "}
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/docs`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 underline"
            >
              /docs
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
            <a href="http://localhost:8001" target="_blank" rel="noopener noreferrer" className="text-blue-600 underline">
              localhost:8001
            </a>
          </li>
        </ul>
      </section>
    </div>
  );
}
