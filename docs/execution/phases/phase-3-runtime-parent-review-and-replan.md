# Phase 3 runtime, parent, review, and replan rewrite

Status: Target

This phase lands the runtime graph semantics: assignments, attempts, parent/root review and release behavior, internal review outputs, criteria and report semantics, and parent-owned structural replan.

## Implementation file lock

Use [Implementation file lock map](../maps/file-priority-map.md) as the canonical owned-surface map for this phase.

## Primary redesign pages

- [Runtime records and lifecycle](../../redesign/architecture/runtime-records-and-lifecycle.md)
- [Assignment contract](../../redesign/architecture/assignment-contract.md)
- [Checkpoint contract](../../redesign/architecture/checkpoint-contract.md)
- [Worker context contract](../../redesign/architecture/worker-context-contract.md)
- [Runtime boundary and controller loop contract](../../redesign/architecture/runtime-boundary-and-controller-loop-contract.md)
- [Runtime observability and boundary log](../../redesign/architecture/runtime-observability-and-boundary-log.md)
- [Artifact ref and storage contract](../../redesign/architecture/artifact-ref-and-storage-contract.md)
- [Parent/root release and closure](../../redesign/workflows/parent-root-release-and-closure.md)
- [Parent review and replan](../../redesign/workflows/parent-review-and-replan.md)
- [Runtime structural replan](../../redesign/workflows/runtime-structural-replan.md)
- [Typed dependency selectors and produce slots](../../redesign/workflows/typed-dependency-selectors-and-produce-slots.md)
- [Criteria and parent verification](../../redesign/workflows/criteria-and-parent-verification.md)
- [Runtime database and object contract](../../redesign/architecture/runtime-database-and-object-contract.md)
- [Review outputs contract](../../redesign/workflows/review-findings-contract.md)

## Required supporting redesign reads

- [Redesign overview](../../redesign/architecture/redesign-overview.md)
- [Completion, checkpoint, and evidence](../../redesign/architecture/completion-checkpoint-and-evidence.md)
- [Parent/root planning surface](../../redesign/workflows/parent-root-planning-surface.md)
- [Parent, worker, and review model](../../redesign/workflows/parent-worker-review-model.md)
- [Guarded registry and runtime writes](../../redesign/interfaces/guarded-registry-and-runtime-writes.md)
- [Definition registry and upload contract](../../redesign/interfaces/definition-registry-and-upload-contract.md)
- [ADR-0001 controller-first relational runtime truth](../../redesign/decisions/ADR-0001-controller-first-relational-runtime-truth.md)
- [ADR-0006 revision-safe replan and adopt](../../redesign/decisions/ADR-0006-revision-safe-replan-and-adopt.md)

## Required current contrast reads

- [Runtime control plane](../../current/architecture/runtime-control-plane.md)
- [Current runtime read models and operator surfaces](../../current/architecture/runtime-read-models-and-operator-surfaces.md)
- [API surface and route map](../../current/interfaces/api-surface-and-route-map.md)
- [API trust lanes](../../current/interfaces/api-trust-lanes.md)
- [Run the current Docker and Postgres verification lane](../../current/operations/run-docker-postgres-verification.md)

## Required examples and diagrams

- the lifecycle and controller-loop mermaid diagrams in [Runtime records and lifecycle](../../redesign/architecture/runtime-records-and-lifecycle.md), [Runtime boundary and controller loop contract](../../redesign/architecture/runtime-boundary-and-controller-loop-contract.md), and [Runtime lifecycle overview](../../redesign/architecture/runtime-lifecycle-overview.md)
- [Parent review and replan](../../redesign/workflows/parent-review-and-replan.md)
- [Parent/root release and closure](../../redesign/workflows/parent-root-release-and-closure.md)
- [Runtime structural replan](../../redesign/workflows/runtime-structural-replan.md)
- [Normal workflow reference](../../redesign/workflows/examples/normal.md)
- [Maximal workflow reference](../../redesign/workflows/examples/maximal.md)

## Exhaustive appendix owners

- [Workflow schema appendix](../../redesign/workflows/workflow-schema-appendix.md)
- [API schema appendix](../../redesign/interfaces/api-schema-appendix.md)

