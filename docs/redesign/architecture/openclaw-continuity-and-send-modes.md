# OpenClaw Continuity And Send Modes

Status: Target

## Purpose

This page records the shipped Phase 4A send-mode truth and keeps any future transport continuity detail below the canonical v1 session/run/abort architecture.

## Core rule

The controller always regenerates the full canonical prompt package before a dispatch.

Canonical v1 dispatch control does not depend on provider-native continuation. Parent/root same-attempt redispatch keeps the same Gateway `sessionKey`, sends a fresh Gateway `agent` request with a fresh `idempotencyKey`, and still emits `full_prompt` by resending the full regenerated canonical prompt package. Gateway then returns a fresh `runId` for that live execution. Continuity-sideband state may still be persisted for observability, but it does not create a live controller path that emits `same_session_continue`. It does not change assignment lineage, attempt lineage, persisted prompt truth, or the controller recovery-action family.

## Canonical v1 control consequence

- `full_prompt` is the only send mode emitted by the canonical live controller path
- parent/root same-attempt redispatch keeps the same Gateway `sessionKey`, sends a fresh `idempotencyKey`, and accepts a fresh returned `runId`
- worker retry, new attempt, and fresh child assignment use a fresh Gateway `sessionKey` and a fresh `runId`
- `session_key_present` and `invalidation_reason` remain
  transport-private/operator-facing observability only
- any retained `previous_response_id` or `same_session_continue` persistence is
  transitional implementation debt, not live target canon

## Shipped controller mapping

| Controller action                              | Canonical transport mapping |
| ---------------------------------------------- | --------------------------- |
| parent/root `redispatch_same_attempt`          | Gateway WS `agent` with same `sessionKey`, fresh `idempotencyKey`, full resend, and fresh returned `runId` |
| worker retry or any semantic `create_new_attempt` | `full_prompt` over a fresh-session launch |
| `escalate`                                     | no dispatch                 |

## Reserved continuity shape

Current code still persists some continuity-sideband debt such as
`same_session_continue` and `previous_response_id`.

In the shipped Phase 4A runtime, those fields do not change send-mode selection:

- launch control still emits `full_prompt`
- OpenClaw request envelopes still carry the regenerated canonical prompt package
- `continuity-state.json` remains an observability projection, not a second dispatch planner

If later work activates adapter-private same-session reuse, that later phase
must restate the exact legality and invalidation rules instead of relying on
this Phase 4A page to imply a live path that does not currently ship.

## OpenClaw request mapping

Keep the canonical Gateway WS request shape separate from any OpenResponses HTTP adapter detail.

Canonical Gateway WS `agent` request fields:

- `sessionKey` = the Gateway continuity selector for the current execution context
- `message` = the full regenerated canonical prompt package as one root string
- `idempotencyKey` = the fresh launch/dedupe key for that dispatch request

Canonical Gateway WS response field used by runtime:

- `runId` = the fresh returned live-execution handle for that request

OpenResponses HTTP adapter-native continuity fields, if retained:

- provider `session_key`
- `previous_response_id`

Rules:

- provider/OpenResponses fields are adapter-native transport detail only
- they are not the canonical Gateway WS request shape
- they are not the required controller inputs for parent/root same-attempt redispatch

The persisted prompt truth remains the full regenerated canonical prompt package for every dispatch.

## Send-mode consequences

### `full_prompt`

- sends the regenerated prompt package in one `message` field
- uses the canonical Gateway WS `agent` path with same `sessionKey` and a fresh `idempotencyKey`
- accepts a fresh returned `runId` from Gateway
- does not require `previous_response_id` on the canonical Gateway WS path
- is the locked resend shape for parent/root same-attempt redispatch

### Reserved `same_session_continue` shape

- the prompt bundle and transport models still define it as transitional
  implementation debt
- shipped Phase 4A control does not emit it
- prompt and runtime docs must not describe it as an available controller
  recovery path

## Related contracts

- [OpenClaw session lifecycle](openclaw-session-lifecycle.md)
- [Watchdog and recovery contract](watchdog-and-recovery-contract.md)
- [Render and persistence](../prompt-layer/render-and-persistence.md)
