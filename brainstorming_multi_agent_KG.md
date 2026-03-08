# Brainstorming — Sistema Multi-Agent per Knowledge Graph
**Progetto**: Knowledge Graph Lab — Hevolus Srl
**Data**: Marzo 2026
**Riferimento libro**: _Knowledge Graph: dalla Teoria alla Pratica v2_
**Autore**: Giuseppe Zileni

---

## 🗺️ Contesto: Dove siamo oggi

### Stack attuale

```
┌─────────────────────────────────────────────────────┐
│                   CLIENT / LLM HOST                 │
│         (Claude Desktop, VS Code, custom app)       │
└──────────────────────┬──────────────────────────────┘
                       │ MCP Protocol
┌──────────────────────▼──────────────────────────────┐
│              knowledge-graph-mcp                    │
│  Tools: kg_query · kg_ingest · kg_cypher            │
│         kg_traverse · kg_search_nodes               │
│         kg_list_documents · kg_delete_document      │
│         kg_health                                   │
└──────────────────────┬──────────────────────────────┘
                       │ HTTP REST
┌──────────────────────▼──────────────────────────────┐
│              knowledge-graph-api (FastAPI)           │
│  Pipeline: extract → chunk → embed → deduplica      │
│  Storage:  Neo4j (graph) + Redis (vector)           │
│  Inference: Ollama (LLM + embeddings)               │
│  Query:    RAG ibrido (vector + graph traversal)    │
└─────────────────────────────────────────────────────┘
```

### Capacità esistenti (già funzionanti)

| Capacità | Tool MCP | Endpoint API |
|----------|----------|--------------|
| Ingestion documento (PDF/DOCX/TXT) | `kg_ingest` | `POST /ingest` |
| Query RAG ibrida | `kg_query` | `POST /query` |
| Traversal grafo | `kg_traverse` | interno |
| Cypher read-only | `kg_cypher` | interno |
| Ricerca nodo per nome | `kg_search_nodes` | interno |
| Gestione documenti | `kg_list_documents` / `kg_delete_document` | vari |

### Limiti del sistema attuale

- **Nessuna orchestrazione**: un singolo LLM decide tutto, senza specializzazione
- **Nessuna pianificazione**: query complesse multi-step non sono gestite
- **Nessun feedback loop**: errori di estrazione non vengono corretti automaticamente
- **Nessuna proattività**: il sistema risponde solo su richiesta, non monitora
- **Nessun ragionamento sul grafo**: il Cypher è usato passivamente, non per inferenza attiva
- **Nessuna collaborazione**: un solo "agente" per tutto

---

## 🧠 Visione: Sistema Multi-Agent

### Principio Guida

> Il Knowledge Graph diventa sia **oggetto di lavoro** degli agenti (ci scrivono e ci leggono) che **memoria condivisa** (lo stato globale del sistema è il grafo stesso).

Ogni agente è specializzato su una responsabilità precisa. Un orchestratore centrale coordina, delega, e aggrega i risultati.

### Pattern architetturale: Supervisor + Specialists

```
                    ┌──────────────────┐
                    │   ORCHESTRATOR   │
                    │  (Router/Planner)│
                    └────────┬─────────┘
                             │  delega per intent
          ┌──────────────────┼──────────────────┐
          │                  │                  │
   ┌──────▼──────┐   ┌───────▼──────┐   ┌──────▼──────┐
   │  INGESTION  │   │   ANALYST    │   │  SYNTHESIS  │
   │   AGENT     │   │    AGENT     │   │    AGENT    │
   └──────┬──────┘   └───────┬──────┘   └──────┬──────┘
          │                  │                  │
   ┌──────▼──────┐   ┌───────▼──────┐   ┌──────▼──────┐
   │  VALIDATOR  │   │     KGC      │   │  MONITOR    │
   │   AGENT     │   │    AGENT     │   │    AGENT    │
   └─────────────┘   └──────────────┘   └─────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │ tool calls
                    ┌────────▼─────────┐
                    │   MCP TOOL LAYER │
                    │  (kg_* tools)    │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ knowledge-graph  │
                    │      api         │
                    │ Neo4j + Redis    │
                    └──────────────────┘
```

