# AutoClaw refactor checklist — runtime stabilization and aggressive logic cleanup

Status: implementation-prep checklist
Owner stance: aggressively separate, merge, and rewrite for DRY, purity, concentrated invariants, and simpler ownership
Scope: backend/runtime/compiler/resource/control-plane cleanup only
Frontend/console note: console cleanup is explicitly deferred unless it blocks backend layering truth; if touched, keep it to boundary/readability cleanup only.
Use this as an operator document and checkpoint map, not as a literal sprint board to execute item-by-item without regrouping. The real unit of work is an invariant/ownership slice, not a file sweep.

---

## Review verdict

I am confident enough in this plan to implement it next.

Why:
- the main architectural fault lines are clear in code, not just in docs
- the highest-risk invariants are identifiable and repeated across modules
- the current repo already has enough tests and structure to support an aggressive backend cleanup without guessing the system shape
- the current danger is semantic drift, not missing architecture
- the review passes converged strongly on the same hotspots: callback identity, runtime orchestration, read-truth drift, task/runtime truth, query/load duplication, route/service leakage, and transitional dead code
- `docs/roadmap/suggestion.md` aligns with the intended direction: routes thin, runtime owns runtime, compiler stays compile-focused, services are cross-domain only, presenters format only

What I am assuming:
- we are allowed to aggressively refactor internal module boundaries
- we are not trying to preserve accidental internal APIs
- we will preserve external behavior where intended, but we will simplify and remove transitional internals
- we prefer fewer canonical code paths over preserving compatibility shims internally
- this is a large refactor, so resetting local DB state, rewriting tests, restructuring service wiring, and changing systemd/service assumptions if needed are allowed when they make the codebase materially simpler and more honest

What I will treat as non-negotiable during implementation:
- one canonical runtime identity contract
- one canonical task-resource / task-compose truth path
- one canonical node-path / graph-materialization rule
- one canonical readiness / resumability decision path
- one canonical dispatch-trigger policy
- no duplicated callback validation logic
- no duplicated launch-binding/remint decision logic across runtime/presenter/API
- no route as the sole owner of runtime-domain invariants
- no cross-module imports of underscore-prefixed helpers left in touched areas
- no transitional dead helpers left behind if we already know the real shape
- routes stay HTTP-only, presenters stay presentation-only, runtime owns execution logic

---

## Large-refactor permissions and expectations

These are explicitly allowed for this pass when they improve the codebase materially:

- [ ] reset local DB/dev data if the old state is blocking an honest rebaseline
- [ ] rewrite migrations rather than preserving messy transitional history
- [ ] rewrite tests substantially when current tests encode transitional/internal behavior instead of the desired contract
- [ ] change service/bootstrap/systemd assumptions and scripts if the current wiring preserves accidental complexity
- [ ] remove or replace compatibility helpers that only exist to prop up old internal shapes
- [ ] break internal-only APIs and helper call patterns freely when the replacement is cleaner and test-backed

Guardrail:
- [ ] do not preserve local/dev/runtime state complexity just because it already exists; prefer a cleaner canonical path and then rebuild tests/bootstrap around it

---

## Global implementation rules

- [ ] Prefer reducing the number of canonical code paths before increasing the number of modules.
- [ ] New modules are justified only when they measurably remove duplication or clarify ownership.
- [ ] Do not split a file mechanically by line count.
- [ ] Prefer a few fatter, clearer ownership modules over file spam.
- [ ] Do not preserve fake module boundaries; either make a boundary real or collapse it.
- [ ] Presenters format data; they do not reconstruct runtime truth.
- [ ] Routes transport requests; they do not own core runtime-domain validation.
- [ ] Runtime logic lives under `app/runtime/*`, not in routes or random services.
- [ ] Compiler logic stays compile-focused under `app/compiler/*`.
- [ ] Registry logic stays under `app/registry/*`.
- [ ] Services are for cross-domain orchestration only, not as a dumping ground for business logic.
- [ ] DB state is authoritative over filesystem audit artifacts.
- [ ] Canonical UUID parsing is the default; compatibility parsing, if kept, must be narrow and documented.
- [ ] Prefer typed read/write contracts over raw dict assembly when shape is known.
- [ ] Treat overlapping checklist areas as one ownership pass when executing:
  - [ ] one trust-boundary pass
  - [ ] one runtime-decision pass
  - [ ] one read-truth/load-profile pass
- [ ] Prefer invariant slices over file sweeps.

---

## Verification style and default workflow

