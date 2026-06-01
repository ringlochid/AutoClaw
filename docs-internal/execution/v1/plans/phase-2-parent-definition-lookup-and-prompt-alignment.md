# Phase 2 Parent Definition Lookup And Prompt Alignment Plan

Status: Reference

selected phase: Phase 2
current phase page: docs-internal/execution/v1/phases/phase-2-prompt-manifest-artifact-bootstrap.md
selected work packages: P2-WP1
summary-only: no
delegated slices: listed
slice id: phase2-prompt-canon-and-generated-examples
slice type: edit
owned surfaces: docs-internal/design/v1/prompt-layer/**, apps/api/app/runtime/prompt/**, apps/api/tests/unit/runtime_prompt_rendering/**
touched surfaces: docs-internal/design/v1/prompt-layer/**, apps/api/app/runtime/prompt/**, apps/api/tests/unit/runtime_prompt_rendering/test_dispatch.py
slice id: phase2-review
slice type: review-only
owned surfaces: docs-internal/design/v1/prompt-layer/**, apps/api/app/runtime/prompt/**, apps/api/tests/unit/runtime_prompt_rendering/**, docs-internal/execution/v1/plans/phase-2-parent-definition-lookup-and-prompt-alignment.md, docs-internal/execution/v1/evidence/phase-2-parent-definition-lookup-and-prompt-alignment.md, docs-internal/execution/v1/reviews/phase-2-parent-definition-lookup-and-prompt-alignment.md
touched surfaces: none

## Goal

Align the prompt-layer canon and live runtime prompt output so parent/root structural edits are taught consistently:

- palette-first discovery remains the default
- current-only `search_definitions` / `get_definition` is a legal read-only escalation path when surfaced
- revision history remains operator-only

## Owned And Allowed Surfaces

- owned: prompt-layer docs, prompt assets, prompt rendering code, prompt examples, prompt tests
- allowed collateral: generated prompt examples and prompt-catalog validation surfaces

## Ordered Work

1. Patch prompt-layer owner docs and examples before code.
2. Update the exact parent legality block and the live runtime prompt renderers.
3. Update prompt-rendering tests to assert both presence of the new lookup guidance and absence of the stale palette-only wording.
4. Regenerate and validate prompt generated examples.

## Validation

- `python -m scripts.docs.prompt_catalog.cli generate`
- `python -m scripts.docs.prompt_catalog.cli validate`
- focused unit prompt-rendering tests

## Delegated Slice Briefs

### phase2-prompt-canon-and-generated-examples

- do-not-edit surfaces:
  - `docs-internal/design/v1/interfaces/**`
  - `apps/api/autoclaw/openclaw/**`
  - execution evidence/reviews
- required reads:
  - all Phase 2 prompt-layer owner docs, examples, and appendices
  - the updated parent/root planning and definition contract docs
- expected outputs:
  - prompt docs, exact prompt assets, generated examples, and runtime prompt output aligned
- required validators:
  - prompt catalog generate/validate
  - focused prompt-rendering tests
- dependencies:
  - prompt legality contract chosen
- parent-owned decisions:
  - exact parent/root legality wording
  - whether current-only lookup stays read-only and current-only
- evidence to return:
  - changed file list
  - focused validator/test outcomes
- stop conditions:
  - if route/API/MCP or execution-artifact changes are required

### phase2-review

- do-not-edit surfaces:
  - all repo-tracked files
- required reads:
  - the Phase 2 page, plan, evidence, and touched prompt-layer docs, assets, code, and tests
- expected outputs:
  - strict review verdict and closure-draft content only
- required validators:
  - none beyond read-only inspection and any non-mutating proof checks
- dependencies:
  - edit slice integrated
- parent-owned decisions:
  - none; this slice reports review truth only
- evidence to return:
  - exact findings or pass verdict
  - draft-ready review text
- stop conditions:
  - if any repo edit seems necessary

## Exit Evidence

- prompt docs, exact prompt assets, rendered examples, and live prompt output agree on the same parent/root legality story
- no revision-history wording leaks into dispatched parent/root planning