---

## 🤖 Catalogo degli Agenti

---

### 1. ORCHESTRATOR AGENT (Router + Planner)

**Responsabilità**: riceve la richiesta utente, classifica l'intent, costruisce un piano di esecuzione, delega agli agenti specializzati, aggrega i risultati.

**Intent classificati** (esempi):
| Intent | Agente delegato |
|--------|----------------|
| "carica questo documento" | Ingestion Agent |
| "cosa sai su X?" | Analyst Agent |
| "quante entità ci sono di tipo Y?" | Analyst Agent (cypher) |
| "genera un report su..." | Synthesis Agent |
| "il sistema funziona?" | Monitor Agent |
| "trova relazioni mancanti" | KGC Agent |
| "questo documento è valido?" | Validator Agent |

**Pattern**: usa `kg_query` per classificazione semantica dell'intent (il KG stesso aiuta a disambiguare le richieste).

**Implementazione**:
```python
class OrchestratorAgent:
    tools = [kg_query, kg_health]  # solo tool di routing/diagnostica
    system_prompt = """
    Sei un orchestratore di un sistema multi-agent su Knowledge Graph.
    Analizza la richiesta, identifica l'intent, costruisci un piano step-by-step,
    delega al sotto-agente corretto. Non eseguire azioni direttamente.
    Piano: [intent] → [agente] → [parametri] → [attesa risultato] → [aggregazione]
    """
```

**Output**: `AgentPlan { steps: [...], assigned_agents: [...], expected_outputs: [...] }`

---

### 2. INGESTION AGENT

**Responsabilità**: gestisce l'intero ciclo di vita di un documento nel KG — dal file grezzo all'entità strutturata nel grafo.

**Sub-task gestiti**:
- Riceve path o URL del documento
- Chiama `kg_ingest` con il thread_id corretto
- Verifica il risultato (conteggio chunk, entità, relazioni)
- Notifica l'Orchestrator del completamento
- In caso di errore: ritenta o delega al Validator Agent

**Strumenti usati**:
- `kg_ingest` (principale)
- `kg_list_documents` (dedup check pre-ingestion)
- `kg_health` (check prima di avviare)

**Pattern interessante — Batch Ingestion Planner**:
```
Ingestion Agent riceve: ["doc1.pdf", "doc2.docx", "doc3.txt"]
→ prioritizza per dimensione o tipo
→ esegue in parallelo con controllo concorrenza
→ aggrega statistiche finali
→ report: "3 documenti ingestiti, 847 chunk, 234 entità, 89 relazioni"
```

**Estensione possibile**: Ingestion da URL (scraping), da email attachment, da SharePoint.

---

### 3. ANALYST AGENT (Graph + Vector)

**Responsabilità**: risponde a domande fattuali sul grafo, combina ricerca vettoriale e traversal del grafo, produce risposte con fonti tracciabili.

**Sub-agenti specializzati**:

#### 3a. Vector Search Sub-Agent
- Usa `kg_query` per ricerca semantica pura
- Ideale per: "trova documenti simili a...", "qual è il concetto più rilevante per X?"

#### 3b. Graph Traversal Sub-Agent
- Usa `kg_traverse` + `kg_cypher` per navigazione strutturale
- Ideale per: "come è collegato X a Y?", "trova tutti i nodi a 2 hop da Z"

#### 3c. Hybrid Reasoning Sub-Agent
- Combina entrambi: prima ricerca vettoriale, poi espande con traversal
- Ideale per: domande complesse che richiedono sia semantica che struttura

**Esempio di piano multi-step**:
```
Domanda: "Quali sono le competenze di Hevolus in AR enterprise?"
Step 1: kg_search_nodes("Hevolus") → trova nodo principale
Step 2: kg_traverse(hevolus_id, max_hops=3) → mappa di competenze
Step 3: kg_query("AR enterprise capabilities Hevolus") → contesto semantico
Step 4: MERGE(grafo + vettori) → risposta sintetizzata con fonti
```

