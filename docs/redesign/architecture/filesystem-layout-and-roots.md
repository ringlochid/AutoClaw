# Filesystem layout and roots

Status: Target

This page defines the canonical v1 task-root roots and what each root means.

## Core rule

The task root is filesystem-first and path-first.

Agents read and write local task-root files. Controller-generated runtime projections and monitoring files live under `_runtime/`. Surfaced refs are path-only in v1.

## Canonical task roots

- `workspace/`
- `context/`
- `outputs/`
- `tmp/`
- `_runtime/`

`workspace/` and `context/` are the human-authored task roots.

`outputs/`, `tmp/`, and `_runtime/` are controller-owned runtime roots.

Trusted OpenClaw session-binding proof is not part of the task root. Callback authorization material remains transport/runtime-private and does not belong in surfaced task-root context.

## Canonical task root tree

```text
<task-root>/
  workspace/
  context/
    criteria/
    wiki/
    ...
  outputs/
    artifacts/
  tmp/
    transfers/
  _runtime/
    workflow-manifest.json
    workflow-manifest.md
    attempts/
      <attempt_id>/
        assignment.json
        assignment.md
        latest-checkpoint.json
        latest-checkpoint.md
        artifact-index.json
        transient-index.json
    dispatch/
      <dispatch_id>/
        delivery-state.json
        continuity-state.json
        watchdog-state.json
        provider-events.ndjson
```

## Root meanings

| Root                 | Exact meaning                                                          |
| -------------------- | ---------------------------------------------------------------------- |
| `workspace/`         | mutable work in progress for the current assignment                    |
| `context/`           | durable task supporting material and curated source/reference material |
| `context/criteria/`  | explicit criteria files                                                |
| `context/wiki/`      | curated task-memory pages                                              |
| `outputs/artifacts/` | durable published outputs and evidence                                 |
| `tmp/transfers/`     | optional transient carryover                                           |
| `_runtime/`          | controller-generated runtime projections and monitoring                |

## Context distinction

- `context/wiki/` is the curated task-memory surface for synthesized task pages and reusable notes.
- `context/criteria/` holds explicit criteria files.
- Other curated files under `context/` are source/reference material such as user docs, PDFs, screenshots, and notes.

Nodes may search `context/wiki/` and other curated files under `context/` directly in v1. Task memory is guided by assignment or checkpoint `task_memory_search_hints`; it is not automatically a must-read consume.

## Common placement examples

| If you have...                                                    | Put it here                                  | Why                                                       |
| ----------------------------------------------------------------- | -------------------------------------------- | --------------------------------------------------------- |
| a draft code change or scratch script for the current assignment  | `workspace/`                                 | mutable work in progress                                  |
| explicit acceptance rules for a node                              | `context/criteria/`                          | durable criteria the assignment or parent review may cite |
| a reusable task-memory page summarizing earlier discoveries       | `context/wiki/`                              | curated synthesized memory, searchable later              |
| a user PDF, screenshot, or note the task may need later           | `context/`                                   | durable source/reference material                         |
| a durable final report or produced evidence file                  | `outputs/artifacts/<owner_node_key>/<slot>/` | immutable published output with current pointer           |
| an optional carryover note that should not become durable truth   | `tmp/transfers/`                             | bounded transient handoff                                 |
| workflow manifest, assignment, checkpoint, or watchdog projection | `_runtime/`                                  | controller-generated projection, not ordinary task work   |

## Path-only surfaced refs

V1 surfaced refs are path-only.

Rules:

- Runtime surfaces local task-root paths, not remote URLs, in assignments, checkpoints, manifests, artifact refs, and transient refs.
- If an external resource is needed, runtime must first localize or mirror it into the task root and then surface the localized `path`.
- Agents must not infer meaning from filenames alone. Durable surfaced refs should also carry descriptions from authored workflow metadata.

## Write and read rule

- `workspace/` is the ordinary mutable work area for the current assignment.
- `context/` is read-first supporting material, not an ordinary scratch area.
- Durable publication goes to `outputs/artifacts/`.
- Optional transient carryover goes to `tmp/transfers/`.
- `_runtime/` is controller-generated only. It is a readable projection and monitoring surface, not an ordinary direct-write target for nodes.
- trusted session-binding proof, callback env var names, and other private write-authority plumbing are not part of ordinary worker-readable filesystem context

## Runtime projection rule

- `_runtime/workflow-manifest.*` is the stable whole-workflow projection.
- `_runtime/attempts/<attempt_id>/assignment.*` and `latest-checkpoint.*` are deterministic controller-generated projections for that attempt.
- `_runtime/dispatch/<dispatch_id>/delivery-state.json`, `continuity-state.json`, `watchdog-state.json`, and `provider-events.ndjson` are observability projections only.
- `_runtime/dispatch/<dispatch_id>/prompt.md` and `prompt-request.json` are
  persisted dispatch prompt artifacts, not assignment/checkpoint currentness
  owners.
- If generated files and controller/DB state disagree, controller/DB state wins.

Concrete example:

- a screenshot downloaded from outside the task must first be localized to something like `C:/tasks/task_2026_0042/context/user-reported-auth-refresh.png`
- a durable review report should end up at `C:/tasks/task_2026_0042/outputs/artifacts/review_findings/findings_report/findings_report.v02.md`
- a transient repro note should end up at `C:/tasks/task_2026_0042/tmp/transfers/repro-notes.md`

## Related contracts

- `task-root-layout-and-generated-files.md`
- `manifest-contract.md`
- `artifact-ref-and-storage-contract.md`
- `worker-context-contract.md`
