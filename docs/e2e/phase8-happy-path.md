# Phase 8 happy-path E2E prep

This is the smallest clean path for validating the AutoClaw ↔ OpenClaw bridge with the native plugin adapter.

## Decision

For the first happy-path E2E run, reuse the existing published AutoClaw registry definitions:

- workflow: `default-bugfix`
- worker role: `main-loop-worker`
- policy: `default`

That keeps registry bootstrap counts stable and avoids introducing new permanent test definitions before the bridge is proven.

## Dedicated OpenClaw worker

Use the dedicated agent id:

- `autoclaw-worker`

Its workspace lives at:

- `~/.openclaw/workspaces/autoclaw-worker`

This worker is intentionally narrow for E2E:

- ack projected manifests first
- use callback tools, not chatty reasoning
- emit concise checkpoint payloads
- request approval/replan only when actually needed

## Required runtime config

AutoClaw needs:

- `AUTOCLAW_API_KEY`
- `AUTOCLAW_INTERNAL_API_KEY`
- `AUTOCLAW_OPENCLAW_BASE_URL`
- `AUTOCLAW_OPENCLAW_ACCOUNT`
- `AUTOCLAW_OPENCLAW_AGENT_ID=autoclaw-worker`
- `AUTOCLAW_OPENCLAW_TIMEOUT_MS=20000`

Gateway auth may come from either:

- `AUTOCLAW_OPENCLAW_GATEWAY_TOKEN`
- `OPENCLAW_GATEWAY_TOKEN`
- or `gateway.auth.token` in `OPENCLAW_CONFIG_PATH` / `~/.openclaw/openclaw.json`

Docker Compose forwards the Phase 8 OpenClaw vars into the `api` container, but a host-native API run is often the clearest debugging path while Phase 8 is still being hardened.

OpenClaw host prerequisites:

- Gateway `/v1/responses` is enabled
- the `autoclaw-worker` agent exists
- the native AutoClaw bridge plugin is loaded so callback tools are available without per-request client tool definitions
- restart the Gateway if config/plugin changes require it

## Happy-path steps

1. Start AutoClaw (host-native or Docker) against the intended database.
2. Ensure OpenClaw Gateway is reachable with authenticated `GET /v1/models` and `POST /v1/responses`.
3. Install/load the AutoClaw bridge plugin into OpenClaw if it is not already loaded.
4. On a clean or reset AutoClaw database, bootstrap the published registry definitions with `POST /internal/registry/bootstrap`.
5. Start a flow from `default-bugfix`.
   - `POST /flows/from-workflow/default-bugfix` already compiles the published workflow; a separate compile call is optional for inspection only.
6. Continue the flow until the loop worker blocks on the projected manifest.
7. Dispatch bootstrap via `/internal/flows/{flow_id}/dispatch-openclaw`.
8. Verify the worker:
   - acknowledges the manifest,
   - stays on the same session,
   - transitions the node attempt into execution.
9. Dispatch execution via `/internal/flows/{flow_id}/dispatch-openclaw` again.
10. Verify the worker:
   - records at least one valid checkpoint,
   - or emits a valid approval/replan boundary,
   - and advances the flow without manual patching.

## Host-native debug runbook (current preferred path)

Use a dedicated host-native API port while Phase 8 is still being debugged.

Example API process:

```bash
cd /home/ubuntu/leo/projects/autoclaw/apps/api
PYTHONPATH=. ../../.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8015
```

### 1. Health + Gateway reachability

```bash
curl -sS http://127.0.0.1:8015/healthz
curl -sS -H "Authorization: Bearer <gateway-token>" http://127.0.0.1:18789/v1/models
```

### 2. Bootstrap registry (clean/reset DB only)

```bash
curl -sS -H 'X-AutoClaw-API-Key: autoclaw-internal-dev-key' \
  -X POST http://127.0.0.1:8015/internal/registry/bootstrap
```

### 3. Start flow

```bash
curl -sS -H 'Content-Type: application/json' \
  -H 'X-AutoClaw-API-Key: autoclaw-operator-dev-key' \
  -X POST \
  --data @docs/e2e/fixtures/phase8-happy-path.start-flow.json \
  http://127.0.0.1:8015/flows/from-workflow/default-bugfix
```

Capture `flow_id` from the response.

### 4. Continue flow

```bash
curl -sS -H 'X-AutoClaw-API-Key: autoclaw-operator-dev-key' \
  -X POST http://127.0.0.1:8015/flows/<flow_id>/continue
```

Expected boundary before dispatch:

- root/loop state reflects a projected manifest boundary
- the node is ready for bootstrap dispatch

### 5. Bootstrap dispatch

```bash
curl -sS -H 'X-AutoClaw-API-Key: autoclaw-internal-dev-key' \
  -X POST http://127.0.0.1:8015/internal/flows/<flow_id>/dispatch-openclaw
```

Then inspect:

```bash
curl -sS -H 'X-AutoClaw-API-Key: autoclaw-operator-dev-key' \
  http://127.0.0.1:8015/flows/<flow_id>
curl -sS -H 'X-AutoClaw-API-Key: autoclaw-internal-dev-key' \
  http://127.0.0.1:8015/internal/flows/<flow_id>/context-manifests
```

Expected current partial-success signal:

- dispatch may still return `502 OpenClaw request timed out`
- but manifest status should flip from `projected` to `acked`
- the same `node_session_key` should remain in use
- the node attempt should move into execution/running state

### 6. Execution dispatch

```bash
curl -sS -H 'X-AutoClaw-API-Key: autoclaw-internal-dev-key' \
  -X POST http://127.0.0.1:8015/internal/flows/<flow_id>/dispatch-openclaw
```

Then inspect:

```bash
curl -sS -H 'X-AutoClaw-API-Key: autoclaw-operator-dev-key' \
  http://127.0.0.1:8015/flows/<flow_id>
curl -sS -H 'X-AutoClaw-API-Key: autoclaw-internal-dev-key' \
  http://127.0.0.1:8015/internal/flows/<flow_id>/checkpoints
curl -sS -H 'X-AutoClaw-API-Key: autoclaw-internal-dev-key' \
  http://127.0.0.1:8015/internal/flows/<flow_id>/audit
```

Phase 8 is only green when execution yields at least one durable control fact:

- checkpoint
- approval request
- or replan request

If execution still times out with no checkpoint, the next debugging target is the execution callback path rather than config/bootstrap.

## Success criteria

A happy-path pass is good when all of these are true:

- AutoClaw returns a real `node_session_key`
- OpenClaw accepts the dispatch
- the worker uses callback tools successfully
- the projected manifest becomes acked
- a valid checkpoint is stored
- the flow progresses to the next expected state

## Notes

- The current bridge path relies on native plugin callback tools and does **not** send per-request Responses API client tool definitions.
- The plugin-backed run is therefore the important final validation because it proves the real native adapter path.
- Current observed partial-success state: bootstrap dispatch may still return timeout even when manifest acknowledgement lands; Phase 8 is not complete until execution dispatch yields a durable checkpoint/approval/replan fact.
- If plugin install/load or Gateway endpoint config changes require a Gateway restart, pause and tell Leo first.
