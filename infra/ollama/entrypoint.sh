#!/bin/sh
# Start Ollama server in background, pull required models, then wait.
set -e

MODELS="${OLLAMA_MODELS:-nomic-embed-text llama3}"

log() {
  echo "[ollama-init] $(date -u '+%Y-%m-%dT%H:%M:%SZ') $*"
}

log "Starting ollama serve..."
ollama serve &
SERVER_PID=$!

# Wait until the API is ready using 'ollama list' (no curl dependency)
log "Waiting for Ollama API to be ready..."
ATTEMPTS=0
until ollama list > /dev/null 2>&1; do
  ATTEMPTS=$((ATTEMPTS + 1))
  if [ $ATTEMPTS -ge 60 ]; then
    log "ERROR: Ollama API did not become ready after 60 seconds. Exiting."
    exit 1
  fi
  sleep 1
done
log "Ollama API is ready (after ${ATTEMPTS}s)."

# Pull each model if not already present
TOTAL=$(echo "$MODELS" | wc -w)
CURRENT=0
for MODEL in $MODELS; do
  CURRENT=$((CURRENT + 1))
  if ollama list 2>/dev/null | grep -q "${MODEL}"; then
    log "[${CURRENT}/${TOTAL}] Model '${MODEL}' already present — skipping pull."
  else
    log "[${CURRENT}/${TOTAL}] Pulling model '${MODEL}'... (this may take several minutes)"
    ollama pull "${MODEL}"
    log "[${CURRENT}/${TOTAL}] Model '${MODEL}' pulled successfully."
  fi
done

log "========================================="
log "ALL MODELS READY — Ollama is serving."
log "Loaded models:"
ollama list 2>/dev/null | tail -n +2 | while IFS= read -r line; do
  log "  * ${line}"
done
log "========================================="

# Hand off to the background server process
wait $SERVER_PID
