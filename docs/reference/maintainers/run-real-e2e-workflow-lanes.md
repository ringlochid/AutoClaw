# Run the current real minimal, normal, and maximal e2e workflow lanes

Status: Reference

Last verified: 2026-05-21

This page describes the current manual operator runbook for exercising the shipped minimal, normal, and maximal workflow fixtures against a real local `autoclaw serve` process.

Use this page when you want a real current-service e2e check instead of an in-process pytest helper.

## What this page covers

- start a fresh local service on the shipped CLI path
- optionally upload or update definitions
- start a real task run for the shipped minimal, normal, and maximal workflow fixtures
- inspect runtime status, operator snapshot, operator trace, and observability refs
- locate the current criteria files and decide whether the lane satisfied them

## What this page does not cover

- separate bridge-plugin packaging or manifest wiring outside this checkout
- every possible callback or mounted node-MCP step needed to drive a live worker by hand

For the current bridge-facing callback and node-MCP surfaces, see [Use the current OpenClaw bridge plugin](../operator/use-the-openclaw-bridge-plugin.md).

## Current lane keys

| Lane      | Workflow key                   | Current proving goal |
| --------- | ------------------------------ | -------------------- |
| minimal   | `minimal-implement-change`     | one bounded implementation child plus parent or root release |
| normal    | `normal-parent-first-release`  | parent-owned implementation subtree, parent-first verification, and bounded root closure |
| maximal   | `maximal-parent-first-release` | multiple subtrees, bounded review or QA aggregation, and final root release |

These workflow keys are shipped seed fixtures.

You do not need a definition upload just to run the stock lanes.

## Recommended isolated local setup

Use an explicit config and data dir so the e2e lane does not share state with a different local run.

```bash
cd /home/ubuntu/leo/projects/autoclaw
python -m venv .venv
./.venv/bin/pip install -e .[dev]

export CONFIG=/tmp/autoclaw-real-e2e/autoclaw-config.toml
export DATA=/tmp/autoclaw-real-e2e/data
export API=http://127.0.0.1:8123
export API_KEY=api-test-key
export INTERNAL_API_KEY=internal-test-key

./.venv/bin/autoclaw init \
  --config "$CONFIG" \
  --data-dir "$DATA" \
  --api-key "$API_KEY" \
  --internal-api-key "$INTERNAL_API_KEY" \
  --force
```

Optional clean SQLite reset before another lane:

```bash
./.venv/bin/autoclaw db reset --config "$CONFIG" --json
```

Start the real service in one terminal and keep it running:

```bash
./.venv/bin/autoclaw serve --config "$CONFIG" 2>&1 | tee /tmp/autoclaw-real-e2e/serve.log
```

Fast health check from a second terminal:

```bash
curl -s "$API/healthz"
curl -s "$API/readyz"
```

## Optional definition upload

The shipped seed definitions are enough for the stock minimal, normal, and maximal lanes.

Only upload definitions when you want to exercise definition ingest itself or override the current seed-backed truth before launch.

Example role upload:

```bash
cat >/tmp/phase45-reviewer.json <<'JSON'
{
  "kind": "role",
  "content": {
    "id": "phase45-reviewer",
    "description": "Review worker for a real e2e lane.",
    "allowed_node_kinds": ["worker"],
    "instruction": "Review only the current surfaced evidence."
  }
}
JSON

curl -sS \
  -H "X-AutoClaw-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -X POST "$API/definitions" \
  -d @/tmp/phase45-reviewer.json
```

For workflow or policy uploads, use the current shapes in [`definition-and-task-compose-yaml-contract.md`](../api/definition-and-task-compose-yaml-contract.md).

## Start a real lane

The current public task-start route is `POST /tasks/start`.

It reuses the `TaskComposeInput` body and waits for initial runtime effects before returning.

### Minimal

