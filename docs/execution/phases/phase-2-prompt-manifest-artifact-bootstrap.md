# Phase 2 prompt, manifest, artifact, and bootstrap rewrite

Status: Target

This phase lands lean task compose, explicit prompt/render/manifest contracts, and richer task-root and artifact bootstrap behavior.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [Prompt layer and dispatch contract](../../redesign/prompt-layer/contract.md)
- [Prompt source and assembly contract](../../redesign/prompt-layer/source-and-sections.md)
- [Prompt field renderers](../../redesign/prompt-layer/field-renderers.md)
- [Prompt render and dispatch audit](../../redesign/prompt-layer/render-and-persistence.md)
- [Prompt machine contract](../../redesign/prompt-layer/machine-contract.md)
- [Manifest contract](../../redesign/architecture/manifest-contract.md)
- [Worker context contract](../../redesign/architecture/worker-context-contract.md)
- [Runtime records and lifecycle](../../redesign/architecture/runtime-records-and-lifecycle.md)
- [Runtime boundary and controller loop contract](../../redesign/architecture/runtime-boundary-and-controller-loop-contract.md)
- [Task-root layout and generated files](../../redesign/architecture/task-root-layout-and-generated-files.md)
- [Artifact ref and storage contract](../../redesign/architecture/artifact-ref-and-storage-contract.md)
- [Typed dependency selectors and produce slots](../../redesign/workflows/typed-dependency-selectors-and-produce-slots.md)
- [Criteria and parent verification](../../redesign/workflows/criteria-and-parent-verification.md)

## Required supporting redesign reads

- [Prompt-layer front door](../../redesign/prompt-layer/README.md)
- [Prompt-layer index](../../redesign/prompt-layer/INDEX.md)
- [Prompt-pack router and exact block ownership](../../redesign/prompt-layer/prompt-pack/README.md)
- [System and provider block](../../redesign/prompt-layer/prompt-pack/system-and-provider-block.md)
- [Runtime rule blocks](../../redesign/prompt-layer/prompt-pack/runtime-rule-blocks.md)
- [Validation and reject blocks](../../redesign/prompt-layer/prompt-pack/validation-and-reject-blocks.md)
- [Generated prompt artifact routing](../../redesign/prompt-layer/generated/README.md)
- [Prompt legality and coverage summary](../../redesign/prompt-layer/legality-and-coverage.md)
- [Prompt catalog machine surface](../../redesign/prompt-layer/prompt-catalog.yaml)
- [Filesystem layout and roots](../../redesign/architecture/filesystem-layout-and-roots.md)
- [Task compose root binding and host placement](../../redesign/architecture/task-compose-root-binding-and-host-placement.md)
- [ADR-0005 task-owned roots and runtime-generated projections](../../redesign/decisions/ADR-0005-task-owned-roots-and-runtime-generated-projections.md)
- [Historical prompt and artifact layers](../../redesign/prompt-layer/historical-prompt-and-artifact-layers.md),
  [historical dispatch-family packs](../../redesign/prompt-layer/prompt-pack/dispatch-family-packs.md),
  [historical packet prose examples](../../redesign/prompt-layer/prompt-pack/historical-packet-prose-examples.md),
  and [historical state and boundary overlays](../../redesign/prompt-layer/prompt-pack/state-and-boundary-overlays.md)
  when stale prompt, packet, bundle, or overlay vocabulary is part of the blocker

## Required current contrast reads

- [Prompt layer and worker delivery](../../current/interfaces/prompt-layer-and-worker-delivery.md)
- [Current exact OpenClaw bridge prompt strings](../../current/interfaces/current-openclaw-bridge-prompt-strings.md)
- [Manifest projection and acknowledgement](../../current/architecture/manifest-projection-and-acknowledgement.md)
- [Task roots and materialized paths](../../current/architecture/task-roots-and-materialized-paths.md)

## Exhaustive appendix owners

- [Workflow schema appendix](../../redesign/workflows/workflow-schema-appendix.md)
- [Prompt resource and usage appendix](../../redesign/prompt-layer/prompt-resource-usage-appendix.md)

## Reference examples

- [System contract layer example](../../redesign/prompt-layer/composition-example.md)
- [Runtime prompt, state, and transport examples](../../redesign/prompt-layer/generated/rendered-examples.md)
- [Generated prompt inventory](../../redesign/prompt-layer/generated/inventory.md)

## Required examples and diagrams

- [System contract layer example](../../redesign/prompt-layer/composition-example.md)
- [Runtime prompt, state, and transport examples](../../redesign/prompt-layer/generated/rendered-examples.md)
- [Generated prompt inventory](../../redesign/prompt-layer/generated/inventory.md)
- the mermaid render-flow diagram in [Prompt render and dispatch audit](../../redesign/prompt-layer/render-and-persistence.md)
- the generated-files layout diagram in [Task-root layout and generated files](../../redesign/architecture/task-root-layout-and-generated-files.md)

## Implementation surfaces

- owned surfaces: `apps/api/app/runtime/resources.py`,
  app-owned shipped prompt assets under `apps/api/app/runtime/prompt/assets/**`,
  prompt/render/materialization services under `apps/api/app/runtime/*` that
  own prompt assembly, manifest projection, task-root generation, artifact
  localization, or generated read-surface materialization, prompt-layer owner
  docs as mirrors of the shipped prompt source, generated prompt examples, and
  manifest/task-root/artifact owner docs
