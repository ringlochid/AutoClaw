# OpenClaw Continuity And Send Modes

Status: Target

## Purpose

This page records the shipped Phase 4A send-mode truth and keeps any future transport continuity detail below the canonical v1 session/run/abort architecture.

## Core rule

The controller always regenerates the full canonical prompt package before a dispatch.

Canonical v1 dispatch control does not depend on provider-native continuation. The shipped runtime emits `full_prompt` for every launch today. Continuity-sideband state may still be persisted for observability, but it does not create a live controller path that emits `same_session_continue`. It does not change assignment lineage, attempt lineage, Gateway `sessionKey`, Gateway `runId`, persisted prompt truth, or the controller recovery-action family.

## Canonical v1 control consequence

- `full_prompt` is the only send mode emitted by the shipped runtime
- callback-safe dispatch separation uses a fresh Gateway `sessionKey` per dispatch
- persisted continuity-sideband fields such as `previous_response_id`, `session_key_present`, and `invalidation_reason` remain transport-private/operator-facing observability only
- any future `same_session_continue` activation would need its owning phase to reopen canon explicitly

## Shipped controller mapping

| Controller action         | Shipped transport mapping |
| ------------------------- | ------------------------- |
| `redispatch_same_attempt` | `full_prompt`             |
| `create_new_attempt`      | `full_prompt`             |
| `escalate`                | no dispatch               |

## Reserved continuity shape

The prompt bundle schema and some sideband projections still reserve continuity fields such as `same_session_continue` and `previous_response_id`.

In the shipped Phase 4A runtime, those fields do not change send-mode selection:

- launch control still emits `full_prompt`
- OpenClaw request envelopes still carry the regenerated canonical prompt package
- `continuity-state.json` remains an observability projection, not a second dispatch planner

If later work activates adapter-private same-session reuse, that later phase must restate the exact legality and invalidation rules instead of relying on this Phase 4A page to imply a live path that does not currently ship.

## OpenClaw request mapping

Map the canonical prompt package into OpenClaw request fields as follows:

- `message` = the shipped live Gateway field that carries the regenerated canonical prompt package as one root string
- `previous_response_id` = reserved continuity field; shipped Phase 4A launches leave it null because control still emits `full_prompt`
- `session_key` = provider transport identity only

The persisted prompt truth remains the full regenerated canonical prompt package for every dispatch.

## Send-mode consequences

### `full_prompt`

- sends the regenerated prompt package in one `message` field
- uses `previous_response_id: null`

### Reserved `same_session_continue` shape

- the prompt bundle and transport models still define it
- shipped Phase 4A control does not emit it
- prompt docs must not describe it as an available controller recovery path until a later owning phase ships that behavior

## Related contracts

- [OpenClaw session lifecycle](openclaw-session-lifecycle.md)
- [Watchdog and recovery contract](watchdog-and-recovery-contract.md)
- [Render and persistence](../prompt-layer/render-and-persistence.md)
