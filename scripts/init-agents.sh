#!/usr/bin/env bash
# init-agents.sh
#
# Bootstraps the brain-llm instance with a default configuration:
#   1. Verify the API is reachable via GET /health.
#   2. Ensure an "ollama-local" provider exists (provider_type=ollama,
#      base_url=http://localhost:11434).
#   3. Register the model "llama3.2:latest" (model_type=llm) on that
#      provider if it is not already registered.
#   4. Create an agent named "Assistant" using this provider/model pair.
#
# The script is idempotent: re-running it will reuse any existing
# provider, model or agent that matches the expected name.
#
# Environment variables (all optional):
#   BASE_URL      - brain-llm API base URL         (default: http://localhost:8000)
#   OLLAMA_URL    - Ollama server base URL         (default: http://localhost:11434)
#   PROVIDER_NAME - Name of the provider record    (default: ollama-local)
#   MODEL_NAME    - Name of the model to register  (default: llama3.2:latest)
#   AGENT_NAME    - Name of the agent to create    (default: Assistant)

set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
PROVIDER_NAME="${PROVIDER_NAME:-ollama-local}"
MODEL_NAME="${MODEL_NAME:-llama3.2:latest}"
AGENT_NAME="${AGENT_NAME:-Assistant}"

log()  { printf "\033[1;34m[init-agents]\033[0m %s\n" "$*"; }
fail() { printf "\033[1;31m[error]\033[0m %s\n" "$*" >&2; exit 1; }

need() { command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"; }
need curl
need python3

# -------- helpers ----------------------------------------------------------

# Extract an integer field from a JSON object on stdin.
json_int() {
    python3 -c "import sys, json; print(json.load(sys.stdin).get('$1', ''))"
}

# Find the first object in a JSON array whose 'name' equals $1.
# Prints the matched id or nothing if no match.
find_id_by_name() {
    local needle="$1"
    python3 -c "
import sys, json
items = json.load(sys.stdin)
match = next((i for i in items if i.get('name') == '$needle'), None)
print(match['id'] if match else '')
"
}

# Find a model by name AND provider id.
find_model_id() {
    local name="$1" pid="$2"
    python3 -c "
import sys, json
items = json.load(sys.stdin)
match = next((i for i in items
              if i.get('name') == '$name' and i.get('provider_id') == $pid), None)
print(match['id'] if match else '')
"
}

# -------- 1. health check --------------------------------------------------

log "Checking API availability at $BASE_URL/health ..."
if ! curl -fsS "$BASE_URL/health" >/dev/null; then
    fail "API is not reachable at $BASE_URL/health"
fi
log "API is up."

# -------- 2. provider ------------------------------------------------------

log "Looking for existing provider '$PROVIDER_NAME' ..."
PROVIDER_ID=$(curl -fsS "$BASE_URL/api/v1/providers" | find_id_by_name "$PROVIDER_NAME")

if [ -z "$PROVIDER_ID" ]; then
    log "Creating Ollama provider '$PROVIDER_NAME' -> $OLLAMA_URL"
    PROVIDER_ID=$(curl -fsS -X POST "$BASE_URL/api/v1/providers" \
        -H "Content-Type: application/json" \
        -d "$(cat <<JSON
{
  "name": "$PROVIDER_NAME",
  "provider_type": "ollama",
  "base_url": "$OLLAMA_URL",
  "default_model": "$MODEL_NAME",
  "description": "Local Ollama server on $OLLAMA_URL"
}
JSON
)" | json_int id)
fi
[ -n "$PROVIDER_ID" ] || fail "Failed to create or find provider."
log "Provider ready (id=$PROVIDER_ID)."

# -------- 3. model ---------------------------------------------------------

log "Looking for existing model '$MODEL_NAME' on provider $PROVIDER_ID ..."
MODEL_ID=$(curl -fsS "$BASE_URL/api/v1/models" | find_model_id "$MODEL_NAME" "$PROVIDER_ID")

if [ -z "$MODEL_ID" ]; then
    log "Registering model '$MODEL_NAME' (llm) on provider $PROVIDER_ID ..."
    MODEL_ID=$(curl -fsS -X POST "$BASE_URL/api/v1/models" \
        -H "Content-Type: application/json" \
        -d "$(cat <<JSON
{
  "name": "$MODEL_NAME",
  "model_type": "llm",
  "provider_id": $PROVIDER_ID,
  "description": "Llama 3.2 served by Ollama"
}
JSON
)" | json_int id)
fi
[ -n "$MODEL_ID" ] || fail "Failed to create or find model."
log "Model ready (id=$MODEL_ID)."

# -------- 4. agent ---------------------------------------------------------

log "Looking for existing agent '$AGENT_NAME' ..."
AGENT_ID=$(curl -fsS "$BASE_URL/api/v1/agents" | find_id_by_name "$AGENT_NAME")

if [ -z "$AGENT_ID" ]; then
    log "Creating agent '$AGENT_NAME' ..."
    AGENT_ID=$(curl -fsS -X POST "$BASE_URL/api/v1/agents" \
        -H "Content-Type: application/json" \
        -d "$(cat <<JSON
{
  "name": "$AGENT_NAME",
  "role": "General purpose assistant",
  "description": "Default assistant powered by $MODEL_NAME on $PROVIDER_NAME",
  "instructions": "You are a helpful assistant. Answer concisely and accurately.",
  "provider_id": $PROVIDER_ID,
  "model": "$MODEL_NAME"
}
JSON
)" | json_int id)
fi
[ -n "$AGENT_ID" ] || fail "Failed to create or find agent."
log "Agent ready (id=$AGENT_ID)."

# -------- 5. usage hint ----------------------------------------------------

cat <<EOF

All good. Try it out:

  curl -X POST $BASE_URL/api/v1/agents/$AGENT_ID/run \\
       -H 'Content-Type: application/json' \\
       -d '{"message": "Hello, who are you?"}'
EOF
