# Docker + GitHub Actions CI/CD Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Creare 4 `.dockerignore`, il workflow CI (`ci.yml`) e il workflow CD (`docker-publish.yml`) per pubblicare automaticamente le immagini `kg-api`, `kg-ui`, `kg-mcp`, `kg-agents` su `ghcr.io/agent-engineering-studio/` ad ogni push su `main` con CI verde.

**Architecture:** Due workflow separati: `ci.yml` esegue lint + test su ogni push/PR; `docker-publish.yml` si attiva via `workflow_run` solo quando `ci.yml` passa su `main` e fa build+push sequenziale con GHA layer cache. Nessuna modifica ai Dockerfile esistenti.

**Tech Stack:** GitHub Actions, Docker Buildx, ghcr.io, Python 3.11 (ruff + pytest), Node 22 (eslint + tsc)

---

## File Map

| File | Azione |
|------|--------|
| `.github/workflows/ci.yml` | CREATE |
| `.github/workflows/docker-publish.yml` | CREATE |
| `knowledge-graph-api/.dockerignore` | CREATE |
| `knowledge-graph-ui/.dockerignore` | CREATE |
| `knowledge-graph-mcp/.dockerignore` | CREATE |
| `knowledge-graph-agents/.dockerignore` | CREATE |

---

## Task 1: `.dockerignore` per i moduli Python (api, mcp, agents)

**Files:**
- Create: `knowledge-graph-api/.dockerignore`
- Create: `knowledge-graph-mcp/.dockerignore`
- Create: `knowledge-graph-agents/.dockerignore`

- [ ] **Step 1: Crea `knowledge-graph-api/.dockerignore`**

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
.git/
.github/
```

- [ ] **Step 2: Crea `knowledge-graph-mcp/.dockerignore`**

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
.git/
.github/
```

- [ ] **Step 3: Crea `knowledge-graph-agents/.dockerignore`**

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
.git/
.github/
```

- [ ] **Step 4: Verifica che i file esistano**

```bash
ls knowledge-graph-api/.dockerignore knowledge-graph-mcp/.dockerignore knowledge-graph-agents/.dockerignore
```

Atteso: 3 file elencati senza errori.

- [ ] **Step 5: Commit**

```bash
git add knowledge-graph-api/.dockerignore knowledge-graph-mcp/.dockerignore knowledge-graph-agents/.dockerignore
git commit -m "chore: add .dockerignore for Python modules (api, mcp, agents)"
```

---

## Task 2: `.dockerignore` per il modulo UI (Node)

**Files:**
- Create: `knowledge-graph-ui/.dockerignore`

- [ ] **Step 1: Crea `knowledge-graph-ui/.dockerignore`**

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
npm-debug.log*
.git/
.github/
```

- [ ] **Step 2: Verifica che il file esista**

```bash
ls knowledge-graph-ui/.dockerignore
```

Atteso: file elencato senza errori.

- [ ] **Step 3: Commit**

```bash
git add knowledge-graph-ui/.dockerignore
git commit -m "chore: add .dockerignore for UI module (Node)"
```

---

## Task 3: Workflow CI (`ci.yml`)

**Files:**
- Create: `.github/workflows/ci.yml`

Note tecniche pre-implementazione:
- **API**: `pip install -r requirements.txt` include già `ruff` e `pytest`
- **MCP**: `pyproject.toml` non ha ruff/pytest → install separato: `pip install ruff pytest pytest-asyncio`
- **Agents**: `requirements.txt` ha pytest ma non ruff → install separato: `pip install ruff`; usa `--pre` per `agent-framework`
- **UI**: script `lint` = `next lint`; type-check via `npx tsc --noEmit`

- [ ] **Step 1: Crea `.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: ["**"]
  pull_request:
    branches: [main]

jobs:
  test:
    name: Lint & Test
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Setup Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"
          cache-dependency-path: |
            knowledge-graph-api/requirements.txt
            knowledge-graph-agents/requirements.txt

      - name: Setup Node 22
        uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: "npm"
          cache-dependency-path: knowledge-graph-ui/package-lock.json

      # ── API ────────────────────────────────────────────────────────
      - name: "[API] Install dependencies"
        working-directory: knowledge-graph-api
        run: pip install -r requirements.txt

      - name: "[API] Lint (ruff)"
        working-directory: knowledge-graph-api
        run: ruff check .

      - name: "[API] Test (pytest)"
        working-directory: knowledge-graph-api
        run: pytest tests/ -v --tb=short

      # ── MCP ────────────────────────────────────────────────────────
      - name: "[MCP] Install dependencies"
        working-directory: knowledge-graph-mcp
        run: |
          pip install -e .
          pip install ruff pytest pytest-asyncio

      - name: "[MCP] Lint (ruff)"
        working-directory: knowledge-graph-mcp
        run: ruff check .

      - name: "[MCP] Test (pytest)"
        working-directory: knowledge-graph-mcp
        run: pytest tests/ -v --tb=short

      # ── Agents ─────────────────────────────────────────────────────
      - name: "[Agents] Install dependencies"
        working-directory: knowledge-graph-agents
        run: |
          pip install --pre -r requirements.txt
          pip install ruff

      - name: "[Agents] Lint (ruff)"
        working-directory: knowledge-graph-agents
        run: ruff check .

      - name: "[Agents] Test (pytest)"
        working-directory: knowledge-graph-agents
        run: pytest tests/ -v --tb=short

      # ── UI ─────────────────────────────────────────────────────────
      - name: "[UI] Install dependencies"
        working-directory: knowledge-graph-ui
        run: npm ci

      - name: "[UI] Lint (eslint)"
        working-directory: knowledge-graph-ui
        run: npm run lint

      - name: "[UI] Type-check (tsc)"
        working-directory: knowledge-graph-ui
        run: npx tsc --noEmit
```