## Implementation surfaces

- owned surfaces: runtime models and persistence in `apps/api/app/db/`,
  runtime schemas under `apps/api/app/schemas/*`, runtime control, assignment,
  attempt, checkpoint, closure, review, and replan services under
  `apps/api/app/runtime/*`, runtime presenters in `apps/api/app/api/*`, and
  the runtime/review/replan owner docs, including the foreground dispatch
  control-state handshake and replacement-dispatch inactivity proof
- allowed collateral surfaces: workflow schema appendix, API schema appendix,
  worker-context docs, and artifact/ref docs when review or replan payloads
  need exact updates, `docs/current/architecture/runtime-control-plane.md` and
  `docs/current/interfaces/api-trust-lanes.md` when truthful current-contrast
  repair is required for runtime control-state, operator or callback lane, or
  compatibility readback wording, plus the existing shipped init/upgrade/reset
  shell under
  `apps/api/app/cli.py` when Phase 3-owned runtime persistence truth must be
  reachable through the shipped path without widening public CLI nouns or
  package/install ownership, plus narrow task-scoped
  `/operator/tasks/{task_id}/snapshot`,
  `/operator/tasks/{task_id}/trace`, and `/observability/tasks/{task_id}/*`
  read shells when Phase 3-owned runtime closure or readback truth must be
  exposed through compatibility reads without widening into watchdog recovery,
  standard external plugin parity, or frozen support-state semantics, plus the
  runtime, schema, route, and e2e proof tests under `apps/api/tests/**` when
  they are required to prove Phase 3-owned control-state, persistence,
  closure, review, or replan truth, plus the
  selected Phase 3 plan/evidence/review artifacts under
  `docs/execution/plans/`, `docs/execution/evidence/`, and
  `docs/execution/reviews/`

## Do not edit / defer surfaces

- gateway/session/continuity implementation beyond narrow compatibility fixes
- watchdog recovery, standard external plugin parity, and frozen support-state
  semantics beyond the narrow task-scoped `/operator/...` snapshot/trace and
  `/observability/...` read shells explicitly allowed above
- public ingest, new CLI noun families, package/install/reset/release
  surfaces, or broader CLI UX beyond the narrow shipped-path proof wiring
  explicitly allowed above
- prompt/render/materialization helpers whose primary contract stays locked to Phase 2 except for narrow compatibility fixes required to land runtime truth cleanly

## Subagents

- every phase plan must explicitly say `no subagents` or define bounded subagents slices
- subagents are useful here for runtime transitions, review/closure, or replan slices
- the parent agent owns the final runtime graph interpretation, boundary legality, and closure semantics

## Wave integration loop

1. lock the current runtime work package against the phase page and file lock map
2. decide `no subagents` or brief the bounded subagents slices
3. integrate the returned runtime, schema, presenter, and docs changes
4. run runtime transition, review, closure, and replan tests plus normal-lane evidence when viable
5. review findings and patch before another wave

## Phase purpose

Make runtime graph truth, closure evidence, parent review, and structural replan explicit enough to support exact controller decisions and later watchdog/operator work.

## Success criteria

- one attempt equals one bounded assignment attempt
- checkpoint plus attempt report plus evidence-backed completion are required
- parent verification, review outputs, and structural replan match canon
- runtime DB truth, runtime schemas, generated runtime projections, and the
  foreground dispatch control-state handshake are owned here rather than split
  across earlier phases
- launch/open/abort control-state transitions, drain-window deadlines, and
  replacement-dispatch inactivity proof follow the Phase 3 runtime docs rather
  than being deferred to later phases
- `release_green` and root `release_blocked` remain terminal preconditions,
  not continuation outcomes; the one-continuation rule stays
  `child_assignment | null`
- runtime structural replan validates against controller-owned registry truth and
  pins exact resolved revisions instead of rereading repo files
- any compatibility `/operator` or `/observability` reads stay task-scoped and
  do not absorb Phase 4B ownership of watchdog recovery, plugin parity, or
  frozen support-state semantics
- shipped install, upgrade, and reset paths create the landed runtime schema
  without test-only setup

## Deliverables

- runtime record and transition alignment
- parent/review/closure alignment
- structural replan alignment