Suggested by `docs/roadmap/suggestion.md`; use this as the practical default for the refactor.

### Refactor/edit workflow
- [ ] edit/refactor locally
- [ ] format first: `make format-api`
- [ ] run bundled checks: `make check-api`
- [ ] run fast tests: `make test-api`
- [ ] run DB/integration tests when runtime/compiler/API persistence changed: `make test-api-db`
- [ ] run docker smoke when endpoint/runtime behavior changed materially:
  - [ ] `make docker-up`
  - [ ] exercise the key path manually
  - [ ] `make docker-down`

### Extra verification notes for this refactor
- [ ] prefer rewriting brittle tests over dragging transitional behavior forward
- [ ] if the migration/schema model is rebaselined, verify both fresh SQLite and fresh Postgres explicitly
- [ ] if service/bootstrap/systemd wiring is simplified, verify the new canonical local start path and service path directly
- [ ] when route/runtime behavior changes materially, confirm routes remain thin and presenters remain formatting-only

### Current test baseline at review time
- [ ] `make check-api` currently fails before runtime tests due largely to lint/format/type hygiene drift in migrations/tests. Treat this as hygiene drift, not the main product signal.
- [ ] `make test-api` is nearly green: 44 passed, 1 failed. Current observed failure looks like unit-level contract drift in `tests/unit/test_registry_service.py::test_iter_definition_files_uses_configured_definitions_root`.
- [ ] `make test-api-db` is not mostly test drift right now. Current observed result: 31 failed, 87 passed, 1 skipped, 5 errors.
- [ ] At least one DB/integration error is a real integration/runtime issue, not test drift: Postgres deadlock during schema reset/setup in `tests/integration/test_phase456_runtime_db.py::test_replan_uses_effective_node_merge_contract_for_metadata_description_and_skills`.
- [ ] Current failing integration surface is concentrated in runtime/API contract areas, especially:
  - [ ] approval/runtime API flows
  - [ ] context manifest ack routes / compatibility behavior
  - [ ] internal OpenClaw dispatch routing
  - [ ] watchdog recovery behavior
  - [ ] replan endpoint/runtime behavior
  - [ ] retry behavior on never-started nodes
  - [ ] task resource binding index/schema expectations
- [ ] Working classification: the suite currently shows **both** runtime/integration breakage **and** test-contract drift, but the DB/integration failures are too numerous and too concentrated in runtime surfaces to dismiss as mostly test drift.

---

## Top-level implementation strategy

Order matters.

1. Restore the test suite as a trustworthy signal first
2. Run a short mandatory guardrail gate
3. Land the runtime truth + callback binding slice
4. Land the task/runtime truth slice
5. Land the orchestration + dispatch ownership slice
6. Pass the migration/schema checkpoint gate
7. Align seeded workflow/docs/runtime graph truth
8. Clean API/query surfaces and boundary leaks
9. Do internal naming cleanup last

---

## Phase 0 — restore the test suite as a trustworthy signal

### 0.1 Fix the quality gate first
- [ ] Fix lint/format/import-order/line-length issues blocking `make check-api`
- [ ] Reformat/fix migration files to repo style unless there is a strong documented reason not to
- [ ] Fix test-file lint/import-order issues so the suite is readable and checkable again
- [ ] Re-run `make check-api` until it becomes a useful signal rather than noise

### 0.2 Resolve obvious unit-level contract drift
- [ ] Investigate and fix/rebaseline `tests/unit/test_registry_service.py::test_iter_definition_files_uses_configured_definitions_root`
- [ ] Decide explicitly whether the current definition precedence behavior is intentional or drifted
- [ ] Patch either implementation or test to the chosen contract

### 0.3 Triage integration failures by category, not one test at a time
- [ ] Group current DB/integration failures into clustered fix buckets:
  - [ ] approval API contract failures
  - [ ] context manifest ack route / compat failures
  - [ ] internal OpenClaw dispatch routing failures
  - [ ] watchdog recovery failures
  - [ ] replan endpoint/runtime failures
  - [ ] retry-on-never-started-node behavior failures
  - [ ] task resource binding index/schema expectation failures
  - [ ] Postgres schema reset/setup deadlock
- [ ] For each cluster, classify whether it is:
  - [ ] real runtime/schema/API breakage
  - [ ] route/service contract drift to fix in product code
  - [ ] test expecting transitional behavior that should be rewritten
- [ ] Fix clustered behavior once, then rewrite/update grouped tests together

