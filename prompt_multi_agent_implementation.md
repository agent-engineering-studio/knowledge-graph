# Implementazione Sistema Multi-Agent per Knowledge Graph

## Contesto
Il progetto `knowledge-graph/` è un monorepo con:
- `knowledge-graph-api/`: FastAPI, pipeline ingest (extract→chunk→embed), Neo4j + Redis, Ollama (llama3 + nomic-embed-text), porta 8000
- `knowledge-graph-mcp/`: MCP server (FastMCP, stdio), 8 tool (kg_health, kg_query, kg_ingest, kg_delete_document, kg_list_documents, kg_search_nodes, kg_traverse, kg_cypher)
- `knowledge-graph-ui/`: Next.js 15

Il file `brainstorming_multi_agent_KG.md` descrive l'architettura target.
Devi implementare **Fase 1 — Foundation** del sistema multi-agent.

---

## Obiettivo — Fase 1 (Foundation)
Crea il modulo `knowledge-graph-agents/` che implementa:

### 1. Struttura directory da creare
```
knowledge-graph-agents/
├── agents/
│   ├── __init__.py
│   ├── orchestrator.py     # Router + Planner
│   ├── ingestion.py        # Ingestion Agent
│   ├── analyst.py          # Analyst Agent (vector + graph + hybrid)
│   ├── validator.py        # Validator Agent + KGQualityReport
│   ├── kgc.py              # KGC Agent (Knowledge Graph Completion)
│   ├── synthesis.py        # Synthesis Agent
│   └── monitor.py          # Monitor Agent
├── orchestration/
│   ├── __init__.py
│   ├── graph.py            # LangGraph StateGraph
│   ├── router.py           # Intent classification (8 intent types)
│   ├── state.py            # AgentState shared schema
│   └── planner.py          # Multi-step plan builder
├── tools/
│   ├── __init__.py
│   └── kg_tools.py         # Wrappa i tool MCP come LangChain @tool
├── memory/
│   ├── __init__.py
│   └── kg_memory.py        # Schema AgentRun nel KG + query memoria
├── api/
│   ├── __init__.py
│   └── agent_api.py        # FastAPI endpoint /agents/run, /agents/status
├── tests/
│   ├── __init__.py
│   └── test_agents.py
├── pyproject.toml
├── requirements.txt
└── .env.example
```

### 2. `orchestration/state.py`
Schema Pydantic condiviso tra tutti gli agenti:
```python
class Intent(str, Enum):
    INGEST = "ingest"
    QUERY = "query"
    ANALYZE = "analyze"
    SYNTHESIZE = "synthesize"
    VALIDATE = "validate"
    KGC = "kgc"
    MONITOR = "monitor"
    HEALTH = "health"

class AgentStep(BaseModel):
    agent: str
    action: str
    params: dict
    status: Literal["pending", "running", "done", "failed"]
    result: Optional[Any]
    error: Optional[str]

class AgentState(TypedDict):
    user_request: str
    intent: Optional[Intent]
    plan: List[AgentStep]
    current_step: int
    context: dict          # dati intermedi condivisi
    final_output: Optional[str]
    error: Optional[str]
    thread_id: str         # namespace KG
    run_id: str            # UUID del run corrente
```

### 3. `tools/kg_tools.py`
Wrappa le chiamate HTTP all'API (`http://localhost:8000`) come LangChain tools:
- `kg_health_tool` → GET /health
- `kg_query_tool(query, namespace, top_k)` → POST /query
- `kg_ingest_tool(file_path, thread_id)` → POST /ingest (multipart)
- `kg_list_documents_tool(namespace)` → GET /documents/{namespace}
- `kg_delete_document_tool(doc_id)` → DELETE /documents/{doc_id}
- `kg_search_nodes_tool(name, namespace)` → POST /graph/nodes/search
- `kg_traverse_tool(node_id, max_hops)` → POST /graph/traverse
- `kg_cypher_tool(query, namespace)` → POST /graph/cypher

Ogni tool usa `httpx.AsyncClient`, legge `KG_API_URL` da env (default `http://localhost:8000`).

