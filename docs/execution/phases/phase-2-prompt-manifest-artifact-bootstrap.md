# Phase 2 prompt, manifest, artifact, and bootstrap rewrite

Status: Target

This phase lands lean task compose, explicit prompt/render/manifest contracts, and richer task-root and artifact bootstrap behavior.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [Prompt layer and dispatch contract](../../redesign/prompt-layer/contract.md)
- [Prompt render and dispatch audit](../../redesign/prompt-layer/render-and-persistence.md)
- [Manifest contract](../../redesign/architecture/manifest-contract.md)
- [Worker context contract](../../redesign/architecture/worker-context-contract.md)
- [Runtime records and lifecycle](../../redesign/architecture/runtime-records-and-lifecycle.md)
- [Runtime boundary and controller loop contract](../../redesign/architecture/runtime-boundary-and-controller-loop-contract.md)
- [Task-root layout and generated files](../../redesign/architecture/task-root-layout-and-generated-files.md)
- [Artifact ref and storage contract](../../redesign/architecture/artifact-ref-and-storage-contract.md)
- [Typed dependency selectors and produce slots](../../redesign/workflows/typed-dependency-selectors-and-produce-slots.md)
- [Criteria and parent verification](../../redesign/workflows/criteria-and-parent-verification.md)

## Exhaustive appendix owners

- [Workflow schema appendix](../../redesign/workflows/workflow-schema-appendix.md)
- [Prompt resource and usage appendix](../../redesign/prompt-layer/prompt-resource-usage-appendix.md)

## Reference examples

- [System contract layer example](../../redesign/prompt-layer/composition-example.md)
- [Runtime prompt, state, and transport examples](../../redesign/prompt-layer/generated/rendered-examples.md)

## Implementation surfaces

- owned surfaces: `autoclaw-main/apps/api/app/schemas/runtime.py`, `autoclaw-main/apps/api/app/db/models/runtime.py`, `autoclaw-main/apps/api/app/runtime/resources.py`, `autoclaw-main/apps/api/app/runtime/dispatcher.py`, prompt or materialization services in `autoclaw-main/apps/api/app/runtime/`, prompt-layer owner docs, generated prompt examples, and manifest/task-root/artifact owner docs
- allowed collateral surfaces: prompt resource appendix, workflow schema appendix, prompt validation tooling, and narrow presenter/read-model surfaces when the prompt/runtime contract cannot otherwise be represented

## Do not edit / defer surfaces

- parent/root review, closure, and structural replan logic
- watchdog, operator, plugin, and support-state readback surfaces
- public ingest, CLI, package, and release behavior

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- subagents are useful here for prompt/render, manifest/task-root, or bootstrap/materialization slices
- the parent agent owns the final contract reconciliation across prompt docs, runtime state, generated examples, and validators

## Wave integration loop

1. lock the current prompt/runtime work package against the phase page and file lock map
2. decide `no subagents` or brief the bounded subagents slices
3. integrate the returned code, docs, and generated examples
4. run prompt validators, runtime tests, and minimal-lane evidence checks when viable
5. review findings and patch before another wave

## Phase purpose

Make prompt/render/manifest/task-root/bootstrap behavior explicit enough that later runtime, operator, and ingest phases can rely on it without hidden coupling.

## Success criteria

- task compose is a lean launch input
- prompt/render/manifest/task-root contracts are explicit and test-backed
- bootstrap and artifact behavior are reproducible and example-backed

## Deliverables

- prompt/render alignment
- manifest and task-root alignment
- bootstrap/materialization alignment

## Milestones

- prompt/render logic aligned
- manifest/task-root semantics aligned
- bootstrap/materialization path aligned

## Ordered work packages

### `P2-WP1`

- objective: align prompt and render semantics with canonical prompt truth
- owned surfaces: prompt, render, and hashing logic plus prompt docs/examples
- dependencies: Phase 1 complete
- test-first requirement: failing or gap-revealing prompt/render tests
- docs/update requirement: prompt examples and rendered examples updated together
- subagent allowed: yes
- closeout evidence: prompt examples match landed behavior

### `P2-WP2`

- objective: align manifest and task-root semantics
- owned surfaces: manifest, worker context, task-root docs, runtime resources
- dependencies: `P2-WP1`
- test-first requirement: manifest projection and task-root tests
- docs/update requirement: generated-file and worker-context docs remain explicit
- subagent allowed: yes
- closeout evidence: manifest/task-root semantics are reproducible

### `P2-WP3`

- objective: align bootstrap, materialization, and artifact handoff behavior
- owned surfaces: dispatcher/materialization code and bootstrap-related docs
- dependencies: `P2-WP1`, `P2-WP2`
- test-first requirement: bootstrap/materialization integration tests
- docs/update requirement: artifact/bootstrap semantics updated in same phase
- subagent allowed: yes
- closeout evidence: bootstrap path is test-backed and no longer filesystem-primary by accident

## Mandatory checklist

- [ ] prompt, manifest, task-root, and artifact docs match the landed runtime behavior
- [ ] generated prompt examples were regenerated or revalidated when the prompt contract changed
- [ ] task compose remains a lean launch input rather than a runtime kitchen sink
- [ ] any subagents slice stayed inside its prompt/render, manifest/task-root, or bootstrap ownership

## Required tests

- unit tests for prompt render logic and contract hashing
- integration tests for manifest projection and task-root bootstrap
- minimal e2e lane once prompt, runtime, and bootstrap flow are viable

## Required docs/examples

- prompt-layer examples
- manifest docs
- task-root docs
- runtime examples

## Candidate delegated slices

- prompt/render slice
- manifest/task-root slice
- bootstrap/materialization slice

## Exit evidence

- prompt, manifest, and runtime-state examples match landed behavior
- bootstrap and materialization semantics are explicit and reproducible
- no old overloaded task-compose or prompt-bundle assumptions survive

## Reset criteria

- the reset gate is required if runtime schema, task-root structure, or manifest persistence truth changes

## Kill-list terms

- task compose as a runtime-derived kitchen sink
- prompt rules that rely on hidden transcript memory
- filesystem-primary truth for generated roots