### 0.4 Stabilize setup/schema blockers before deeper semantic cleanup
- [ ] Fix the Postgres deadlock during schema reset/setup first
- [ ] Make SQLite/Postgres test setup boring and deterministic
- [ ] Fix backend parity/index/schema expectation failures next
- [ ] Only after setup/schema stabilizes, work through runtime semantic failures in approval/ack/watchdog/replan/dispatch clusters

Exit condition:
- [ ] `make check-api` passes or only has intentional documented exceptions
- [ ] `make test-api` passes cleanly
- [ ] `make test-api-db` failures are reduced to a small set of known refactor-category failures, not scattered breakage
- [ ] the suite is trustworthy enough to guide the refactor rather than obscure it

---

## Phase 1 — mandatory short guardrail gate

This phase is mandatory and intentionally short.

- [ ] callback identity characterization tests
- [ ] node-path regression tests
- [ ] watchdog decision-table tests
- [ ] one task bootstrap/resource truth test

Exit condition:
- [ ] these four guardrail areas are covered by clear, stable tests before deeper rewrites begin

---

## Phase 2 — runtime truth + callback binding

Goal: centralize runtime truth, callback identity, and read-truth selection before broader orchestration changes.

Current pain:
- callback identity checks are split across runtime handlers, routes, and bridge paths
- runtime read truth is reconstructed across runtime services, read models, and presenters
- duplicated `selectinload(...)` trees and checkpoint helper logic increase drift risk
- presenters still participate in runtime-state selection rather than pure formatting

### 2.1 Write down runtime invariants as code-facing truth
- [ ] Create a short implementation contract doc under `docs/` for:
  - [ ] current attempt identity rules
  - [ ] active flow revision rules
  - [ ] node session binding rules
  - [ ] context manifest lifecycle rules
  - [ ] ack lineage rules
  - [ ] ack checkpoint semantics (`sequence_no = 0` hidden from visible timelines but authoritative for lineage)
  - [ ] checkpoint monotonicity rules
  - [ ] visible-vs-hidden checkpoint semantics
  - [ ] readiness / resumability decision rules
  - [ ] dispatch-trigger rules
  - [ ] watchdog recovery decision rules
- [ ] Use this contract to drive code extraction decisions, not the other way around

### 2.2 Delete or quarantine transitional/dead surfaces early
- [ ] Inventory touched-area dead/transitional helpers, placeholder branches, and fake abstraction centers
- [ ] Delete or quarantine them before major extraction work preserves them accidentally
- [ ] Explicitly audit for:
  - [ ] `runtime/packaging.py::current_runtime_view()`
  - [ ] `if False` / placeholder runtime branches
  - [ ] compatibility shims in touched paths that are no longer the chosen truth
  - [ ] duplicate helper paths that are obviously transitional

### 2.3 Safety/trust-boundary inventory
- [ ] Inventory all places where secrets/tokens are returned to clients or embedded into UI config
- [ ] Inventory all filesystem write paths and classify authoritative vs audit-only files
- [ ] Inventory all permissive parsing shims and decide where strict-vs-compat parsing is allowed
- [ ] Inventory all routes by trust lane:
  - [ ] public/operator
  - [ ] internal callback
  - [ ] worker-scoped read
  - [ ] browser console bootstrap

### 2.4 Introduce a single delegated execution binding module
- [ ] Create one concentrated module for delegated runtime identity validation, e.g. `runtime/execution_binding.py`
- [ ] Move shared validation there:
  - [ ] ensure flow exists and is not terminal where required
  - [ ] ensure current attempt
  - [ ] ensure active flow revision freshness
  - [ ] ensure node session matches current delegated session
  - [ ] ensure manifest belongs to attempt
  - [ ] ensure manifest hash matches
  - [ ] ensure latest acked manifest is the valid lineage anchor
  - [ ] ensure ack checkpoint lineage matches latest acknowledged manifest
  - [ ] ensure capability/authority lane is appropriate for the action if needed
- [ ] Expose a single validated binding object / dataclass for downstream operations

### 2.5 Stop open-coding callback prerequisites in each handler
- [ ] Refactor checkpoint write path to depend on one shared validated binding object
- [ ] Refactor approval creation path to use the same shared validation path when callback-bound
- [ ] Refactor replan request path to use the same shared validation path
- [ ] Refactor manifest-ack path to use the same identity vocabulary and error style
- [ ] Refactor worker-bundle access path to use the same validated binding object
- [ ] Refactor `publish_context_item` callback-bound publication to use the same validated binding object
- [ ] Remove route-level callback invariant logic from `api/routes/flows.py`