### 4. `orchestration/router.py`
Classifica l'intent dell'utente (regex + keyword matching semplice per Fase 1):
```python
INTENT_PATTERNS = {
    Intent.INGEST: [r"carica|ingest|upload|importa"],
    Intent.QUERY: [r"cosa sai|dimmi|descrivi|spiega"],
    Intent.ANALYZE: [r"analizza|quante entità|conta|statistiche"],
    Intent.SYNTHESIZE: [r"report|genera|riassumi|sintesi"],
    Intent.VALIDATE: [r"valida|verifica qualità|check"],
    Intent.KGC: [r"relazioni mancanti|completa|gap"],
    Intent.MONITOR: [r"salute|funziona|status|health"],
}
```

### 5. `orchestration/graph.py`
LangGraph `StateGraph` con nodi per ogni agente e routing condizionale dall'orchestratore:
```python
workflow = StateGraph(AgentState)
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("ingestion", ingestion_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("validator", validator_node)
workflow.add_node("kgc", kgc_node)
workflow.add_node("synthesis", synthesis_node)
workflow.add_node("monitor", monitor_node)
workflow.set_entry_point("orchestrator")
workflow.add_conditional_edges("orchestrator", route_by_intent, {...})
workflow.add_edge("ingestion", "validator")  # post-ingest check automatico
```

### 6. Agenti

**`agents/orchestrator.py`**:
- Riceve `AgentState`, chiama `router.classify_intent(user_request)`
- Costruisce `plan` con steps ordinati
- Non esegue azioni dirette, solo routing

**`agents/ingestion.py`**:
- Esegue `kg_ingest_tool` con il file/URL ricevuto
- Verifica il risultato (chunk count, entity count)
- Aggiorna `context["ingestion_result"]`
- In caso di errore setta `step.status = "failed"` con dettaglio

**`agents/analyst.py`**:
- 3 sub-strategie: `vector_search`, `graph_traversal`, `hybrid`
- Output strutturato: `{"answer", "confidence", "sources", "graph_path"}`

**`agents/validator.py`**:
- Esegue query Cypher per: nodi orfani, nodi senza embedding
- Calcola `KGQualityReport` con `overall_health` (0.0→1.0)

**`agents/kgc.py`**:
- Trova nodi con degree basso via Cypher
- Propone candidati relazione tramite similarity vettoriale
- Output: `KGCProposal` con lista relazioni proposte + confidence

**`agents/synthesis.py`**:
- Esegue query vector + graph, costruisce prompt per Ollama
- Genera Markdown output, opzionale auto-ingest del report

**`agents/monitor.py`**:
- Chiama `kg_health_tool` + `validator` quick check
- Genera summary stato sistema

### 7. `memory/kg_memory.py`
Schema `AgentRunRecord` (Pydantic) + funzione `save_agent_run` che scrive nel grafo Neo4j tramite API.

### 8. `api/agent_api.py`
FastAPI app separata (porta 8001):
```
POST /agents/run       body: {"request": str, "thread_id": str}
GET  /agents/run/{id}  response: AgentRunRecord
GET  /agents/health    response: {"status": "ok", "kg_api": bool}
```

### 9. `requirements.txt`
```
langgraph>=0.2.0
langchain>=0.3.0
langchain-community>=0.3.0
httpx>=0.27.0
fastapi>=0.115.0
uvicorn>=0.30.0
pydantic>=2.0.0
python-dotenv>=1.0.0
```

### 10. `tests/test_agents.py`
Test con `pytest` e mock di `httpx`:
- `test_intent_classification`
- `test_ingestion_agent`
- `test_analyst_agent_vector`
- `test_validator_agent`
- `test_orchestrator_plan`
- `test_full_pipeline_ingest_analyze`

---

## Vincoli importanti
1. **Nessuna modifica** a `knowledge-graph-api/` o `knowledge-graph-mcp/`
2. Il `thread_id` (namespace) deve essere passato su ogni tool call
3. Tutti gli agenti sono `async`
4. `KG_API_URL=http://localhost:8000` come default da `.env`
5. LLM: **Ollama** (`http://localhost:11434`, modello `llama3`) — non OpenAI
6. Cypher degli agenti: **read-only** tramite guardrail esistente

---

## Verifica finale
```bash
cd knowledge-graph-agents
pip install -r requirements.txt
python -m uvicorn api.agent_api:app --port 8001
curl -X POST http://localhost:8001/agents/run \
  -H "Content-Type: application/json" \
  -d '{"request": "cosa sai su Hevolus?", "thread_id": "default"}'
```
Risposta attesa: `{"run_id": "...", "output": "...", "plan": [...], "quality": {...}}`
