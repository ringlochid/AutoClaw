# 02 — Phase 2: Registry and Compiler

## Goal

Turn definition files and published registry entries into deterministic compiled plans.

## In Scope

- definition import/export
- draft/validate/publish flow
- version pinning rules
- compiler v0 parse/resolve/normalize/validate/lower pipeline
- cycle detection for invalid dependency graphs
- compiled plan hash generation

## Out of Scope

- optimizer-heavy compile passes
- advanced hierarchy-specific compile tricks
- speculative AI compile decisions

## Deliverables

- registry services for roles/policies/workflows/skill refs
- publish validation path
- deterministic compiler function(s)
- compiled plan persistence

## Data Model Changes

- tighten registry version schemas
- finalize compiled plan tables
- add revision/hash fields where needed

## API / Runtime Changes

- registry read endpoints
- compile endpoint or internal compile service
- run creation should use compiled plans instead of raw definitions

## Tests / Verification

- same input definitions produce the same plan hash
- invalid refs fail compile cleanly
- invalid cycles fail compile cleanly
- published versions are pinned per run

## Exit Criteria

Phase 2 is done when a published workflow version deterministically compiles into one canonical compiled plan revision.

## Deferred Follow-ups

- partial recompile
- complex patch operation set

## Risks

- registry logic and compiler logic coupling too tightly
- source definition flexibility outrunning validation rigor
