# Source inputs and unsafe material

Status: Reference

This page records what was safe to absorb and what was unsafe to merge directly.

## Safe to absorb selectively

- validated current fact summaries from `legacy-packs/merge_v2/current/`
- current-doc conventions such as `Last verified`
- high-level trust-lane and packaging summaries from current repo docs once rechecked against code

## Unsafe to merge directly

- `autoclaw-main/docs/flows/06-max-complexity-workflow.md`
- `autoclaw-main/docs/flows/06b-max-complexity-workflow-full.md`
- `autoclaw-main/docs/decisions/ADR-0003-parent-supervisor-main-loop-kernel.md`
- roadmap pages that act like current truth rather than history
- any doc that still teaches `can_spawn_children` as the parenthood rule

## Why this matters

The current repo docs still mix:

- current truth
- historical phase notes
- target redesign semantics

`..` was therefore re-authored from validated facts and redesign contracts instead of being assembled by wholesale file moves.