### 2.6 Standardize failure semantics and strictness rules
- [ ] Ensure all callback identity failures return a coherent conflict shape
- [ ] Remove bespoke mismatch messages where they duplicate the same invariant class
- [ ] Distinguish clearly between:
  - [ ] not found
  - [ ] stale binding
  - [ ] wrong session
  - [ ] wrong manifest lineage
  - [ ] stale attempt / inactive revision
  - [ ] unsupported trust lane / authority mismatch
- [ ] Require canonical UUID parsing by default in runtime/control paths
- [ ] If compatibility parsing is retained, narrow it to the one documented shim path only
- [ ] Log/observe compatibility parsing use so malformed senders stay visible

### 2.7 Collapse duplicate read-truth and query/load shapes
- [ ] Inventory repeated `selectinload(...)` graphs across runtime/services/routes/presenters
- [ ] Define a small set of named load profiles/query builders for:
  - [ ] runtime control/mutation
  - [ ] operator inspect/summary
  - [ ] audit/timeline
  - [ ] callback validation
  - [ ] worker bundle
- [ ] Replace repeated ad hoc loader forests with these profiles
- [ ] Treat “no endpoint/runtime path should hand-roll large relation trees when an equivalent load profile already exists” as a hard rule

### 2.8 Introduce one canonical runtime snapshot/view owner
- [ ] Create a dedicated runtime snapshot/view layer that owns selection of:
  - [ ] current node
  - [ ] current attempt
  - [ ] latest visible checkpoint
  - [ ] current session
  - [ ] current manifest
  - [ ] current wait/block reason
- [ ] Make presenters format only
- [ ] Remove or simplify any presenter logic that reconstructs runtime truth

### 2.9 Deduplicate checkpoint/helper semantics
- [ ] Introduce shared helpers for:
  - [ ] visible checkpoints
  - [ ] latest visible checkpoint
  - [ ] next visible checkpoint sequence
  - [ ] checkpoint summary payload rendering
- [ ] Unify manifest/checkpoint/context-item payload renderers where they are restating the same truth in different vocabularies

Exit condition:
- [ ] no checkpoint/approval/replan/worker-bundle/publish path manually reconstructs delegated identity rules inline
- [ ] no route is the sole owner of execution-truth validation
- [ ] runtime read truth is selected in one layer and formatted elsewhere
- [ ] duplicated load graphs are sharply reduced and named

---

## Phase 3 — task/runtime truth: bootstrap, resources, compose, materialization

Goal: one truth path, no blurry overlap.

Current pain:
- resource binding creation, task bootstrap, task-compose persistence, and task filesystem materialization are spread across:
  - `apps/api/app/runtime/resources.py`
  - `apps/api/app/runtime/packaging.py`
  - `apps/api/app/services/task_service.py`
  - pieces of `dispatcher.py`
- `task_service.py` imports underscore-prefixed helpers from `resources.py`
- `_task_key`/task dirs/materialization paths are re-derived across modules

### 3.1 Define the single ownership rule in code
- [ ] task resource bindings are the durable task resource truth
- [ ] `TaskCompose` is the persisted launch snapshot/view, not a co-equal resource truth layer
- [ ] runtime session/container-ish state is derived, not separately canonical
- [ ] manifest files are projections/audit artifacts, not authority
- [ ] task launch identity (task slug/key + directories + slot paths) has one canonical owner/helper/value object

### 3.2 Consolidate bootstrap and snapshot logic
- [ ] Merge task bootstrap + task resource binding + compose snapshot concerns into one concentrated public service layer (prefer one `task_runtime.py`-style owner over many tiny files)
- [ ] Ensure create-task, start-task-compose, upload refresh, and replan remint all use the same underlying bootstrap/snapshot primitives
- [ ] Remove duplicate derivation of:
  - [ ] task key / task slug
  - [ ] task directories
  - [ ] resource root URIs
  - [ ] context refs derived from task defaults
  - [ ] compose refresh/remint decisions

### 3.3 Make public-vs-private boundaries real
- [ ] Eliminate cross-module imports of underscore-prefixed helpers in touched areas
- [ ] Promote externally used helpers into a named public API or co-locate callers with the implementation
- [ ] Treat the current `task_service.py` ↔ `resources.py` boundary as one seam to redesign, not two adjacent files to tidy

### 3.4 Simplify `resources.py`
- [ ] Group helpers by lifecycle rather than many narrow ambient helpers
- [ ] Prefer a few clearer public operations such as:
  - [ ] ensure task bindings
  - [ ] resolve task refs
  - [ ] render manifest resource payload
