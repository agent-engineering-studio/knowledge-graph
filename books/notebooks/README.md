# 📓 Knowledge Graph — Notebook di Test

Jupyter Lab notebooks per testare le query e i pattern del libro **Knowledge Graph: dalla Teoria alla Pratica**.

## Quick Start (3 minuti)

```bash
# 1. Avvia lo stack infrastruttura (Neo4j + Redis + RedisInsight)
docker compose --profile dev up -d

# 2. Avvia Jupyter Lab
docker compose -f notebooks/docker-compose.notebooks.yml up -d

# 3. Apri nel browser
open http://localhost:8888/?token=kglab
```

> **Nota**: Ollama deve essere in esecuzione sull'host (`ollama serve`) oppure avviato con profilo `cpu`/`gpu`.

## Notebook disponibili

| # | Notebook | Contenuto | Capitolo libro |
|---|----------|-----------|----------------|
| 1 | `nb1_neo4j_graph_queries.ipynb` | Query Cypher: seed, ricerca semantica, navigazione relazionale, skill matching | Cap. Il Valore del KG in Azienda |
| 2 | `nb2_redis_vector_search.ipynb` | Embedding, indice HNSW, ricerca KNN, filtri per intent | Cap. Vector Store e Ricerca Semantica |
| 3 | `nb3_rag_pipeline.ipynb` | Pipeline RAG completa: vector + graph + LLM grounded | Cap. Pipeline RAG con KG |
| 4 | `nb4_entity_extraction.ipynb` | Estrazione entità/relazioni da testo con Ollama LLM | Cap. Estrazione Entità con LLM |
| 5 | `nb5_data_governance.ipynb` | Data lineage, PII detection, report GDPR Art. 30 | Cap. Compliance e Data Governance |

## Prerequisiti

| Servizio | URL | Note |
|----------|-----|------|
| Neo4j Browser | http://localhost:7474 | `neo4j` / password da `.env` |
| Redis Insight | http://localhost:5540 | Aggiungi connessione: `kg-redis:6379` |
| Ollama API | http://localhost:11434 | Modelli: `nomic-embed-text`, `qwen2.5:14b` |
| Jupyter Lab | http://localhost:8888 | Token: `kglab` |

## Ordine consigliato

1. **Notebook 1** — Popola il grafo Neo4j con dati di esempio e testa le query base
2. **Notebook 2** — Crea l'indice vettoriale Redis e testa la ricerca semantica
3. **Notebook 4** — Estrai entità da testo libero con Ollama
4. **Notebook 3** — Esegui la pipeline RAG completa (richiede nb1 + nb2 completati)
5. **Notebook 5** — Costruisci e interroga il modello di governance

## Esecuzione locale (senza Docker per Jupyter)

```bash
# Installa dipendenze
pip install jupyterlab neo4j redis httpx numpy pandas networkx matplotlib

# Avvia (connessione a Neo4j/Redis locali)
cd notebooks
jupyter lab
```

In questo caso, modifica le variabili d'ambiente nei notebook:
- `NEO4J_URI=bolt://localhost:7687`
- `REDIS_URL=redis://localhost:6379`
- `OLLAMA_BASE_URL=http://localhost:11434`

## Troubleshooting

| Problema | Soluzione |
|----------|----------|
| `ConnectionRefused` su Neo4j | Verifica: `docker ps \| grep neo4j` e che il profilo `dev` sia attivo |
| `ConnectionRefused` su Redis | Verifica: `docker ps \| grep redis` |
| Embedding timeout | Ollama deve avere il modello scaricato: `ollama pull nomic-embed-text` |
| Notebook non trova la rete Docker | Assicurati che `kg_network` esista: `docker network ls \| grep kg` |
