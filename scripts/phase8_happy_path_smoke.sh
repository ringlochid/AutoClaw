#!/usr/bin/env bash
set -euo pipefail

API_URL="${AUTOCLAW_API_URL:-http://127.0.0.1:8001}"
WORKFLOW_KEY="${AUTOCLAW_WORKFLOW_KEY:-default-bugfix}"
OPERATOR_KEY="${AUTOCLAW_API_KEY:-autoclaw-operator-dev-key}"
INTERNAL_KEY="${AUTOCLAW_INTERNAL_API_KEY:-autoclaw-internal-dev-key}"
FIXTURE="${AUTOCLAW_PHASE8_FIXTURE:-docs/e2e/fixtures/phase8-happy-path.start-flow.json}"

if [[ ! -f "$FIXTURE" ]]; then
  echo "Missing fixture: $FIXTURE" >&2
  exit 1
fi

start_response=$(curl -sS \
  -H "Content-Type: application/json" \
  -H "X-AutoClaw-API-Key: ${OPERATOR_KEY}" \
  -X POST \
  --data @"$FIXTURE" \
  "${API_URL}/flows/from-workflow/${WORKFLOW_KEY}")

flow_id=$(python3 - <<'PY' "$start_response"
import json, sys
payload = json.loads(sys.argv[1])
print(payload["flow_id"])
PY
)

continue_response=$(curl -sS \
  -H "X-AutoClaw-API-Key: ${OPERATOR_KEY}" \
  -X POST \
  "${API_URL}/flows/${flow_id}/continue")

dispatch_response=$(curl -sS \
  -H "X-AutoClaw-API-Key: ${INTERNAL_KEY}" \
  -X POST \
  "${API_URL}/internal/flows/${flow_id}/dispatch-openclaw")

python3 - <<'PY' "$continue_response" "$dispatch_response"
import json, sys
continued = json.loads(sys.argv[1])
dispatch = json.loads(sys.argv[2])
print("flow_id=", dispatch["flow_id"])
print("phase=", dispatch["phase"])
print("node_session_key=", dispatch["node_session_key"])
print("openclaw_response_id=", dispatch.get("openclaw_response_id"))
print("manifest_id=", dispatch.get("manifest_id"))
print("flow_status_after_continue=", continued["status"])
PY