- [ ] Reduce helper-heavy implicit contracts

### 3.5 Kill transitional helpers
- [ ] Remove `current_runtime_view()` early
- [ ] Remove code paths that no longer represent the chosen model
- [ ] Make task compose refresh/remint rules explicit after upload/bootstrap/replan
- [ ] Ensure no fake transitional helper remains in touched modules

### 3.6 Safety hardening for materialization
- [ ] Harden upload/materialized-file writes against symlink/root-escape cases
- [ ] Use resolved root-containment checks for task-owned writes
- [ ] Treat filesystem artifacts as audit-only unless explicitly modeled otherwise
- [ ] Prefer immutable task slug/path identity over mutable payload-derived naming where practical
- [ ] Add tests for:
  - [ ] symlinked parent dir escape
  - [ ] weird Unicode / separator edge cases in upload paths
  - [ ] task-key/task-slug mutation not relocating existing task storage

### 3.7 Add high-value tests
- [ ] fresh task bootstrap creates one primary workspace/context/manifest binding each
- [ ] task compose URIs reflect actual task bindings
- [ ] upload path respects task-owned target directories and updates compose truth if needed
- [ ] replan/remint decision matches runtime truth and API/operator surfaces

Exit condition:
- [ ] one developer can answer “where does task launch/resource truth live?” with one short answer
- [ ] no cross-module private-helper leakage remains in touched task/runtime code

---

## Phase 4 — orchestration + dispatch ownership

Goal: reduce duplicated orchestration logic, make ownership boundaries real, and freeze dispatch behavior.

Current pain:
- `apps/api/app/runtime/runner.py` is doing too much:
  - flow creation
  - revision creation
  - node graph materialization
  - node attempt creation/bootstrap
  - advancement loop
  - continue/pause/cancel/retry control
  - task bootstrap coupling
- readiness/resumability logic is split across runner, scheduler, and control
- dispatch triggers are implied from several paths
- bridge/manifest/session lifecycle ownership is still too split

### 4.1 Consolidate by real ownership, not by line-count chopping
- [ ] Prefer a few fatter, clearer ownership modules over many tiny ones
- [ ] Suggested target shape:
  - [ ] `runtime/flow_runtime.py` or equivalent concentrated owner for flow materialization + attempt lifecycle + advancement + operator actions
  - [ ] keep scheduler as the owner of readiness predicates
  - [ ] keep state transitions concentrated in one narrow place
- [ ] Only split further if tests/call sites show the boundary is already real

### 4.2 Make scheduler the sole owner of readiness semantics
- [ ] Reconcile `_next_unstarted_node` / scheduler release helpers
- [ ] Choose one canonical readiness decision path
- [ ] Choose one canonical resumability decision path
- [ ] Ensure runner/runtime consumes scheduler predicates instead of restating them

### 4.3 Freeze node-path truth
- [ ] Audit `_build_node_path` and graph materialization logic against intended workflow semantics
- [ ] Extract node-path derivation into an explicit named rule/helper
- [ ] Fix the normalization/path duplication debt for good
- [ ] Add tests that fail on path duplication regressions like:
  - [ ] `root.root.discovery`
  - [ ] repeated nested prefixes

### 4.4 Freeze dispatch-trigger policy
- [ ] Document and test exactly one canonical dispatch authority policy for:
  - [ ] operator continue
  - [ ] manifest-ack resume
  - [ ] watchdog wake
  - [ ] manual dispatch endpoint
- [ ] Ensure dispatch semantics are frozen before/alongside runner decomposition
- [ ] Remove duplicate or implicit dispatch triggers where possible

### 4.5 Reduce mutable orchestration sprawl
- [ ] Prefer smaller explicit transitions over long stateful branches with side effects
- [ ] Inventory every place that mutates:
  - [ ] attempt status
  - [ ] flow node state
  - [ ] node session status
  - [ ] context manifest status
  - [ ] approval expiry/status
- [ ] Concentrate these transitions behind fewer state/lifecycle entry points

### 4.6 Clarify bridge ownership
- [ ] Keep bridge code concentrated unless a split measurably reduces duplication
- [ ] If support extraction is needed, prefer one supporting type/helper module rather than several micro-files
- [ ] Separate internally (not necessarily by many files):
  - [ ] candidate selection
  - [ ] phase inference
  - [ ] envelope building
  - [ ] dispatch transport
  - [ ] payload/result shaping