- allowed collateral surfaces: prompt-generated example surfaces, prompt
  resource appendix, workflow schema appendix, the exact Phase 2
  current-contrast pages named above when truthful prompt/manifest/task-root
  contrast repair is required, targeted prompt validation tooling under
  `scripts/docs/*`, narrow `pyproject.toml` package-data entries only when
  those prompt assets must ship through the existing package path, narrow
  presenter/read-model surfaces when the prompt/runtime contract cannot
  otherwise be represented, prompt/render/bootstrap/e2e proof tests under
  `apps/api/tests/**` when they are required to prove Phase 2-owned truth, and
  the selected Phase 2 plan/evidence/review artifacts under
  `docs/execution/plans/`, `docs/execution/evidence/`, and
  `docs/execution/reviews/`

## Do not edit / defer surfaces

- parent/root review, closure, and structural replan logic
- watchdog, operator, plugin, and support-state readback surfaces
- foreground dispatch control-state handshake, replacement-dispatch inactivity
  proof, continuation-slot legality, release precondition truth, and runtime
  assignment/attempt/checkpoint/currentness rows, which remain Phase 3-owned
- public ingest, new CLI noun families, package/install/reset/release
  surfaces, or broader CLI UX beyond the narrow prompt-asset package-data
  allowance above

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
- shipped exact prompt blocks are app-owned packaged assets, and prompt docs,
  generated examples, and prompt-catalog references mirror that shipped source
- prompt/render/manifest/task-root contracts are explicit and test-backed
- prompt and runtime read surfaces keep the locked carrier split: surfaced
  non-artifact durable refs keep `kind`, surfaced criteria omit ordinary
  `version`, and `release_green` or `release_blocked` are not continuation
  outcomes
- bootstrap and artifact behavior are reproducible and example-backed
- runtime persistence truth for assignments, attempts, checkpoints, and currentness remains deferred to Phase 3
- release preconditions and foreground control-state ownership also remain
  Phase 3-owned
- runtime persistence truth for assignments, attempts, checkpoints, currentness,
  release preconditions, and foreground control-state remains deferred to
  Phase 3

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

- objective: align prompt and render semantics with canonical prompt truth and
  app-owned shipped prompt assets
- owned surfaces: prompt assets, prompt/render and hashing logic, plus prompt
  docs/examples
- dependencies: Phase 1 complete
- test-first requirement: failing or gap-revealing prompt/render tests
- docs/update requirement: prompt examples and rendered examples updated together
- subagent allowed: yes
- closeout evidence: prompt examples and the shipped prompt assets match landed behavior

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
- owned surfaces: prompt/render/materialization code and bootstrap-related docs
- dependencies: `P2-WP1`, `P2-WP2`
- test-first requirement: bootstrap/materialization integration tests
- docs/update requirement: artifact/bootstrap semantics updated in same phase
- subagent allowed: yes
- closeout evidence: bootstrap path is test-backed and no longer filesystem-primary by accident

## Mandatory checklist

- [ ] prompt, manifest, task-root, and artifact docs match the landed runtime behavior
- [ ] app-owned shipped prompt assets, prompt docs mirrors, generated examples,
      and prompt-catalog references were updated together when prompt-source
      ownership changed
- [ ] generated prompt examples were regenerated or revalidated when the prompt contract changed
- [ ] task compose remains a lean launch input rather than a runtime kitchen sink
- [ ] prompt/read surfaces preserve the locked carrier split for criteria,
      continuation truth, and current-assignment readback
- [ ] any subagents slice stayed inside its prompt/render, manifest/task-root, or bootstrap ownership

## Required tests

- unit tests for prompt render logic and contract hashing
- prompt asset lookup or packaging tests when shipped prompt assets change
- integration tests for manifest projection and task-root bootstrap
- prompt-catalog generate/validate checks when prompt-layer owner or generated surfaces change
- package-install verification when narrow prompt-asset package-data changes
- minimal e2e lane once prompt, runtime, and bootstrap flow are viable

## Required docs/examples

- prompt-layer examples
- manifest docs
- task-root docs
- runtime examples
- required examples and diagrams named above

## Candidate delegated slices

- prompt/render slice
- manifest/task-root slice
- bootstrap/materialization slice

## Exit evidence

Record the approved plan under [../plans/README.md](../plans/README.md), the
executed prompt or runtime proof under [../evidence/README.md](../evidence/README.md),
and any closeout review or exception record under
[../reviews/README.md](../reviews/README.md).

- prompt, manifest, and runtime-state examples match landed behavior
- app-owned shipped prompt assets are the runtime source and prompt docs remain
  mirrors of that source
- bootstrap and materialization semantics are explicit and reproducible
- no old overloaded task-compose or prompt-bundle assumptions survive
- runtime DB rows, runtime schemas, assignment currentness, checkpoint truth,
  release precondition truth, and foreground control-state ownership are still
  deferred cleanly to Phase 3

## Reset criteria

- the reset gate is required if runtime schema, task-root structure, manifest
  persistence truth, or shipped prompt-asset package-install truth changes

## Kill-list terms

- task compose as a runtime-derived kitchen sink
- redesign docs treated as the shipped prompt source
- prompt rules that rely on hidden transcript memory
- filesystem-primary truth for generated roots
- runtime persistence truth split across both Phase 2 and Phase 3