**Output strutturato**:
```json
{
  "answer": "...",
  "confidence": 0.87,
  "sources": ["doc_id_1", "doc_id_2"],
  "graph_path": ["Hevolus → COMPETENZA_IN → AR → USATO_IN → Enterprise"],
  "vector_chunks": [...]
}
```

---

### 4. KGC AGENT (Knowledge Graph Completion)

**Responsabilità**: identifica relazioni mancanti nel grafo, propone nuovi link tra entità, usa pattern di completamento basati su LLM.

> Questo agente implementa direttamente il Capitolo 13 del libro v2 ("Knowledge Graph Completion").

**Approcci implementabili**:

#### 4a. Rule-based Completion
```cypher
-- Trova entità simili senza relazione diretta
MATCH (a:KGNode)-[:RELATED_TO]->(b:KGNode)
MATCH (b)-[:RELATED_TO]->(c:KGNode)
WHERE NOT (a)-[:RELATED_TO]->(c)
RETURN a, c, count(*) as path_count
ORDER BY path_count DESC
```

#### 4b. LLM-based Link Prediction
- Prende coppie di nodi non collegati
- Invia al LLM (via Ollama): "Esiste una relazione semantica tra X e Y? Se sì, quale?"
- Propone il link con confidence score

#### 4c. Embedding Similarity Completion
- Usa Redis per trovare nodi con embedding simile ma senza archi
- Propone relazioni dove la similarità vettoriale è alta ma il grafo è "sparse"

**Workflow KGC Agent**:
```
1. Esegui cypher: trova nodi con pochi archi (degree < threshold)
2. Per ogni nodo isolato: cerca vicini vettoriali in Redis
3. Chiedi al LLM di valutare la relazione proposta
4. Se confidence > 0.8: proponi l'aggiornamento
5. Manda proposta all'Orchestrator per approvazione (human-in-the-loop opzionale)
```

**Output**: `KGCProposal { new_relations: [...], confidence_scores: [...], evidence: [...] }`

---

### 5. VALIDATOR AGENT

**Responsabilità**: verifica la qualità del grafo e dei documenti ingestiti — coerenza, completezza, duplicati, anomalie.

**Check implementati**:

| Check | Query Cypher | Azione |
|-------|-------------|--------|
| Nodi orfani (no relazioni) | `MATCH (n) WHERE NOT (n)--() RETURN n` | Flag per KGC |
| Entità duplicate | embedding similarity > 0.95 tra nodi diversi | Merge proposto |
| Relazioni contradittorie | pattern inversi nella stessa coppia | Alert |
| Namespace overflow | thread_id con troppi documenti | Warning |
| Embedding mancanti | nodi senza vettore | Ri-embedding |

**Pattern: Quality Score del KG**
```python
class KGQualityReport:
    orphan_nodes: int
    duplicate_candidates: list
    avg_degree: float
    coverage_score: float  # % entità con embedding
    consistency_score: float  # % relazioni senza contraddizioni
    overall_health: float  # 0.0 → 1.0
```

**Trigger**: può essere lanciato:
- Dopo ogni ingestion (post-hook)
- Su schedule (ogni notte)
- Su richiesta dell'Orchestrator

---

### 6. SYNTHESIS AGENT

**Responsabilità**: genera report, sintesi e documenti strutturati combinando informazioni da più parti del grafo.

**Casi d'uso**:
- "Genera un executive summary su [topic]"
- "Crea un documento di onboarding per [team] basato sulle SOP del KG"
- "Confronta [entità A] e [entità B] su tutti gli assi disponibili"
- "Estrai una timeline degli eventi per [progetto]"

**Pipeline Synthesis Agent**:
```
1. Orchestrator fornisce: topic + namespace + formato output
2. Synthesis Agent esegue query multiple (vettoriale + graph)
3. Raccoglie chunks, entità, relazioni rilevanti
4. Costruisce prompt strutturato per LLM con tutto il contesto
5. Genera output formattato (Markdown / JSON / HTML)
6. Opzionale: salva il report nel KG come nuovo documento
```

**Caratteristica chiave**: il Synthesis Agent può **auto-ingestire** il report generato — così il KG cresce con la propria conoscenza sintetizzata.