### 4.7 Make envelope builders typed and minimal
- [ ] Introduce typed bootstrap/execution envelope builders
- [ ] Ensure the same delegated identity vocabulary is used everywhere
- [ ] Reduce repeated prose instructions where deterministic fields can carry the same truth
- [ ] Ensure no secrets/tokens appear in browser config, worker-facing envelopes, logs, or audit read models

### 4.8 Tighten bootstrap vs execution phase rules
- [ ] Make “projected manifest present → bootstrap phase” an explicit tested rule
- [ ] Make “acked manifest + running attempt → execution phase” an explicit tested rule
- [ ] Ensure impossible phase combinations fail closed
- [ ] Reduce phase selection to one explicit state table if possible

### 4.9 Make manifest/session lifecycle ownership explicit
- [ ] Define one clear owner path for:
  - [ ] session create/rebind/end
  - [ ] manifest project/ack/supersede
  - [ ] worker-visible manifest selection
  - [ ] worker bundle eligibility
- [ ] Reduce split ownership between dispatcher/control/routes/callback validators

### 4.10 Add dispatch integrity rules
- [ ] Persist or expose dispatch acceptance state explicitly
- [ ] Do not treat a session as effectively active without corresponding transport acceptance truth
- [ ] Add a detached-dispatch failure test where background dispatch creation fails after DB prep

### 4.11 Add dispatch/watchdog tests
- [ ] targeted dispatch candidate selection
- [ ] no openclaw-ready attempt available
- [ ] projected manifest path
- [ ] acked manifest path
- [ ] stale or ambiguous candidate rejection
- [ ] one candidate wake
- [ ] multiple blocked nodes escalate
- [ ] missing/rebound session escalates
- [ ] wake budget exhaustion escalates
- [ ] ambiguous timeout remains resumable but not auto-resolved blindly

Exit condition:
- [ ] runner/runtime orchestration has one clear owner path for readiness, dispatch, and lifecycle transitions
- [ ] bridge code is mostly orchestration glue around typed, tested helpers
- [ ] manifest/session lifecycle ownership is understandable as one coherent contract
- [ ] watchdog behavior can be explained as a small decision table

---

## Phase 5 — migration/schema checkpoint gate

This is a gate, not an optional later cleanup wish.

### 5.1 Audit runtime schema against intended model
- [ ] list live-required tables
- [ ] mark historical/transitional tables/columns
- [ ] prove nothing still depends on migration-era leftovers / nullable transitional shapes / historical aliases
- [ ] confirm partial indexes and portability rules for SQLite/Postgres

### 5.2 Rebaseline deliberately
- [ ] produce one clean canonical Alembic baseline matching the real current model
- [ ] ensure fresh SQLite boot works
- [ ] ensure fresh Postgres boot works
- [ ] ensure upgraded dev DB either works or the repo explicitly documents upgrade-history expectations after rebaseline
- [ ] ensure test suite uses the same truth, not silent per-backend assumptions

### 5.3 Add backend parity tests
- [ ] timestamps/defaults
- [ ] foreign keys
- [ ] unique partial indexes / role-specific constraints
- [ ] task resource binding constraints

Checkpoint gate:
- [ ] Do not claim the refactor stable until this migration/schema gate passes on both SQLite and Postgres.

---

## Phase 6 — compiler semantics hardening, not feature expansion

Goal: keep compiler clean while freezing merge semantics.

Current read:
- compiler structure is fairly good already
- risk is semantic creep, not total disorder
- runtime/replan currently reaches into compiler-private merge helpers

### 6.1 Freeze merge contract in tests
- [ ] role/workflow defaults merge
- [ ] task defaults merge
- [ ] node resources merge
- [ ] skill ref merge
- [ ] replan uses same merge/delete semantics as initial compile where intended

### 6.2 Reduce over-clever parent inference risk
- [ ] Review `normalize.py` parent assignment rules against target graph semantics
- [ ] Ensure parent inference cannot silently disagree with explicit hierarchy intent
- [ ] Add tests for nested ownership graphs and loop-style edges

### 6.3 Keep compiler pure and define a public semantics surface
- [ ] Ensure resolve/validate/normalize remain mostly pure transform steps
- [ ] Prevent runtime-specific repair logic from leaking into compiler internals
- [ ] Move replan-needed merge semantics out of private `_merge_*` helpers or formally expose them as a public compiler semantics surface
- [ ] Prevent non-compiler modules from depending on compiler-private utilities

Exit condition:
- [ ] compiler remains boring, predictable, and strongly test-defined
- [ ] runtime/replan no longer depends on compiler-private helper imports

