Run the same lint and test checks that GitHub Actions CI runs, but locally and only for the modules that have changed. This prevents CI failures and blocked Docker builds before they happen.

## What to do

**Step 1 — Detect changed modules**

Run this command from the repo root and collect the output:

```bash
git diff --name-only HEAD
git diff --name-only --cached
```

From the file paths, determine which of these four modules are affected:
- `knowledge-graph-api` — any path starting with `knowledge-graph-api/`
- `knowledge-graph-mcp` — any path starting with `knowledge-graph-mcp/`
- `knowledge-graph-agents` — any path starting with `knowledge-graph-agents/`
- `knowledge-graph-ui` — any path starting with `knowledge-graph-ui/`

If `$ARGUMENTS` names a specific module (e.g. `api`, `mcp`, `agents`, `ui`), check only that one instead.

If no files are changed and no argument is given, check all four modules.

**Step 2 — Run checks for each affected module**

Run each check in sequence. Stop immediately if any command exits non-zero and report the failure clearly. Do not skip to the next module after a failure — fix first.

### knowledge-graph-api

```bash
cd knowledge-graph-api
pip install -r requirements.txt -q
ruff check .
pytest tests/ -v --tb=short
cd ..
```

### knowledge-graph-mcp

```bash
cd knowledge-graph-mcp
pip install -e . -q
pip install ruff pytest pytest-asyncio -q
ruff check .
pytest tests/ -v --tb=short
cd ..
```

### knowledge-graph-agents

```bash
cd knowledge-graph-agents
pip install --pre -r requirements.txt -q
pip install ruff -q
ruff check .
pytest tests/ -v --tb=short
cd ..
```

### knowledge-graph-ui

```bash
cd knowledge-graph-ui
npm ci --silent
npm run lint
npx tsc --noEmit
cd ..
```

**Step 3 — Report**

After all checks finish, print a summary table:

| Module | Lint | Tests | Result |
|--------|------|-------|--------|
| api    | ✓/✗ | ✓/✗  | PASS/FAIL |
| ...    |      |       |           |

If everything passed: confirm it is safe to commit and push.

If anything failed: show the exact error output and tell the user which file and line to fix before committing.

## Key rules

- Always run from the repo root (`knowledge-graph/`), not from inside a module directory.
- Use `--tb=short` for pytest so failures are readable without being overwhelming.
- `ruff check` errors that end with `[*]` are auto-fixable — offer to run `ruff check --fix .` in that module if any are found.
- Never commit or push as part of this check — this command only validates, it does not modify git state.