---

### 7. MONITOR AGENT

**Responsabilità**: supervisiona la salute del sistema, le performance, la qualità delle risposte, e genera alert.

**Metriche monitorate**:

| Metrica | Fonte | Alert se |
|---------|-------|----------|
| Latenza query RAG | log API | > 5s |
| Tasso di risposta "non so" | LLM output | > 20% |
| Crescita nodi/archi | Neo4j stats | anomalie |
| Redis memory usage | Redis INFO | > 80% |
| Ollama availability | kg_health | down |
| Quality Score KG | Validator Agent | < 0.7 |

**Pattern: Scheduled Monitoring**
```python
# Ogni ora
async def monitor_cycle():
    health = await kg_health()
    quality = await validator_agent.run_quick_check()
    perf = await query_agent.run_benchmark_queries()

    if quality.overall_health < 0.7:
        await orchestrator.trigger(KGCAgent)

    if health.neo4j_status == "down":
        await send_alert(channel="ops")
```

---

## 🔗 Interazioni tra Agenti — Scenari

### Scenario 1: "Ingesta e analizza questo documento"

```
User → Orchestrator
  Orchestrator: intent = INGEST + ANALYZE

  Step 1: delega a Ingestion Agent
    Ingestion Agent → kg_ingest(file, thread_id)
    Ingestion Agent → report(chunks=45, entities=12, relations=8)

  Step 2: delega a Validator Agent (post-ingest check)
    Validator Agent → quality_check(namespace)
    Validator Agent → found 2 duplicate candidates

  Step 3: delega ad Analyst Agent
    Analyst Agent → kg_query("topic del documento")
    Analyst Agent → synthesis delle entità principali

  Step 4: Orchestrator aggrega
    Output: "Documento ingestito. 12 nuove entità.
             2 possibili duplicati da verificare.
             Concetti principali: [X, Y, Z]"
```

### Scenario 2: "Cosa manca nel nostro grafo su [topic]?"

```
User → Orchestrator
  Orchestrator: intent = KGC + GAP_ANALYSIS

  Step 1: Analyst Agent mappa entità esistenti su topic
  Step 2: KGC Agent identifica relazioni mancanti
  Step 3: KGC Agent propone 5 nuovi link con confidence
  Step 4: Synthesis Agent genera report "Gap Analysis"
  Step 5: Orchestrator presenta proposta all'utente
```

### Scenario 3: "Report settimanale automatico"

```
Monitor Agent (trigger: ogni lunedì 09:00)
  → Chiama Validator Agent per quality score
  → Chiama Analyst Agent per "novità settimana"
  → Chiama KGC Agent per "opportunità di completamento"
  → Chiama Synthesis Agent per generare report PDF
  → Salva report nel KG + invia summary all'utente
```

---

## 🏗️ Architettura Tecnica Proposta

### Opzione A — LangGraph (Python-native)

```python
# grafo degli agenti come StateGraph
from langgraph.graph import StateGraph

workflow = StateGraph(AgentState)
workflow.add_node("orchestrator", orchestrator_agent)
workflow.add_node("ingestion", ingestion_agent)
workflow.add_node("analyst", analyst_agent)
workflow.add_node("kgc", kgc_agent)
workflow.add_node("validator", validator_agent)
workflow.add_node("synthesis", synthesis_agent)

# routing condizionale
workflow.add_conditional_edges("orchestrator", route_by_intent)
```

**Pro**: Python nativo, ottimo per graph-based orchestration, integrazione diretta con MCP tools.
**Contro**: setup più complesso, curva di apprendimento.

### Opzione B — Microsoft Semantic Kernel (Agent Framework)

```python
# Semantic Kernel con plugin MCP
kernel = Kernel()
kg_plugin = KernelPlugin.from_mcp_server("knowledge-graph-mcp")
kernel.add_plugin(kg_plugin, "KnowledgeGraph")

# Orchestrator come Planner
planner = SequentialPlanner(kernel)
plan = await planner.create_plan_async("ingesta e analizza doc.pdf")
result = await plan.invoke_async()
```