---

## Phase 7 — registry and definition truth-sync

Goal: stop truth drift between docs, packaged defs, configured defs, and runtime behavior.

### 7.1 Align seeded workflow truth
- [x] Decide whether `max-complexity-review` seed becomes the full 06b target or docs step down to the compact truth
- [x] Document the current seeded-workflow/runtime/test contract drift clearly enough to stop guessing
- [ ] Do not leave them divergent
- [ ] Add a graph-shape test for the intended seeded workflow

Operator note (2026-04-20): current test/runtime truth is the full 06b-style seeded workflow under `apps/api/app/resources/definitions/workflows/max-complexity-review.yaml`, while repo-root `definitions/workflows/max-complexity-review.yaml` is still the compact variant. Current failures indicate the seeded 06b graph also over-constrains `root.implementation_loop` via dependency edges from `root.product.architecture` and `root.product.product_plan`, conflicting with the intended happy-path execution contract encoded by runtime tests.

### 7.2 Clarify definition source precedence
- [ ] packaged definitions
- [ ] configured filesystem definitions root
- [ ] publish/bootstrap rules
- [ ] external-current skill/version behavior
- [ ] definition precedence ordering is named explicitly in code/docs, not ambient

### 7.3 Add tests for definition identity and override precedence
- [ ] `id == filename stem`
- [ ] packaged + filesystem override ordering
- [ ] missing definitions fail clearly

### 7.4 Readability/style cleanup for registry owner boundaries
- [ ] Separate discovery/loading, precedence resolution, and publish/version mutation concerns enough that `registry_service.py` stops being a mixed historical layer

Exit condition:
- [ ] docs and seeded workflow truth stop disagreeing about the main exemplar graph
- [ ] definition precedence is explicit and test-backed

---

## Phase 8 — API, routes, and query surface cleanup

Goal: expose stable behavior, not internal accidents.

### 8.1 Group routes by stable capability and trust lane
- [ ] split/group route surfaces by:
  - [ ] task launch/import/upload
  - [ ] flow control
  - [ ] worker callback routes
  - [ ] operator audit/query
  - [ ] dispatch/watchdog controls if they remain distinct
  - [ ] internal-only surfaces
- [ ] make trust lane explicit for each route class:
  - [ ] public/operator
  - [ ] internal callback
  - [ ] worker-scoped read
  - [ ] browser console

### 8.2 Reduce deprecated drift
- [ ] quarantine historical routes clearly
- [ ] avoid keeping alternative ways to do the same unstable thing
- [ ] dedupe internal/public route bodies where they are functionally the same

### 8.3 Simplify read-model loading
- [ ] keep using named query builders/load profiles
- [ ] no endpoint/runtime path should hand-roll large relation trees when an equivalent load profile already exists

### 8.4 Browser/operator auth hardening
- [ ] replace browser-visible operator API-key bootstrap with a safer auth model or safer bootstrap contract
- [ ] document what credentials each route class accepts and why

Exit condition:
- [ ] API reflects stable product surfaces, not the repo’s refactor history
- [ ] browser/bootstrap trust is safer and explicit

---

## Phase 9 — internal naming cleanup

Goal: improve maintainability after semantics are stable.

### 9.1 Rename only after runtime truth is clean
- [ ] move internal `app.*` naming toward `autoclaw.*` if still desired
- [ ] keep imports and package resource discovery coherent
- [ ] avoid doing this during invariant-heavy refactors

### 9.2 Normalize ownership vocabulary before/alongside rename
- [ ] document what belongs in:
  - [ ] `runtime/`
  - [ ] `services/`
  - [ ] `api/routes/`
  - [ ] `registry/`
- [ ] ensure new code lands consistently before renaming sweeps

Exit condition:
- [ ] naming cleanup is a polish pass, not mixed into rescue work

---

## Concrete file-level targets

This section is advisory only.
Use it to spot likely hot files, not to drive the refactor as a file-by-file sweep.
The real implementation unit is a behavior/invariant slice.


### Highest-priority refactor targets
- [ ] `apps/api/app/runtime/runner.py`
- [ ] `apps/api/app/runtime/resources.py`
- [ ] `apps/api/app/services/openclaw_bridge.py`
- [ ] `apps/api/app/runtime/checkpoints.py`
- [ ] `apps/api/app/runtime/approvals.py`
- [ ] `apps/api/app/runtime/replan.py`
- [ ] `apps/api/app/runtime/dispatcher.py`
- [ ] `apps/api/app/runtime/watchdog.py`
- [ ] `apps/api/app/runtime/packaging.py`
- [ ] `apps/api/app/api/routes/flows.py`
- [ ] `apps/api/app/runtime/read_models.py`
- [ ] `apps/api/app/api/presenters/runtime.py`
- [ ] `apps/api/app/services/task_service.py`

