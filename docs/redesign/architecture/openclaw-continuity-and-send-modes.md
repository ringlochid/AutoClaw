# OpenClaw Continuity And Send Modes

Status: Target

## Purpose

This page records optional transport continuity detail below the canonical v1 session/run/abort architecture.

## Core rule

The controller always regenerates the full canonical prompt package before a dispatch.

Canonical v1 dispatch control does not depend on provider-native continuation. If transport continuity exists, it stays below the core lock as an adapter optimization only. It does not change assignment lineage, attempt lineage, Gateway `sessionKey`, Gateway `runId`, persisted prompt truth, or the controller recovery-action family.

## Canonical v1 control consequence

- `full_prompt` remains the canonical dispatch basis
- callback-safe dispatch separation may use a fresh `sessionKey` per dispatch
- any retained `same_session_continue` detail is not required for canonical v1 runtime correctness

## Optional adapter-only mapping

If an implementation retains provider-native continuity:

| Controller action         | Optional adapter transport mapping                                     |
| ------------------------- | ---------------------------------------------------------------------- |
| `redispatch_same_attempt` | `full_prompt`, or adapter-private same-session reuse when legality remains proven |
| `create_new_attempt`      | `full_prompt` only                                                     |
| `escalate`                | no dispatch                                                            |

## Optional same-session legality

If OpenClaw uses provider-native continuity, it may do so only when all of these remain true:

- the same current `node_key`
- the same current `assignment_key`
- the same current `attempt_id`
- the current dispatch is `redispatch_same_attempt`
- the session remains bound to that exact current attempt
- no structural adopt, retry, supersession, or assignment replacement occurred since the continuity basis was minted
- the prior dispatch path is not rebound, expired, or provider-signal ambiguous
- controller continuity truth remains `legal_same_session`
- the transport family and current controller configuration still allow safe reuse

This is therefore same-node, same-assignment, same-attempt transport reuse only, and it remains below the canonical v1 control contract.

## Full-prompt cases

Use `full_prompt` for:

- the first dispatch of a path
- any new attempt
- any new assignment
- any `create_new_attempt` recovery
- any `redispatch_same_attempt` where continuity is not `legal_same_session`
- any prompt-basis or transport invalidation that makes continuity unsafe

## Exact invalidators

If any of these change, `same_session_continue` is no longer legal:

- `previous_response_id` is absent or unusable
- the current node changes
- `attempt_id` changes
- `assignment_key` changes
- binding legality changes
- prompt basis changes
- provider signal becomes ambiguous
- transport fails
- operator or controller forces full prompt

When continuity is illegal, the controller either dispatches the same attempt with ordinary `full_prompt` semantics or escalates.

## OpenClaw request mapping

Map the canonical prompt package into OpenClaw request fields as follows:

- `instructions` static provider-side system and instruction text for the regenerated canonical prompt package
- `input` dynamic rendered prompt body for the regenerated canonical prompt package
- `previous_response_id` continuity pointer only when an implementation retains adapter-private continuity reuse
- `session_key` provider transport identity only

The persisted prompt truth remains the full regenerated canonical prompt package for every dispatch.

## Send-mode consequences

### `full_prompt`

- sends static provider text in `instructions`
- sends the regenerated prompt body in `input`
- uses `previous_response_id: null`

### Optional adapter-private continuity reuse

- if retained, it is legal only for `redispatch_same_attempt` on the same node, same assignment, and same attempt
- it may carry a non-null `previous_response_id`
- it keeps persisted prompt truth identical to the full regenerated canonical prompt package
- it does not widen the prompt family set or the recovery-action set
- it falls back to `full_prompt` or `escalate` when continuity legality is lost

## Related contracts

- [OpenClaw session lifecycle](openclaw-session-lifecycle.md)
- [Watchdog and recovery contract](watchdog-and-recovery-contract.md)
- [Render and persistence](../prompt-layer/render-and-persistence.md)