**Pro**: allineato con Microsoft Agent Framework (libro), ottimo supporto planner.
**Contro**: dipendenza da Azure/OpenAI per alcuni features.

### Opzione C — AutoGen (Microsoft Research)

```python
# AutoGen multi-agent conversazione
from autogen import AssistantAgent, UserProxyAgent, GroupChat

orchestrator = AssistantAgent("orchestrator", ...)
ingestion = AssistantAgent("ingestion_agent", tools=[kg_ingest])
analyst = AssistantAgent("analyst_agent", tools=[kg_query, kg_traverse])

group_chat = GroupChat([orchestrator, ingestion, analyst], ...)
```

**Pro**: pattern conversazionale naturale, facilmente estendibile.
**Contro**: overhead di comunicazione, debugging più complesso.

### ✅ Raccomandazione

> **Opzione A (LangGraph) come core** + **tool layer MCP esistente** + **Semantic Kernel per planning complesso**.
> I tool MCP diventano i `@tool` di ogni agente — zero duplicazione di codice.

---

## 📦 Struttura Repository Proposta

```
knowledge-graph-lab/
├── knowledge-graph-api/        # ✅ ESISTENTE — FastAPI + pipeline
├── knowledge-graph-mcp/        # ✅ ESISTENTE — MCP tool layer
├── knowledge-graph-agents/     # 🆕 NUOVO — sistema multi-agent
│   ├── agents/
│   │   ├── orchestrator.py     # Router + Planner
│   │   ├── ingestion.py        # Ingestion Agent
│   │   ├── analyst.py          # Analyst Agent (vector + graph)
│   │   ├── kgc.py              # KGC Agent
│   │   ├── validator.py        # Validator Agent
│   │   ├── synthesis.py        # Synthesis Agent
│   │   └── monitor.py          # Monitor Agent
│   ├── orchestration/
│   │   ├── graph.py            # LangGraph StateGraph definition
│   │   ├── router.py           # Intent classification
│   │   ├── state.py            # AgentState shared schema
│   │   └── planner.py          # Multi-step plan builder
│   ├── tools/
│   │   ├── kg_tools.py         # Wrapper MCP tools → LangChain tools
│   │   └── internal_tools.py   # Tool interni (non MCP)
│   ├── memory/
│   │   └── kg_memory.py        # KG come memoria persistente agenti
│   ├── api/
│   │   └── agent_api.py        # FastAPI endpoint per sistema multi-agent
│   ├── scheduler/
│   │   └── cron.py             # Monitor Agent scheduling
│   └── tests/
│       └── test_agents.py
└── docker-compose.agents.yml   # 🆕 estende docker-compose.yml
```

---

## 🧩 Il Knowledge Graph come Memoria degli Agenti

**Idea chiave**: invece di usare memoria in-process (volatile), ogni agente scrive il proprio stato e i propri ragionamenti nel KG stesso.

```
Struttura memoria nel KG:

(AgentRun) -[EXECUTED_BY]→ (Agent)
(AgentRun) -[PRODUCED]→ (KGNode | KGRelation | Report)
(AgentRun) -[USED_TOOL]→ (Tool)
(AgentRun) -[HAD_INTENT]→ (Intent)

Query "cosa ha fatto il KGC Agent la settimana scorsa?":
MATCH (r:AgentRun)-[:EXECUTED_BY]->(a:Agent {name: "KGCAgent"})
WHERE r.created_at > datetime() - duration({days: 7})
RETURN r.summary, r.output_count
```

**Vantaggi**:
- Audit trail completo e navigabile
- Gli agenti possono imparare dai run precedenti
- Il KG diventa auto-descrittivo (sa cosa è stato fatto su se stesso)
- Debugging tramite Cypher + Neo4j Browser

---

## 🚀 Roadmap di Implementazione

### Fase 1 — Foundation (2 settimane)
- [ ] Wrapper `kg_tools.py`: adatta i tool MCP come LangChain tools
- [ ] `AgentState` schema condiviso
- [ ] Orchestrator base (routing per intent semplice)
- [ ] Ingestion Agent (usa `kg_ingest` esistente)
- [ ] Test integration con MCP server esistente