```bash
cat >/tmp/task-compose-minimal.json <<'JSON'
{
  "task": {
    "key": "auth-refresh-hardening",
    "title": "Harden auth refresh flow",
    "summary": "Investigate and fix the auth refresh regression.",
    "instruction": "Stay scoped to the auth refresh failure path only."
  },
  "workflow": {
    "key": "minimal-implement-change"
  }
}
JSON

curl -sS \
  -H "X-AutoClaw-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -X POST "$API/tasks/start" \
  -d @/tmp/task-compose-minimal.json
```

### Normal

Use the same payload and change only the workflow key:

```json
"workflow": { "key": "normal-parent-first-release" }
```

### Maximal

Use the same payload and change only the workflow key:

```json
"workflow": { "key": "maximal-parent-first-release" }
```

## Capture the current task id and manifest path

Save the task-start response and extract the current task id plus manifest path:

```bash
curl -sS \
  -H "X-AutoClaw-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -X POST "$API/tasks/start" \
  -d @/tmp/task-compose-minimal.json \
  >/tmp/task-start.json

TASK_ID="$(jq -r '.task_id' /tmp/task-start.json)"
MANIFEST_PATH="$(jq -r '.workflow_manifest_ref.path' /tmp/task-start.json)"
TASK_ROOT="$(dirname "$(dirname "$MANIFEST_PATH")")"
```

`MANIFEST_PATH` points at:

- `<task_root>/_runtime/workflow-manifest.md`

and `TASK_ROOT` is the root you will use for criteria, artifacts, and observability file rereads.

## Inspect runtime and operator state

Current operator read surfaces are:

- `GET /runtime/tasks/{task_id}`
- `GET /operator/tasks/{task_id}/snapshot`
- `GET /operator/tasks/{task_id}/trace`

Recommended first reads:

```bash
curl -sS -H "X-AutoClaw-API-Key: $API_KEY" \
  "$API/runtime/tasks/$TASK_ID"

curl -sS -H "X-AutoClaw-API-Key: $API_KEY" \
  "$API/operator/tasks/$TASK_ID/snapshot"

curl -sS -H "X-AutoClaw-API-Key: $API_KEY" \
  "$API/operator/tasks/$TASK_ID/trace?scope=whole&sort=occurred_at_asc"
```

Helpful trace checks:

```bash
curl -sS -H "X-AutoClaw-API-Key: $API_KEY" \
  "$API/operator/tasks/$TASK_ID/trace?scope=whole&sort=occurred_at_asc" \
  | jq -r '.dispatch_history[].node_key'
```

If you are using `operator MCP` instead of HTTP, follow the same observe-first sequence:

- `get_runtime_task`
- `get_operator_snapshot`
- `get_operator_trace`
- `get_delivery_state_ref` / `get_continuity_state_ref` / `get_watchdog_state_ref` / `get_provider_events_ref` only when deeper support-file inspection is needed

Do not use `continue_task` as a polling or diagnostic command. In current shipped behavior it is a mutating pause-resume control only, and any use should still carry a fresh `expected_active_flow_revision_id` from a current runtime read.

Treat the observability `get_*_ref` lane as support-only reread. It returns file refs/paths rather than parsed status answers, and controller/runtime truth wins if a support reread disagrees with the current runtime state.

Expected node progression for the stock lanes:

- minimal:
  - `root`
  - `implement_change`
- normal:
  - `root`
  - `implementation_subtree`
  - `investigate_issue`
  - `implement_change`
  - `review_change`
  - `release_closure`
- maximal:
  - `root`
  - `discovery`
  - `gather_evidence`
  - `implementation_loop`
  - `plan_iteration`
  - `implement_change`
  - `review_change`
  - `qa_sweep`
  - `release_closure`

## Follow failure logs and observability refs

Current observability routes return file refs, not assembled truth:

- `GET /observability/tasks/{task_id}/delivery-state`
- `GET /observability/tasks/{task_id}/continuity-state`
- `GET /observability/tasks/{task_id}/watchdog-state`
- `GET /observability/tasks/{task_id}/provider-events`

