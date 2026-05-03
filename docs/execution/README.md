# Execution guidance

Status: Reference

This implementation-control surface tells Codex how to route redesign work through pre-implementation review, phase planning, approved execution, and post-implementation review. After Phase 0, treat this pack as frozen canonical execution guidance unless an explicit canon fix is required.

## Search-first routing

If you are asking:

- "Which phase should I select for this work?" -> [Phase overview](phases/overview.md)
- "Should we rewrite from scratch or salvage first?" -> [Phase 0.5 cleanup and salvage baseline](phases/phase-0.5-cleanup-and-salvage-baseline.md) and [Repo salvage matrix](maps/repo-salvage-matrix.md)
- "What do we keep vs delete?" -> [Repo salvage matrix](maps/repo-salvage-matrix.md)
- "How should we handle the plugin?" -> [Phase 0.5 cleanup and salvage baseline](phases/phase-0.5-cleanup-and-salvage-baseline.md) and [Cleanup and salvage checklist](gates/cleanup-and-salvage-checklist.md)
- "Which tests are salvageable?" -> [Repo salvage matrix](maps/repo-salvage-matrix.md) and [Cleanup and salvage checklist](gates/cleanup-and-salvage-checklist.md)
- "What should I read first before touching code?" -> [Root execution contract](../../AGENTS.md), then [Use this pack for implementation](how-to/use-this-pack-for-implementation.md)
- "Which files or surfaces am I allowed to touch in this phase?" -> [Implementation file lock map](maps/file-priority-map.md) and the current phase page
- "Should I review docs readiness before coding?" -> [Execution router](#execution-router) and [Phase prompts](gates/phase-implementation-prompts.md)
- "I am in Codex Plan Mode and need the reusable phase-plan prompt." -> [Phase prompts](gates/phase-implementation-prompts.md) and the selected current phase page
- "I need the phase-local goal, deliverables, or work packages." -> the selected current phase page plus the [implementation file lock map](maps/file-priority-map.md)
- "I finished implementation and need the post-review flow." -> [Verification prompts](gates/verification-prompts.md)
- "What gates do I need to pass?" -> [Execution gates](gates/README.md)
- "What do I read before implementing?" -> [Use this pack for implementation](how-to/use-this-pack-for-implementation.md)
- "How do I answer an implementation question without guessing?" -> [Use this pack for implementation](how-to/use-this-pack-for-implementation.md) and [Docs answer-sourcing checklist](gates/docs-answer-sourcing-checklist.md)
- "Where are exhaustive API request/response details?" -> [Phase 5A](phases/phase-5a-definition-ingest-api-and-cli.md) and [API schema appendix](../redesign/interfaces/api-schema-appendix.md)
- "Where are the exact artifact/ref, worker-context, release, or internal replan contracts?" -> [Phase 3](phases/phase-3-runtime-parent-review-and-replan.md), [Artifact ref and storage contract](../redesign/architecture/artifact-ref-and-storage-contract.md), [Worker context contract](../redesign/architecture/worker-context-contract.md), [Runtime boundary and controller loop contract](../redesign/architecture/runtime-boundary-and-controller-loop-contract.md), [Parent/root release and closure](../redesign/workflows/parent-root-release-and-closure.md), [Runtime structural replan](../redesign/workflows/runtime-structural-replan.md), [Workflow schema appendix](../redesign/workflows/workflow-schema-appendix.md), and [API schema appendix](../redesign/interfaces/api-schema-appendix.md)
- "Where is the frozen `autoclaw definitions import ...` contract?" -> [Phase 5A](phases/phase-5a-definition-ingest-api-and-cli.md) and [Definition ingest and task-start file contract](../redesign/interfaces/definition-ingest-and-upload-contract.md)
- "Where are exhaustive prompt section/root/continuation rules?" -> [Phase 2](phases/phase-2-prompt-manifest-artifact-bootstrap.md), [Phase 4A](phases/phase-4a-openclaw-gateway-session-and-continuity.md), and [Prompt resource and usage appendix](../redesign/prompt-layer/prompt-resource-usage-appendix.md)
- "Where are the runtime-generated assignment, checkpoint, task-root, and surfaced-artifact contracts?" -> [Phase 2](phases/phase-2-prompt-manifest-artifact-bootstrap.md), [Manifest contract](../redesign/architecture/manifest-contract.md), [Worker context contract](../redesign/architecture/worker-context-contract.md), [Task root layout and generated files](../redesign/architecture/task-root-layout-and-generated-files.md), [Artifact ref and storage contract](../redesign/architecture/artifact-ref-and-storage-contract.md), and [Prompt contract](../redesign/prompt-layer/contract.md)
- "How does current map to target?" -> [Current-to-target mapping](maps/current-to-target-mapping.md)
- "How do I migrate current `skill_refs` and skill-registry surfaces?" -> [Current-to-target mapping](maps/current-to-target-mapping.md), [Phase 1 authoring and compiler rewrite](phases/phase-1-authoring-and-compiler-rewrite.md), and [Phase 5A definition ingest, API, and CLI](phases/phase-5a-definition-ingest-api-and-cli.md)
- "Where do the plugin/operator doc locks and `request_approval` removal land?" -> [Phase 4B watchdog, operator, plugin, and support-state lanes](phases/phase-4b-watchdog-operator-plugin-and-support-state.md)
- "Where do package/install/reset and docs cutover rules land?" -> [Phase 5B packaging, release, and docs cutover](phases/phase-5b-packaging-release-and-docs-cutover.md)
- "Which files or surfaces matter first?" -> [Implementation file lock map](maps/file-priority-map.md)

## Start here

- [Root execution contract](../../AGENTS.md)
- [Coding standards](../../STYLE.md)
- [Phase overview](phases/overview.md)
- [Phase 0.5 cleanup and salvage baseline](phases/phase-0.5-cleanup-and-salvage-baseline.md)
- [Use this pack for implementation](how-to/use-this-pack-for-implementation.md)

## Phase selection

The execution pack does not keep a separate repo-global active-phase marker.

For each bounded redesign work package:

1. use pre-implementation review plus [Phase overview](phases/overview.md) to select the phase that owns the next blocking redesign delta
2. prefer the earliest phase whose target contract and locked surfaces are still required for that blocker
3. use [Phase 0.5 cleanup and salvage baseline](phases/phase-0.5-cleanup-and-salvage-baseline.md) before Phase 1 when stale repo shape, reset baseline ambiguity, stale tests, or plugin-boundary drift still dominate
4. record the selected phase explicitly in the approved plan

In the rest of this pack, `current phase page` means the selected phase page for the approved work package.

## Fast path

1. Read [Root execution contract](../../AGENTS.md).
2. Read [Coding standards](../../STYLE.md).
3. Run pre-implementation review and select the current phase.
4. Read the current phase page and the implementation file lock map together.
5. Read the redesign pages named by that phase page.
6. Read any named appendix owners when exact API/schema/prompt detail matters.
7. Build the approved phase plan, including the subagents decision and validation loop, and then execute.

## Execution router

1. Read [Root execution contract](../../AGENTS.md) and [Coding standards](../../STYLE.md).
2. Run the pre-implementation review flow in [Phase prompts](gates/phase-implementation-prompts.md).
3. Use that review to select the current phase and name the current phase page.
4. If the review finds a docs gap, patch canon before coding.
5. If the review says code work is ready, read the current phase page plus the [implementation file lock map](maps/file-priority-map.md).
6. Enter plan-mode phase planning and build the approved WBS for the selected phase, including the subagents decision, wave plan, and validation checkpoints.
7. After plan approval, execute using default Codex behavior plus `AGENTS.md`, `STYLE.md`, the current phase page, the implementation file lock map, and the approved plan.
8. Run post-implementation review, gates, reset when applicable, and phase-done checks before claiming completion.

## Keywords

- implementation pack
- phase overview
- cleanup phase
- salvage matrix
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

## Supporting maps

- [Current-to-target mapping](maps/current-to-target-mapping.md)
- [Current schema, route, and plugin migration appendix](maps/current-schema-route-and-plugin-migration-appendix.md)
- [Implementation file lock map](maps/file-priority-map.md)
- [Repo salvage matrix](maps/repo-salvage-matrix.md)
- [Execution how-to guides](how-to/use-this-pack-for-implementation.md)

## Implementation loop

1. Start with [Use this pack for implementation](how-to/use-this-pack-for-implementation.md).
2. Run the pre-implementation review prompt to confirm the selected phase, docs readiness, confidence, and blocking criteria.
3. Read the current phase page plus the implementation file lock map before planning implementation work.
4. Use the phase planning prompt while Codex is in Plan Mode to build the WBS, locked surfaces, dependencies, tests, subagents strategy, wave plan, and exit evidence.
5. Execute only after the plan is approved.
6. When you change canonical docs, prompt-pack inputs, `prompt-catalog.yaml`, or generated prompt pages, run `python scripts/docs/prompt_catalog_tools.py validate` from the workspace root. If prompt-catalog or prompt-pack inputs changed, run `python scripts/docs/prompt_catalog_tools.py generate` first.
7. Use [Verification prompts](gates/verification-prompts.md) for post-implementation review before claiming phase completion.

## Surface rule

Use this surface for implementation order, gates, and execution evidence.

Do not use it as the canonical target contract or the source of shipped current behavior.