- [ ] **Step 2: Verifica sintassi YAML**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))" && echo "YAML OK"
```

Atteso: `YAML OK`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add CI workflow with lint and test for all modules"
```

---

## Task 4: Workflow CD (`docker-publish.yml`)

**Files:**
- Create: `.github/workflows/docker-publish.yml`

Note tecniche:
- Trigger: `workflow_run` su `ci.yml` con `conclusion: success` su branch `main`
- Auth: `GITHUB_TOKEN` automatico, nessun secret manuale
- Owner: `agent-engineering-studio` (da `github.repository_owner`)
- Cache scope separato per ogni immagine

- [ ] **Step 1: Crea `.github/workflows/docker-publish.yml`**

```yaml
name: Docker Publish

on:
  workflow_run:
    workflows: ["CI"]
    types: [completed]
    branches: [main]

permissions:
  contents: read
  packages: write

jobs:
  publish:
    name: Build & Push Docker Images
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Login to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Setup Docker Buildx
        uses: docker/setup-buildx-action@v3

      # ── kg-api ─────────────────────────────────────────────────────
      - name: Build & Push kg-api
        uses: docker/build-push-action@v6
        with:
          context: ./knowledge-graph-api
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/kg-api:latest
          cache-from: type=gha,scope=kg-api
          cache-to: type=gha,scope=kg-api,mode=max

      # ── kg-ui ──────────────────────────────────────────────────────
      - name: Build & Push kg-ui
        uses: docker/build-push-action@v6
        with:
          context: ./knowledge-graph-ui
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/kg-ui:latest
          cache-from: type=gha,scope=kg-ui
          cache-to: type=gha,scope=kg-ui,mode=max

      # ── kg-mcp ─────────────────────────────────────────────────────
      - name: Build & Push kg-mcp
        uses: docker/build-push-action@v6
        with:
          context: ./knowledge-graph-mcp
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/kg-mcp:latest
          cache-from: type=gha,scope=kg-mcp
          cache-to: type=gha,scope=kg-mcp,mode=max

      # ── kg-agents ──────────────────────────────────────────────────
      - name: Build & Push kg-agents
        uses: docker/build-push-action@v6
        with:
          context: ./knowledge-graph-agents
          push: true
          tags: ghcr.io/${{ github.repository_owner }}/kg-agents:latest
          cache-from: type=gha,scope=kg-agents
          cache-to: type=gha,scope=kg-agents,mode=max
```

- [ ] **Step 2: Verifica sintassi YAML**

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/docker-publish.yml'))" && echo "YAML OK"
```

Atteso: `YAML OK`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/docker-publish.yml
git commit -m "ci: add Docker publish workflow for ghcr.io on main"
```

---

## Task 5: Push finale

- [ ] **Step 1: Verifica stato git**

```bash
git status
git log --oneline -5
```

Atteso: working tree pulito, 4-5 commit recenti visibili.

- [ ] **Step 2: Push su main**

```bash
git push origin main
```

Atteso: push completato, GitHub Actions si attiva automaticamente.

- [ ] **Step 3: Verifica workflow su GitHub**

Vai su `https://github.com/agent-engineering-studio/knowledge-graph/actions` e verifica:
- `CI` workflow appare come triggered
- Al completamento con successo, `Docker Publish` parte automaticamente

---

## Self-review checklist

- [x] `.dockerignore` coprente per tutti i moduli (Python e Node)
- [x] `ci.yml`: install corretto per ogni modulo (API usa requirements.txt con ruff; MCP installa ruff separatamente; Agents usa --pre per agent-framework)
- [x] `docker-publish.yml`: trigger `workflow_run` + `if: conclusion == 'success'` garantisce che non parta su CI fallita
- [x] `github.repository_owner` è dinamico — funziona su fork senza modifiche
- [x] Cache scope separato per ogni immagine — nessun conflitto
- [x] Nessun secret manuale richiesto — solo `GITHUB_TOKEN` automatico