### Secondary cleanup targets
- [ ] `apps/api/app/compiler/normalize.py`
- [ ] `apps/api/app/compiler/resolve.py`
- [ ] `apps/api/app/services/registry_service.py`
- [ ] `apps/api/app/main.py`
- [ ] `apps/api/app/core/ids.py`
- [ ] `apps/api/app/runtime/watchdog_queries.py`
- [ ] service/bootstrap scripts and user-service wiring if simplifying them removes accidental complexity
- [ ] stale tests that encode transitional behavior rather than the desired contract

---

## Suggested concentrated module outcomes

These names are suggestive, not mandatory. Prefer fewer, clearer ownership modules over file spam.

### Runtime core
- [ ] `runtime/execution_binding.py` — validated delegated identity / callback binding
- [ ] `runtime/flow_runtime.py` — concentrated owner for flow materialization + attempt lifecycle + advancement + operator actions
- [ ] `runtime/runtime_snapshot.py` or equivalent — canonical current runtime state selection / read truth
- [ ] `runtime/manifest_lifecycle.py` if and only if manifest/session ownership remains too split to keep in one clearer owner

### Task/runtime layer
- [ ] `runtime/task_runtime.py` — canonical owner for task bindings + task identity/dirs + compose snapshot + upload/replan refresh

### Bridge layer
- [ ] keep `services/openclaw_bridge.py` concentrated unless one support module measurably reduces duplication

Only introduce these if they genuinely reduce duplication. Do not create file spam.

---

## Anti-goals during implementation

- [ ] do not widen scope into major console/UI work during runtime stabilization
- [ ] do not add new workflow features before invariants are clean
- [ ] do not keep duplicate code paths “for now” if one canonical path is already chosen
- [ ] do not preserve accidental internal APIs just because they already exist
- [ ] do not mix internal package renaming with runtime invariant refactors
- [ ] do not multiply files without a measurable reduction in duplication or ambiguity
- [ ] do not let presenters/routes remain hidden owners of runtime truth
- [ ] do not preserve messy DB/test/service wiring just to avoid rewriting local/dev setup

---

## Definition of done for the refactor pass

I will consider this pass successful only if all of these are true:

- [ ] the test suite is trustworthy again before deep refactor work proceeds
- [ ] delegated execution identity logic is centralized and reused everywhere
- [ ] worker-bundle and publish-context validation share the same identity contract as callback writes
- [ ] runtime orchestration has one clear owner path for readiness, dispatch, and lifecycle transitions
- [ ] read-path truth is selected canonically and presenters no longer reconstruct it
- [ ] node path / graph materialization semantics are fixed and test-locked
- [ ] task-compose / task-resource / filesystem materialization truth is singular and coherent
- [ ] no duplicated launch-binding/remint decision logic remains across runtime/presenter/API
- [ ] watchdog logic is explicit and bounded
- [ ] dispatch acceptance truth is explicit enough to avoid “active without delivery fact” ambiguity
- [ ] the migration/schema checkpoint gate passes on both SQLite and Postgres
- [ ] seeded workflow/docs/runtime truth for the exemplar graph is aligned
- [ ] API/query surfaces are cleaner and less duplicative
- [ ] no cross-module imports of underscore-prefixed helpers remain in touched areas
- [ ] no obviously dead transitional helper remains in the touched areas
- [ ] browser/operator auth and secret exposure surfaces are safer and explicit
- [ ] routes are thin, presenters are presentation-only, and runtime logic is owned by runtime modules
- [ ] the canonical local start/test/service path is simpler and verified after the refactor

---

## Recommended immediate next implementation slice

This is the first real chunk. Treat it as the startup slice that turns the refactor from planning into execution.

1. [ ] Restore `make check-api` as a useful gate
2. [ ] Fix/rebaseline the current unit-level contract drift in registry precedence
3. [ ] Stabilize DB reset/deadlock behavior and backend parity so the test harness is boring
4. [ ] Land the mandatory short guardrail tests
5. [ ] Extract `execution_binding`
6. [ ] Centralize runtime snapshot/load truth

Only after that first chunk is real and verified should the refactor widen into task-runtime truth and broader orchestration ownership.
