# Execution guidance

Status: Reference

This implementation-control surface tells Codex how to route target-design work through pre-implementation review, phase planning, approved execution, and post-implementation review. After Phase 0, treat this pack as frozen canonical execution guidance unless an explicit canon fix is required.

For Phase 0-3, this pack assumes a one-process local-tool runtime. MQ or distributed-safe compatibility is a non-goal note until canon explicitly reopens it. Shared Phase 0 execution canon must not invent low-level effect-kind authority; exact case-sequence timing and sync/async ownership live on the Phase 2 or Phase 3 pages plus their owner docs.

## Search-first routing

These routes point to the owning phase-local pages. Phase 0 keeps the router references only; it does not restate OpenClaw worker/plugin semantics, frozen public CLI nouns, or onboarding/install teaching as parallel canon.

If you are asking:

- "Which phase should I select for this work?" -> [Phase overview](phases/overview.md)
- "Should we rewrite from scratch or hard reset first?" -> [Phase 0.5 total code hard reset baseline](phases/phase-0.5-cleanup-and-salvage-baseline.md) and [Repo hard-reset matrix](maps/repo-salvage-matrix.md)
- "What survives the hard reset?" -> [Repo hard-reset matrix](maps/repo-salvage-matrix.md)
- "How should we handle plugin salvage or rebuild during cleanup?" -> [Phase 0.5 total code hard reset baseline](phases/phase-0.5-cleanup-and-salvage-baseline.md) and [Cleanup and salvage checklist](gates/cleanup-and-salvage-checklist.md)
- "Which tests survive the hard reset?" -> [Repo hard-reset matrix](maps/repo-salvage-matrix.md) and [Hard-reset checklist](gates/cleanup-and-salvage-checklist.md)
- "What should I read first before touching code?" -> [Root execution contract](../../../AGENTS.md), then [Use this pack for implementation](how-to/use-this-pack-for-implementation.md)
- "Which files or surfaces am I allowed to touch in this phase?" -> [Implementation file lock map](maps/file-priority-map.md) and the current phase page
- "Should I review docs readiness before coding?" -> [Execution router](#execution-router) and [Phase prompts](gates/phase-implementation-prompts.md)
- "I am in Codex Plan Mode and need the reusable phase-plan prompt." -> [Phase prompts](gates/phase-implementation-prompts.md) and the selected current phase page
- "I need the phase-local goal, deliverables, or work packages." -> the selected current phase page plus the [implementation file lock map](maps/file-priority-map.md)
- "Where do OpenClaw gateway, session, bootstrap, continuity, or exact Gateway RPC subset questions land?" -> [Phase 4A](phases/phase-4a-openclaw-gateway-session-and-continuity.md), [OpenClaw Gateway RPC subset](../../design/v1/architecture/openclaw-gateway-rpc-subset.md), and [OpenClaw worker and gateway contract](../../design/v1/architecture/openclaw-worker-and-gateway-contract.md)
- "Where do OpenClaw plugin/MCP tool-lane or operator-safe automation questions land?" -> [Phase 4B](phases/phase-4b-watchdog-operator-plugin-and-support-state.md), [MCP, plugin, and CLI boundary](../../design/v1/interfaces/mcp-plugin-and-cli-boundary.md), and [Plugin tool reference](../../design/v1/interfaces/plugin-tool-reference.md)
- "Where do session-authority simplification, callback-binding removal, unified node/callback validation, or parent/root-only same-session redispatch implementation land?" -> [Phase 4.5](phases/phase-4.5-session-authority-simplification-and-mcp-runtime-continuity-cleanup.md), [Runtime records and lifecycle](../../design/v1/architecture/runtime-records-and-lifecycle.md), [OpenClaw session lifecycle](../../design/v1/architecture/openclaw-session-lifecycle.md), and [MCP, plugin, and CLI boundary](../../design/v1/interfaces/mcp-plugin-and-cli-boundary.md)
- "Where is the target public root CLI noun family, including deferred `autoclaw openclaw ...`, `autoclaw definitions import ...`, and `autoclaw task-compose start ...` work?" -> [Phase 5A](phases/phase-5a-definition-ingest-api-and-cli.md) and [CLI surface and operator workflows](../../design/v1/interfaces/cli-surface-and-operator-workflows.md)
- "Where do install, onboarding, bootstrap teaching, and docs cutover questions land?" -> [Phase 5B](phases/phase-5b-packaging-release-and-docs-cutover.md) and [Install and onboard](../../design/v1/how-to/install-and-onboard.md)
- "Where do stale compose, env-example, service-template, dormant placeholder, or local-artifact cleanup questions land before the standards refactor?" -> [Phase 5.5](phases/phase-5.5-repo-hygiene-and-active-surface-freeze.md), [Release and install strategy](../../design/v1/interfaces/release-and-install-strategy.md), and [Run the current Docker and Postgres verification lane](../../current/v1/operations/run-docker-postgres-verification.md)
- "Where do repo-wide source layout, readability, naming, import-gate, audit-tooling, or canonical package-migration refactors land after the product behavior already works?" -> [Phase 6](phases/phase-6-source-structure-boundaries-and-naming-convergence.md), [Source layout standard](../../../.agents/standards/structure/source-layout.md), [Readability and refactor standard](../../../.agents/standards/code/readability-refactor.md), and [Naming standard](../../../.agents/standards/code/naming.md)
- "Where do phase-numbered test tree cleanup, cross-lane helper cleanup, or proof-lane convergence questions land?" -> [Phase 7](phases/phase-7-test-structure-and-proof-convergence.md), [Test structure standard](../../../.agents/standards/structure/test-structure.md), and [Progressive e2e workflow lanes](phases/progressive-e2e-workflow-lanes.md)
- "Where do local-tool-first timing, inline-vs-after-return behavior, or sync/async ownership live?" -> [Phase 2](phases/phase-2-prompt-manifest-artifact-bootstrap.md), [Phase 3](phases/phase-3-runtime-parent-review-and-replan.md), and [Design-to-code landing map](maps/design-code-landing-map.md)
- "I finished implementation and need the post-review flow." -> [Verification prompts](gates/verification-prompts.md)
- "What gates do I need to pass?" -> [Execution gates](gates/README.md)
- "What do I read before implementing?" -> [Use this pack for implementation](how-to/use-this-pack-for-implementation.md)
- "How do I cover secondary design pages, ADRs, how-to guides, tutorials, or historical findings?" -> [Design-to-code landing map](maps/design-code-landing-map.md), [Use this pack for implementation](how-to/use-this-pack-for-implementation.md), and the selected current phase page
- "How do I answer an implementation question without guessing?" -> [Use this pack for implementation](how-to/use-this-pack-for-implementation.md) and [Docs answer-sourcing checklist](gates/docs-answer-sourcing-checklist.md)
- "Where is the design-to-code landing coverage map?" -> [Design-to-code landing map](maps/design-code-landing-map.md)
- "Where are exhaustive API request/response details?" -> [Phase 5A](phases/phase-5a-definition-ingest-api-and-cli.md) and [API schema appendix](../../design/v1/interfaces/api-schema-appendix.md)
- "Where are the exact artifact/ref, worker-context, release, or internal replan contracts?" -> [Phase 3](phases/phase-3-runtime-parent-review-and-replan.md), [Artifact ref and storage contract](../../design/v1/architecture/artifact-ref-and-storage-contract.md), [Worker context contract](../../design/v1/architecture/worker-context-contract.md), [Runtime boundary and controller loop contract](../../design/v1/architecture/runtime-boundary-and-controller-loop-contract.md), [Parent/root release and closure](../../design/v1/workflows/parent-root-release-and-closure.md), [Runtime structural replan](../../design/v1/workflows/runtime-structural-replan.md), [Workflow schema appendix](../../design/v1/workflows/workflow-schema-appendix.md), and [API schema appendix](../../design/v1/interfaces/api-schema-appendix.md)
- "Where is the frozen `autoclaw definitions import ...` contract?" -> [Phase 5A](phases/phase-5a-definition-ingest-api-and-cli.md) and [Definition ingest and task-start file contract](../../design/v1/interfaces/definition-ingest-and-upload-contract.md)
- "Where are exhaustive prompt section/root/continuation rules and the shipped prompt-source split?" -> [Phase 2](phases/phase-2-prompt-manifest-artifact-bootstrap.md), [Phase 4A](phases/phase-4a-openclaw-gateway-session-and-continuity.md), and [Prompt resource and usage appendix](../../design/v1/prompt-layer/prompt-resource-usage-appendix.md)
- "Where are the runtime-generated assignment, checkpoint, task-root, and surfaced-artifact contracts?" -> [Phase 2](phases/phase-2-prompt-manifest-artifact-bootstrap.md), [Manifest contract](../../design/v1/architecture/manifest-contract.md), [Worker context contract](../../design/v1/architecture/worker-context-contract.md), [Task root layout and generated files](../../design/v1/architecture/task-root-layout-and-generated-files.md), [Artifact ref and storage contract](../../design/v1/architecture/artifact-ref-and-storage-contract.md), and [Prompt contract](../../design/v1/prompt-layer/contract.md)
- "How does current map to target?" -> [Current-to-target mapping](maps/current-to-target-mapping.md)
- "How do I migrate current `skill_refs` and skill-registry surfaces?" -> [Current-to-target mapping](maps/current-to-target-mapping.md), [Phase 1 authoring and compiler rewrite](phases/phase-1-authoring-and-compiler-rewrite.md), and [Phase 5A definition ingest, API, and CLI](phases/phase-5a-definition-ingest-api-and-cli.md)
- "Where do the plugin/operator doc locks and `request_approval` removal land?" -> [Phase 4B watchdog, operator, plugin, and support-state lanes](phases/phase-4b-watchdog-operator-plugin-and-support-state.md)
- "Where do package/install/reset and docs cutover rules land?" -> [Phase 5B packaging, release, and docs cutover](phases/phase-5b-packaging-release-and-docs-cutover.md) and [Install and onboard](../../design/v1/how-to/install-and-onboard.md)
- "Which files or surfaces matter first?" -> [Implementation file lock map](maps/file-priority-map.md)

## Start here

- [Root execution contract](../../../AGENTS.md)
- [Coding standards](../../../STYLE.md)
- [Phase overview](phases/overview.md)
- [Phase 0.5 total code hard reset baseline](phases/phase-0.5-cleanup-and-salvage-baseline.md)
- [Use this pack for implementation](how-to/use-this-pack-for-implementation.md)

## Execution record home

- [Plans home](plans/README.md) stores approved phase plans and WBS artifacts.
- [Evidence home](evidence/README.md) stores executed validator, test, gate, reset, and smoke evidence.
- [Reviews home](reviews/README.md) stores mandatory review outputs, closeout reviews, and explicit exceptions.

Use these folders as record homes only. The phase-local contract still lives on the current phase page plus the implementation file lock map.

The shared record-home READMEs and templates remain Phase 0-owned execution canon. Historical cross-phase or aggregate summary artifacts are also Phase 0-owned only while they still provide unique replacement-routing value; once the phase-scoped replacements and router pages are sufficient, prune the historical ballast instead of keeping it as duplicate context.

## Authoritative artifact rule

Use phase-scoped records for authoritative closeout:

- each approved plan, executed evidence artifact, and mandatory review used to close work must name exactly one selected phase and therefore one current phase page
- the selected phase owns only the phase-scoped artifacts that document that selected phase; shared record-home routers/templates and any retained historical summary artifacts stay Phase 0-owned unless the work is an explicit canon fix
- cross-phase or aggregate records may exist only as historical summaries, do not satisfy mandatory-review, reset-gate, or phase-done closure requirements, and should be deleted once they no longer add unique routing value beyond the authoritative phase-scoped chain

## Parseable artifact grammar

Use this exact top-of-file block, immediately after the `Status:` line and before any `##` heading, in approved plans, executed evidence artifacts, mandatory reviews, and any cross-phase or aggregate summary artifacts stored under the execution record homes:

```text
selected phase: ...
current phase page: ...
selected work packages: ...
summary-only: no|yes
delegated slices: none|listed
slice id: ...
slice type: edit|review-only
owned surfaces: ...
touched surfaces: ...
```

Rules:

- preserve the exact line order shown above for the five required header lines
- `selected phase:` must name exactly one selected phase on authoritative phase-scoped artifacts
- `current phase page:` must name exactly one repo-relative phase page path on authoritative phase-scoped artifacts
- `selected work packages:` must list only work-package ids defined on that selected phase page on authoritative phase-scoped artifacts
- `summary-only: no` is the authoritative phase-scoped sentinel
- `summary-only: yes` is the historical-summary sentinel
- when `delegated slices:` is `listed`, append one contiguous four-line slice block per delegated slice in the exact order `slice id:`, `slice type:`, `owned surfaces:`, `touched surfaces:`
- cross-phase or aggregate historical summaries that do not map to one selected phase page must use `selected phase: none`, `current phase page: none`, and `selected work packages: none`
- historical artifacts that still belong to one selected phase may keep that selected phase, current phase page, and selected work packages, but must still use `summary-only: yes`

This top-level block is the authoritative execution-record grammar. If a later narrative section such as `## Slice identity` repeats any of these fields, that narrative copy is descriptive only and cannot replace a missing, reordered, or malformed top-of-file block.

Rules:

- authoritative phase-scoped closure artifacts must use `summary-only: no`
- historical cross-phase or aggregate artifacts must use `summary-only: yes` and cannot be used as closure authority
- historical summary artifacts must include truthful `## Authoritative replacements` links that point only to `summary-only: no` replacement artifacts
- prose such as "historical summary only" or "not authoritative phase closure evidence" does not substitute for `summary-only: yes`
- `selected work packages:` must stay inside the ordered work packages defined on the selected phase page
- `touched surfaces:` may be `none` only for `review-only` slices that returned no edits

## Phase selection

The execution pack does not keep a separate repo-global active-phase marker.

For each bounded target-design work package:

1. use pre-implementation review plus [Phase overview](phases/overview.md) to select the phase that owns the next blocking design delta
2. prefer the earliest phase whose target contract and locked surfaces are still required for that blocker
3. use [Phase 0.5 total code hard reset baseline](phases/phase-0.5-cleanup-and-salvage-baseline.md) before Phase 1 when stale repo shape, reset baseline ambiguity, stale tests, or plugin-boundary drift still dominate
4. record exactly one selected phase explicitly in the approved plan
5. use that same single selected phase for any evidence or review artifact that claims phase closure

In the rest of this pack, `current phase page` means the selected phase page for the approved work package.

## Phase 0-3 local-tool-first rule

- treat Phase 0-3 as one-process local-tool-first execution
- MQ or distributed-safe compatibility is a non-goal note until canon explicitly reopens it
- shared Phase 0 canon must not define low-level effect-kind taxonomies as if they were the live timing contract
- Phase 2 owns the prompt/bootstrap/materialization case sequences, including which generated read surfaces must exist before return versus after return
- Phase 3 owns the control-state, boundary-drain, and replacement-dispatch case sequences, including the sync/async split for those flows

## Fast path

1. Read [Root execution contract](../../../AGENTS.md).
2. Read [Coding standards](../../../STYLE.md).
3. Run pre-implementation review and select the current phase.
4. Read the current phase page and the implementation file lock map together.
5. Read the primary design pages, required supporting design reads, required current-contrast pages, and required examples or diagrams named by that phase page.
6. Read any named appendix owners when exact API/schema/prompt detail matters.
7. Use the [Design-to-code landing map](maps/design-code-landing-map.md) when the phase touches target contract coverage, supporting live references, examples, tutorials, or proof gates.
8. Build the approved phase plan for that one selected phase, including the subagents decision and validation loop, and record it under [Plans home](plans/README.md).
9. Record phase-scoped validator, test, and gate output under [Evidence home](evidence/README.md) and any mandatory review or exception writeup under [Reviews home](reviews/README.md).
10. Execute.

## Execution router

1. Read [Root execution contract](../../../AGENTS.md) and [Coding standards](../../../STYLE.md).
2. Run the pre-implementation review flow in [Phase prompts](gates/phase-implementation-prompts.md).
3. Use that review to select the current phase and name the current phase page.
4. If the review finds a docs gap, patch canon before coding.
5. If the review says code work is ready, read the current phase page plus the [implementation file lock map](maps/file-priority-map.md).
6. Read any required supporting design pages, current-contrast pages, examples, and diagrams named by the current phase page before planning implementation.
7. If the blocker depends on exact case-sequence timing or sync/async ownership, route that detail to the owning Phase 2 or Phase 3 page before planning.
8. Enter plan-mode phase planning and build the approved WBS for the selected phase, including the subagents decision, wave plan, validation checkpoints, and any required DB or package verification lanes. Record the approved phase-scoped artifact under [Plans home](plans/README.md).
9. After plan approval, execute using default Codex behavior plus `AGENTS.md`, `STYLE.md`, the current phase page, the implementation file lock map, and the approved plan.
10. Run post-implementation review, gates, reset when applicable, and phase-done checks before claiming completion.

## Keywords

- implementation pack
- phase overview
- cleanup phase
- hard-reset matrix
- plugin rebuild
- stale contract tests
- implementation fast path
- current-to-target mapping
- implementation file lock map
- definitions import
- AssignChildPayload and CheckpointWrite
- packet and ref contract
- appendix owners
- plugin doc lock
- request_approval removal
- operator trace naming
- phase 4a
- phase 4b
- phase 5a
- phase 5b
- phase 5.5
- phase 6
- phase 7

## Supporting maps

- [Current-to-target mapping](maps/current-to-target-mapping.md)
- [Current schema, route, and plugin migration appendix](maps/current-schema-route-and-plugin-migration-appendix.md)
- [Design-to-code landing map](maps/design-code-landing-map.md)
- [Implementation file lock map](maps/file-priority-map.md)
- [Repo hard-reset matrix](maps/repo-salvage-matrix.md)
- [Execution how-to guides](how-to/use-this-pack-for-implementation.md)

## Implementation loop

1. Start with [Use this pack for implementation](how-to/use-this-pack-for-implementation.md).
2. Run the pre-implementation review prompt to confirm the selected phase, docs readiness, confidence, and blocking criteria.
3. Read the current phase page plus the implementation file lock map before planning implementation work.
4. Read every required supporting design page, required current-contrast page, required example, and required diagram named by the current phase page.
5. If the blocker depends on exact case-sequence timing or sync/async ownership, route that detail to the owning Phase 2 or Phase 3 page before planning.
6. Use the [Design-to-code landing map](maps/design-code-landing-map.md) to confirm which target owners, supporting live references, examples, tutorials, and proof gates must land in code for the selected phase.
7. Use the phase planning prompt while Codex is in Plan Mode to build the WBS, locked surfaces, dependencies, tests, subagents strategy, wave plan, and exit evidence, and record the approved phase-scoped result under [Plans home](plans/README.md).
8. Execute only after the plan is approved.
9. When you change app-owned shipped prompt assets, canonical prompt docs, `prompt-catalog.yaml`, or generated prompt pages, run `python -m scripts.docs.prompt_catalog.cli validate` from the workspace root. If prompt assets, prompt-catalog, or other prompt-generation inputs changed, run `python -m scripts.docs.prompt_catalog.cli generate` first. If the slice also touched `scripts/docs/*`, run `ruff check scripts/docs` and `mypy scripts/docs`.
10. Use [Verification prompts](gates/verification-prompts.md) for post-implementation review before claiming phase completion, and record execution proof under [Evidence home](evidence/README.md) plus review output under [Reviews home](reviews/README.md).

## Surface rule

Use this surface for implementation order, gates, and execution evidence.

Do not use it as the canonical target contract or the source of shipped current behavior.
