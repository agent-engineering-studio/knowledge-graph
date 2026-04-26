# Docker + GitHub Actions CI/CD Design

**Date:** 2026-04-26  
**Project:** knowledge-graph  
**Scope:** Build e pubblicazione di 4 immagini Docker su GitHub Container Registry (ghcr.io)

---

## Obiettivo

Automatizzare la build e il push delle immagini Docker per i 4 moduli principali del progetto (`api`, `ui`, `mcp`, `agents`) su GitHub Container Registry ad ogni push su `main`, preceduto da un passaggio obbligatorio di lint + test.

---

## Immagini target

| Modulo | Dockerfile | Immagine pubblicata |
|--------|-----------|---------------------|
| API (FastAPI) | `knowledge-graph-api/Dockerfile` | `ghcr.io/<owner>/kg-api:latest` |
| UI (Next.js) | `knowledge-graph-ui/Dockerfile` | `ghcr.io/<owner>/kg-ui:latest` |
| MCP Server | `knowledge-graph-mcp/Dockerfile` | `ghcr.io/<owner>/kg-mcp:latest` |
| Agents | `knowledge-graph-agents/Dockerfile` | `ghcr.io/<owner>/kg-agents:latest` |

`<owner>` = `agent-engineering-studio` (GitHub organization/user del repository)

---

## Decisioni chiave

| Decisione | Scelta |
|-----------|--------|
| Tag strategy | Solo `latest`, sovrascritto ad ogni push su `main` |
| Build order | Sequenziale (un job unico) |
| Docker layer cache | GitHub Actions cache (`type=gha`), scope separato per immagine |
| Pre-build checks | Lint + test per tutti e 4 i moduli |
| Registry | GitHub Container Registry (`ghcr.io`) |
| Auth | `GITHUB_TOKEN` automatico — nessun secret manuale |

---

## Architettura workflow

### Flusso complessivo

```
push su qualsiasi branch / PR verso main
        │
        ▼
   ci.yml (CI)
   ─────────────────────────────
   lint + test: api, mcp, agents (Python/ruff/pytest)
   lint + test: ui (Node/eslint/tsc)
        │
        │ (solo se push su main E ci.yml verde)
        ▼
docker-publish.yml (CD)
   ─────────────────────────────
   login ghcr.io
   setup buildx
   build+push kg-api:latest    (cache scope=kg-api)
   build+push kg-ui:latest     (cache scope=kg-ui)
   build+push kg-mcp:latest    (cache scope=kg-mcp)
   build+push kg-agents:latest (cache scope=kg-agents)
```

---

## File da creare

```
knowledge-graph/
├── .github/
│   └── workflows/
│       ├── ci.yml                          # NUOVO
│       └── docker-publish.yml              # NUOVO
├── knowledge-graph-api/
│   └── .dockerignore                       # NUOVO
├── knowledge-graph-ui/
│   └── .dockerignore                       # NUOVO
├── knowledge-graph-mcp/
│   └── .dockerignore                       # NUOVO
└── knowledge-graph-agents/
    └── .dockerignore                       # NUOVO
```

**Nessuna modifica ai Dockerfile esistenti.**

---

## Dettaglio: `ci.yml`

**Trigger:** `push` su qualsiasi branch, `pull_request` verso `main`

**Job `test` (ubuntu-latest, sequenziale):**

1. `actions/checkout@v4`
2. Setup Python 3.11 (`actions/setup-python@v5`) con cache pip
3. Setup Node 22 (`actions/setup-node@v4`) con cache npm
4. **API:** `pip install -e ".[dev]"` → `ruff check .` → `pytest` (in `knowledge-graph-api/`)
5. **MCP:** `pip install -e ".[dev]"` → `ruff check .` → `pytest` (in `knowledge-graph-mcp/`)
6. **Agents:** `pip install -e ".[dev]"` → `ruff check .` → `pytest` (in `knowledge-graph-agents/`)
7. **UI:** `npm ci` → `npm run lint` → `npm run type-check` (in `knowledge-graph-ui/`)

Se un modulo non ha test configurati, lo step usa `continue-on-error: false` ma pytest non fallisce su directory vuote.

---

## Dettaglio: `docker-publish.yml`

**Trigger:** `workflow_run` — si attiva solo quando `ci.yml` completa con `conclusion: success` su branch `main`

**Permissions:** `packages: write`, `contents: read`

**Job `publish` (ubuntu-latest, sequenziale):**

1. `actions/checkout@v4`
2. `docker/login-action@v3` → `ghcr.io` con `GITHUB_TOKEN`
3. `docker/setup-buildx-action@v3`
4. Per ogni immagine (`kg-api`, `kg-ui`, `kg-mcp`, `kg-agents`):
   - `docker/build-push-action@v6`
   - `context:` → directory del modulo
   - `tags:` → `ghcr.io/<owner>/kg-<name>:latest`
   - `cache-from: type=gha,scope=kg-<name>`
   - `cache-to: type=gha,scope=kg-<name>,mode=max`
   - `push: true`

---

## Dettaglio: `.dockerignore`

### Python (api, mcp, agents)
```
__pycache__/
*.pyc
*.pyo
.pytest_cache/
.ruff_cache/
.mypy_cache/
.venv/
venv/
*.egg-info/
dist/
build/
.env
.env.*
tests/
docs/
*.md
```

### Node (ui)
```
node_modules/
.next/
out/
.env
.env.*
*.md
coverage/
.eslintcache
*.log
```

---

## Sicurezza

- `GITHUB_TOKEN` è automatico e scaduto al termine del workflow — nessun secret da gestire
- Le immagini `ghcr.io` sono pubbliche per default su repo pubblici; su repo privati restano private
- Nessun secret applicativo (DB password, API keys) viene incluso nelle immagini — queste sono immagini base senza config runtime

---

## Dipendenze di build

I Dockerfile esistenti non richiedono modifiche. Se un Dockerfile usa `COPY . .`, il `.dockerignore` esclude automaticamente i file indesiderati dal build context.

---

## Test della pipeline

Per verificare che la pipeline funzioni correttamente:
1. Push su branch feature → solo `ci.yml` si attiva
2. PR verso `main` → solo `ci.yml` si attiva
3. Merge su `main` con CI verde → `ci.yml` poi `docker-publish.yml`
4. Merge su `main` con CI rosso → solo `ci.yml`, `docker-publish.yml` non parte
