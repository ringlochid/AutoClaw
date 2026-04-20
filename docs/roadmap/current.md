# Current Roadmap Status

Last verified: 2026-04-20

This document describes the current repo state, not the desired future state.
Use it as the current-status entry point before reading historical phase plans.

## Summary

AutoClaw is on the flow-first runtime model:

- `task`
- `flow`
- `flow_revision`
- `flow_node`
- `node_attempt`
- `node_checkpoint`
- `node_sessions`
- `context_items`
- `context_manifests`

The OpenClaw bridge is materially working.
The current work is mostly ownership cleanup and product-surface cleanup, not foundational bring-up.

## Verified baseline

Current verified local baseline for this repo state:

- `make format-api` passes
- `make check-api` passes
- `make test-api` passes
- `make test-api-db` passes

## Landed behavior

These are safe to treat as current truth:

- real AutoClaw to OpenClaw dispatch through the Responses gateway path
- stable delegated session routing through `node_sessions.provider_session_key`
- manifest acknowledgement as a real pre-execution runtime gate
- approval resolution and manifest acknowledgement triggering controller advancement automatically
- bounded same-session watchdog wake with explicit escalation reasons
- typed worker-bundle, runtime-slice, timeline-slice, and audit reads
- explicit definition precedence and identity rules for packaged and filesystem-backed definitions

## Still open

These are still real follow-on concerns, but they are now narrower than the old phase docs suggest:

- policy-driven loop and governance extraction is still thinner than the target contract
- downstream evidence propagation for fully hands-off review/governance flows still needs improvement
- broader graph/operator ergonomics remain behind the runtime correctness work
- migration history remains historical debt even though the current verified baseline is green

## Historical status notes

- legacy `run` / top-level `attempt` structures are no longer live implementation truth
- older phase docs remain useful as migration history, but they are not the default source of truth for the current repo state
- the runtime-stabilization checklist is closed and preserved as a closure record in `../refactor-checklist-runtime-stabilization.md`

## Read next

- `../README.md` — repo overview
- `../../ROADMAP.md` — short public-facing roadmap
- `README.md` — roadmap index
- `00-principles.md` — invariants
- `../architecture/README.md` — reference contracts