## Milestones

- runtime record truth aligned
- parent/review/closure path aligned
- structural replan path aligned

## Ordered work packages

### `P3-WP1`

- objective: align runtime record transitions, foreground control-state
  handshake, and assignment/attempt semantics
- owned surfaces: runtime persistence, runtime control services, runtime schemas
- dependencies: Phase 2 complete
- test-first requirement: failing or gap-revealing runtime transition tests
- documentation update requirement: runtime record docs remain precise
- subagent allowed: yes
- closeout evidence: runtime truth and control-state ownership match canonical
  runtime record docs

### `P3-WP2`

- objective: align parent verification, review outputs, and closure evidence
- owned surfaces: parent/review/closure code and docs
- dependencies: `P3-WP1`
- test-first requirement: review outputs and closure tests
- documentation update requirement: parent/review docs and examples updated in same phase
- subagent allowed: yes
- closeout evidence: checkpoint-only closure is no longer canonical behavior

### `P3-WP3`

- objective: align parent-owned structural replan and adoption flow
- owned surfaces: replan code, schemas, and docs
- dependencies: `P3-WP1`, `P3-WP2`
- test-first requirement: replan adoption tests
- documentation update requirement: replan dossier and adoption flow remain explicit
- subagent allowed: yes
- closeout evidence: structural replan stays under parent authority only

## Mandatory checklist

- [ ] assignment, attempt, checkpoint, review, and replan semantics are explicit and aligned in docs and code
- [ ] checkpoint-only closure logic is no longer canonical or left alive in parallel
- [ ] parent verification and structural replan remain under parent authority only
- [ ] launch/open/abort control-state transitions, drain-window deadlines, and
      replacement-dispatch inactivity proof remain Phase 3-owned and aligned
      with the runtime lifecycle docs
- [ ] `release_green` and root `release_blocked` stay terminal preconditions
      rather than continuation outcomes, and the one-continuation rule stays
      `child_assignment | null`
- [ ] any Phase 3 compatibility `/operator` or `/observability` reads stay
      narrow and task-scoped rather than widening into Phase 4B watchdog,
      plugin, or frozen support-state ownership
- [ ] runtime install, upgrade, and reset proof does not rely on manual
      `metadata.create_all()` or other test-only schema setup
- [ ] runtime structural adopt and validation do not reread repo-local
      definition files once earlier-phase registry truth exists
- [ ] any subagents slice stayed inside its runtime transition, review, closure, or replan ownership

## Required tests

- unit tests for runtime record transitions and parent-boundary rules
- unit or integration tests for launch/open/abort control-state transitions and
  replacement-dispatch inactivity proof
- integration tests for review outputs, parent verification, and replan adoption
- fresh-install and reset smoke for shipped SQLite init or upgrade or reset paths
- normal e2e lane once parent, review, and closure flow are viable
- SQLite local smoke once runtime persistence and generated runtime truth are viable
- Postgres + Docker strong verification once runtime persistence and migrations are viable

## Required docs and examples

- runtime records docs
- parent/review docs
- replan docs
- required examples and diagrams named above

## Candidate delegated slices

- runtime transitions slice
- review/closure slice
- replan slice

## Exit evidence

Record the approved plan under [../plans/README.md](../plans/README.md), the
executed runtime proof under [../evidence/README.md](../evidence/README.md),
and any closeout review or exception record under
[../reviews/README.md](../reviews/README.md).

- runtime truth matches canonical runtime-record and boundary docs
- launch/control-state ownership and continuation truth match the taught
  runtime lifecycle and boundary docs
- parent, review, and replan behavior match the taught workflow and prompt surfaces
- stale checkpoint-only closure logic is gone
- shipped init or upgrade or reset paths create and verify the landed runtime
  schema without test-only setup
- SQLite and Postgres proof lanes are recorded or explicitly blocked with an exact phase-bounded reason

## Reset criteria

- apply the reset gate if runtime schema, runtime persistence, or generated runtime truth changes

## Kill-list terms

- attempt identity detached from assignment identity
- review treated as an external gate
- structural replan adopted outside parent authority
- runtime truth split across both Phase 2 and Phase 3