Read them like this:

```bash
curl -sS -H "X-AutoClaw-API-Key: $API_KEY" \
  "$API/observability/tasks/$TASK_ID/delivery-state"

curl -sS -H "X-AutoClaw-API-Key: $API_KEY" \
  "$API/observability/tasks/$TASK_ID/provider-events"
```

Then open the returned files under:

- `<task_root>/_runtime/dispatch/<dispatch_id>/delivery-state.json`
- `<task_root>/_runtime/dispatch/<dispatch_id>/continuity-state.json`
- `<task_root>/_runtime/dispatch/<dispatch_id>/watchdog-state.json`
- `<task_root>/_runtime/dispatch/<dispatch_id>/provider-events.ndjson`

Use them this way:

- `delivery-state.json`: transport family, transport state, provider error, and acceptance or terminal timestamps
- `continuity-state.json`: session-key presence, invalidation reason, and current continuity drift
- `watchdog-state.json`: stale classification, recovery action, and escalation reason
- `provider-events.ndjson`: adapter or provider event timeline in order

Also inspect the real service log you started with `tee`:

```bash
tail -n 200 /tmp/autoclaw-real-e2e/serve.log
```

## Criteria and success checks

Current criteria are controller-owned files under:

- `<task_root>/context/criteria/`

List them:

```bash
find "$TASK_ROOT/context/criteria" -maxdepth 1 -type f | sort
```

Use the criteria files together with:

- the workflow manifest at `$MANIFEST_PATH`
- operator snapshot current paths
- operator trace dispatch or checkpoint history
- produced artifacts under `<task_root>/outputs/artifacts/`

Current decision rule:

- treat criteria files as the acceptance contract
- treat operator trace and observability refs as the explanation of what actually happened
- treat artifacts and checkpoints as the concrete evidence that the lane did or did not satisfy the criteria

## Current failure triage shortcut

- launch failed before useful execution: inspect `delivery-state.json`, `continuity-state.json`, and the service log
- execution stalled: inspect `watchdog-state.json`, operator trace, and current runtime status
- wrong node or wrong subtree advanced: inspect `trace?scope=whole` and compare node order with the lane expectations above
- release looked wrong: inspect `context/criteria/`, surfaced artifact refs, and the final root or parent dispatch in operator trace

## Relationship to the bridge-facing path

This page gives the operator-side current e2e runbook:

- setup
- optional definition upload
- public task start
- runtime or operator inspection
- failure triage
- criteria checks

If your real lane also needs live node-tool or callback writes, continue with:

- [Use the current OpenClaw bridge plugin](../operator/use-the-openclaw-bridge-plugin.md)

That page owns the current callback and mounted node-MCP write surfaces.

## Evidence

- inspected code in `apps/api/src/autoclaw/interfaces/cli/__init__.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/definitions.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/tasks.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/runtime.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/operator.py`
- inspected code in `apps/api/src/autoclaw/interfaces/http/routers/observability.py`
- inspected code in `apps/api/src/autoclaw/definitions/contracts/registry.py`
- inspected code in `apps/api/src/autoclaw/runtime/contracts/start.py`
- inspected code in `apps/api/src/autoclaw/runtime/contracts/primitives.py`
- inspected current route map in `../api/api-surface-and-route-map.md`
- inspected current read-model docs in `../operator/runtime-read-models-and-operator-surfaces.md`
- inspected e2e fixtures in `apps/api/tests/helpers/runtime_seed.py`
- inspected e2e flows in:
  - `apps/api/tests/e2e/phase2/minimal_runtime_lane_support.py`
  - `apps/api/tests/e2e/phase3/normal_lane/flow.py`
  - `apps/api/tests/e2e/phase4/maximal_lane/flow.py`
- did not execute the commands in this docs pass
