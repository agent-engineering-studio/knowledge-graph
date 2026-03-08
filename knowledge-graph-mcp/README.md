# knowledge-graph-mcp

**Model Context Protocol (MCP)** server for the **Knowledge Graph Lab** project.
Exposes the FastAPI backend as MCP tools for Claude Desktop, Claude Code and any other MCP-compatible client.

> Full project documentation in the [root README](../README.md).

---

## Table of contents

- [What is MCP](#what-is-mcp)
- [Stack](#stack)
- [Prerequisites](#prerequisites)
- [Setup](#setup)
- [Configuration](#configuration)
- [Running](#running)
- [Exposed tools](#exposed-tools)
- [Claude integration](#claude-integration)
- [Testing](#testing)
- [Docker](#docker)
- [Directory structure](#directory-structure)

---

## What is MCP

The [Model Context Protocol](https://modelcontextprotocol.io) is an open standard that allows LLMs to call external tools in a structured way.
This server exposes 8 tools that wrap the backend HTTP API — the model can run RAG queries, ingest documents and explore the graph directly from a chat session.

---

## Stack

| Component | Technology |
| --- | --- |
| MCP framework | FastMCP (mcp[cli] 1.2+) |
| HTTP client | httpx 0.27+ |
| Data models | Pydantic v2 + pydantic-settings |
| Transport | stdio (Claude Desktop / Code) |
| Testing | pytest + pytest-asyncio |

---

## Prerequisites

- Python 3.11+
- API backend reachable (default `http://localhost:8000`)

Start the API (from the repo root):

```bash
make up-infra && make run
```

---

## Setup

```bash
cd knowledge-graph-mcp

# Install in editable mode (with dependencies)
pip install -e .

# Or from the repo root
make mcp-install
```

---

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `KG_API_URL` | `http://localhost:8000` | Base URL of the FastAPI backend |

```bash
export KG_API_URL=http://localhost:8000
```

---

## Running

```bash
# Direct launch (stdio transport)
python -m kg_mcp.server

# With MCP Inspector (interactive browser-based debugger)
npx @modelcontextprotocol/inspector python -m kg_mcp.server

# Or from the repo root
make mcp-inspector
```

---

## Exposed tools

| Tool | Description |
| --- | --- |
| `kg_health` | Health check of the API (Neo4j, Redis, Ollama) |
| `kg_query` | Hybrid RAG query (vector + graph) |
| `kg_ingest` | Ingest a document (PDF, DOCX, TXT) |
| `kg_delete_document` | Delete a document by ID |
| `kg_list_documents` | List documents in a namespace |
| `kg_search_nodes` | Search nodes by name and namespace |
| `kg_traverse` | Traverse node neighbours (max_hops) |
| `kg_cypher` | Execute a read-only Cypher query |

> `kg_cypher` includes a regex guardrail that blocks write operations (`CREATE`, `MERGE`, `DELETE`, `SET`, `REMOVE`, `DROP`).

### Example — Query from Claude

Once configured, Claude can invoke tools automatically:

```text
User:  What do you know about Neo4j in namespace "project1"?
Claude: [calls kg_query with query="Neo4j" thread_id="project1"]
        Neo4j is a graph database focused on nodes and relationships...
```

---

## Claude integration

### Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "knowledge-graph": {
      "command": "python",
      "args": ["-m", "kg_mcp.server"],
      "env": {
        "KG_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

### Claude Code (VS Code)

The server is already configured in `.vscode/launch.json` as **"MCP: Server (debugpy)"**.

To add it to `claude_code_config.json`:

```json
{
  "mcpServers": {
    "knowledge-graph": {
      "command": "python",
      "args": ["-m", "kg_mcp.server"],
      "cwd": "knowledge-graph-mcp/src",
      "env": { "KG_API_URL": "http://localhost:8000" }
    }
  }
}
```

---

## Testing

```bash
cd knowledge-graph-mcp

pytest tests/ -v

# Or from the repo root
make mcp-test
```

Tests mock the HTTP client — no live services needed.
8 tests cover all tools and error cases.

---

## Docker

```bash
# Start via compose (prod profile)
docker compose --profile prod up mcp -d

# Follow logs
docker compose logs -f mcp
```

> In Docker the MCP server uses SSE transport on port 8080.
> For local use with Claude Desktop/Code always run `python -m kg_mcp.server` (stdio).

---

## Directory structure

```text
knowledge-graph-mcp/
├── src/kg_mcp/
│   ├── server.py               # MCP server (FastMCP) + tool definitions
│   ├── api_client.py           # HTTP client to knowledge-graph-api
│   ├── tools.py                # Tool implementations
│   └── config.py               # KG_API_URL + settings
├── tests/
│   └── test_tools.py           # Unit tests with mocked API client
├── Dockerfile
└── pyproject.toml
```
