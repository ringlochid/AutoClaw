# Current Roadmap Status

## Status summary

The **target docs are now coherent**, but the **codebase is still on the legacy runtime model**.
This file should stay brutally honest about that difference.

## Target contract (docs)

The architecture now treats this as authoritative:

- `task`
- `flow`
- `flow_revision`
- `flow_node`
- `node_attempt`
- `node_checkpoint`
- `node_sessions`
- `context_items`
- `context_manifests`

## Current code still does this

Current implementation still contains legacy structures and behavior such as:

- `runs`
- top-level `attempts`
- `flows.attempt_id`
- `approvals.run_id`
- `approvals.attempt_id`
- `current_attempt_number`
- run-scoped routes / services
- `flow_nodes.iteration_index`-style legacy execution modeling
- checkpoints not yet fully centered on `node_attempt` as the canonical history unit

## Meaning for roadmap writing

It is safe to write real phase plans in this folder **as migration plans**.
It is not safe to write them as if the runtime reset has already landed.

## Current focus

- finish the roadmap cleanup around the target contract
- write the phase-3 runtime migration plan against the real legacy codebase
- keep roadmap text aligned with `docs/architecture/**`, not with temporary legacy naming

## Open implementation decisions still to freeze

- after approval/context acknowledgement, resume the same blocked attempt or create a new attempt?
- represent context acknowledgement only in manifest metadata, or also as a first-class checkpoint/event?

## Why this reset matters

This gives a cleaner model where:

- `flow` is the whole execution container
- `flow_revision` owns executable graph snapshots
- `node_attempt` is the execution container for one specific node
- history and provenance are queryable without transcript inspection
- shared context is published and projected through explicit runtime metadata, not hidden prompt residue
