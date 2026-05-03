# Parent/root planning surface

Status: Target

This page explains the live parent/root planning surface without relying on assembled gate bundles.

```mermaid
flowchart TD
    A["current workflow manifest"] --> P["parent/root open dispatch"]
    B["current assignment"] --> P
    C["child latest checkpoints"] --> P
    D["referenced durable artifacts"] --> P
    E["current criteria"] --> P
    F["optional transient refs"] --> P
    G["task-memory search hints and curated docs"] --> P
    H["definition registry reads for role/policy"] --> P
    P --> Q["assign_child"]
    P --> R["add_child / update_child / remove_child"]
    P --> S["release_green / release_blocked"]
    P --> T["yield after one staged continuation outcome"]
```

## Why this surface is enough

- the manifest provides whole-workflow structure and current direct-child visibility
- child checkpoints provide summary-first history and next-step handover
- durable artifacts provide drilldown evidence
- criteria provide the current acceptance contract
- registry list/search plus current detail reads provide legal role/policy discovery before structural edits

There is no separate assembled planning-snapshot family in v1.

## Worked planning example

Assume the current parent/root has just been redispatched after `implement_change` finished. The surfaced evidence now includes:

- checkpoint summary: "Patch implemented; verification report still lacks one retry-path case."
- artifact refs:
  - `change_patch` version `2`
  - `verification_report` version `3`
- current subtree criteria

The planning surface is enough to choose the next action:

1. the checkpoint summary says what changed
2. the artifact refs show exactly where to drill down
3. the current criteria explain whether the missing retry-path case still matters
4. parent/root can now choose either:
   - `assign_child` for follow-up engineering work
   - `add_child` for a new QA worker if the current direct-child set is wrong
   - `release_green` only if the evidence and criteria already justify closure

No hidden gate summary, bundle, or callback envelope is needed to make that decision.

## Planning rule

Parent/root should:

- start from checkpoint summaries and current criteria
- drill into referenced artifacts only when summaries are insufficient
- use current role/policy discovery only; do not plan from revision history as a normal parent/root input
- use structural edits only on current direct children
- stage exactly one continuation outcome before `yield`
- explain later-sensitive decisions in checkpoints rather than hidden controller prose

## What the parent/root does not need

The live planning surface does not require historical gate-era callback machinery or packet/bundle-first planning surfaces.