### Fase 2 — Intelligence (3 settimane)
- [ ] Analyst Agent con sub-agent vector/graph/hybrid
- [ ] Validator Agent con quality score
- [ ] KGC Agent (rule-based + LLM-based)
- [ ] Memoria agenti nel KG (schema AgentRun)

### Fase 3 — Autonomy (2 settimane)
- [ ] Synthesis Agent con auto-ingestione report
- [ ] Monitor Agent con scheduling
- [ ] Agent API (FastAPI wrapper del sistema multi-agent)
- [ ] Docker Compose esteso

### Fase 4 — Production (1 settimana)
- [ ] Human-in-the-loop per KGC proposals
- [ ] Tracing distribuito (OpenTelemetry)
- [ ] Dashboard qualità KG
- [ ] Test di orchestrazione end-to-end

---

## 💡 Idee Avanzate / Future

### 1. Self-Improving KG
Il KGC Agent + Synthesis Agent in loop: ogni nuovo documento arricchisce il grafo, il KGC propone nuovi link, il Synthesis Agent genera insight, che vengono reingestiti. Il grafo cresce in qualità senza intervento umano.

### 2. Agente Specializzato per Dominio
Un agente "domain expert" per ciascun namespace: es. `TechAgent` per namespace tecnico, `SalesAgent` per namespace commerciale. Ognuno ha prompt e tool specializzati per il proprio dominio.

### 3. Multi-tenant Agent Orchestration
Ogni `thread_id` (namespace) ha il proprio set di agenti configurabili. Un utente di Hevolus vede solo il suo namespace, con agenti calibrati sui suoi documenti.

### 4. Conversational Memory con Continuità
Il KG traccia la storia delle conversazioni utente (`ConversationNode`). Il prossimo turno beneficia del contesto di tutti i turni precedenti, navigando il grafo della conversazione.

### 5. Agent Tool Marketplace
Nuovi tool vengono registrati come nodi nel KG (`ToolNode`). L'Orchestrator interroga il KG per scoprire dinamicamente quali tool sono disponibili — no hard-coding.

---

## ⚠️ Rischi e Mitigazioni

| Rischio | Probabilità | Impatto | Mitigazione |
|---------|------------|---------|-------------|
| Loop infiniti tra agenti | Media | Alto | Timeout + max_iterations per piano |
| KGC propone relazioni errate | Alta | Medio | Human-in-the-loop + confidence threshold |
| Overhead latenza multi-step | Alta | Medio | Caching intermedi + streaming progressivo |
| Stato inconsistente tra agenti | Bassa | Alto | AgentState atomico + transazioni Neo4j |
| LLM (Ollama) bottleneck | Alta | Alto | Queue + retry + fallback a risposta parziale |
| Crescita incontrollata grafo | Media | Medio | Validator Agent + policy di pulizia |

---

## 📊 KPI di Successo del Sistema Multi-Agent

| KPI | Baseline (oggi) | Target (post v1) |
|-----|----------------|-----------------|
| Latenza query complessa | ~3-5s | < 8s (multi-step accettabile) |
| Copertura entità collegate | ~60% | > 85% |
| Autonomia ingestion | 0% (manuale) | 80% (auto-trigger) |
| Quality Score KG | non misurato | > 0.80 |
| Relazioni KGC proposte/settimana | 0 | > 50 (di cui 80% accettate) |
| Report auto-generati/settimana | 0 | ≥ 1 (Monitor Agent) |

---

## 📌 Decisioni da Prendere

1. **Framework orchestrazione**: LangGraph vs AutoGen vs Semantic Kernel?
2. **Deployment agenti**: stessa macchina API o microservizi separati?
3. **KGC automatico o human-in-the-loop** per i nuovi link proposti?
4. **Scheduling Monitor Agent**: cron interno o job scheduler esterno (Celery, APScheduler)?
5. **LLM per agenti**: stesso Ollama dell'API o modello più potente (es. GPT-4o) per reasoning?
6. **Interfaccia utente agenti**: via MCP (Claude Desktop) o nuova Agent API REST?

---

*Fine documento di brainstorming — v1.0 — Marzo 2026*
