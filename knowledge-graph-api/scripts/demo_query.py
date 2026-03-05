"""Interactive demo for the RAG query pipeline."""

from __future__ import annotations

import asyncio

from query.rag_pipeline import GraphRAGPipeline, QueryOptions
from utils.logger import logger

DEMO_QUERIES = [
    "What is Redis and how is it used?",
    "How does Neo4j store data compared to traditional databases?",
    "What embedding models does Ollama support for RAG?",
]


async def main() -> None:
    """Run an interactive demo of the RAG pipeline."""
    pipeline = GraphRAGPipeline()
    thread_id = "seed"

    print("\n=== Knowledge Graph RAG Demo ===\n")
    print("Choose a query:\n")
    for i, q in enumerate(DEMO_QUERIES, 1):
        print(f"  {i}. {q}")
    print(f"  {len(DEMO_QUERIES) + 1}. Enter custom query")
    print()

    choice = input("Select (number): ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(DEMO_QUERIES):
            user_query = DEMO_QUERIES[idx]
        else:
            user_query = input("Enter your query: ").strip()
    except ValueError:
        user_query = input("Enter your query: ").strip()

    if not user_query:
        print("No query provided. Exiting.")
        return

    print(f"\nQuery: {user_query}\n")
    print("Processing...\n")

    result = await pipeline.query(
        user_query=user_query,
        thread_id=thread_id,
        options=QueryOptions(top_k=5, max_hops=2),
    )

    print(f"Intent: {result.query_intent}")
    print(f"Processing time: {result.processing_time_ms:.1f} ms\n")
    print("--- Answer ---")
    print(result.answer)
    print("\n--- Sources ---")
    for src in result.sources:
        print(f"  [{src.doc_id}] {src.text_preview[:80]}...")
    print(f"\n--- Nodes used: {len(result.nodes_used)} | Edges used: {len(result.edges_used)} ---")


if __name__ == "__main__":
    asyncio.run(main())
