# 10 — Phase 10: Effective-node Compiler Semantics and Authoring Safety

This phase remains historical. Any still-open non-UI backend/runtime work that depends on these semantics now belongs to **Phase 13**.

## Goal

Finish the compiler contract so compiled output is not only deterministic, but also semantically explicit, inspectable, and safe for richer authoring patterns.

Target end state:

- the compiler computes an explicit **effective node** for each workflow node
- merge precedence across role / workflow / node / replan inputs is defined, not implied
- role / workflow / node descriptions are explicit and inspectable, including a first-class node description rather than burying meaning in opaque metadata
- validation runs on the merged effective node, not just on raw graph structure
- compiled output remains canonical, hash-stable, and inspectable
- unsupported or ambiguous authoring patterns fail fast instead of being guessed at compile time

## Why this phase exists

Phase 2 established the baseline deterministic compiler contract:

- published definitions are resolved to pinned versions
- graph structure is normalized and persisted as immutable compiled output
- repeated compiles from equivalent inputs should stay stable

That baseline remains correct and useful.

But the current compiler no longer stops at **pinned lineage** alone.
Current code/tests now prove a baseline semantic contract:

- workflow/default/node merge is field-aware for the current defaults, resources, and skill-reference lanes
- compiled nodes persist an `effective_payload` that carries task defaults and node-local resource intent
- preview/compile validation fails closed for ambiguous required image/compose/container passthroughs and invalid task-default shapes

That baseline closes the immediate runtime dependency.
The remaining Phase 10 work is broader follow-through from that baseline, not starting from zero:

- richer role/policy/node provenance and node-description inspection
- deeper skill and task-resource follow-through across authoring surfaces
- stronger compile inspection/debug surfaces

## Why this is a separate later phase

This work should not block:

- **Phase 8** bridge hardening
- **Phase 9** packaging / local-first productization

Those phases are already large and have clearer product/runtime urgency.

Phase 10 exists to finish the compiler properly once the bridge and install story are real enough that stronger authoring semantics are worth locking down.

## Current problem statement

Today the compiler is materially stronger for current controlled definitions, but the full authoring/compiler contract is still thinner than the roadmap and architecture want.

Risks if this remains unfinished too long:

- silent inheritance mistakes
- workflow/node skill application that is broader than intended
- unclear override precedence
- future drift between author intent and compiled runtime meaning
- runtime-side pressure to reinterpret source definitions that should have been made explicit at compile time

The issue is not primarily randomness.
The issue is **under-specified merge semantics**.

## In scope

### 1. Define explicit merge precedence

For any field that may come from multiple layers, the compiler should apply one explicit precedence order.

Target merge layers:

1. role defaults
2. workflow defaults
3. node-local overrides
4. replan patch overrides

This does **not** mean every field must support merging.
Some fields should stay replace-only.
The important part is that each field has one documented rule.

Minimum normative merge table:

- scalar fields such as `mode` or `description`: replace by highest-precedence non-null value
- maps such as structured metadata: documented deep-merge or replace, field by field
- keyed lists such as skill bindings: merge by stable identity (`provider` + `key`) with conflict rules, not append-by-accident
- keyed resource bindings: merge by stable binding identity/role, not raw array position
- explicit delete/remove semantics must be documented for replan patches and node overrides
- `null` must have one documented meaning per field (`inherit`, `clear`, or invalid), not an implicit guess

### 2. Introduce effective-node compilation

For each node, compile a deterministic effective artifact that includes at least:

- node identity
- effective role key + pinned role version
- effective policy key + pinned policy version
- effective mode
- effective workflow/role/node description context, including a first-class node description
- effective skill bindings
- effective metadata / execution hints
- provenance showing which layer supplied each merged field when useful for inspection

This effective-node artifact becomes the semantic truth for runtime handoff.

That runtime-facing meaning should also be strong enough to drive a stable compiled execution contract:

- backend hint
- required resource slots
- skill contract
- bootstrap/execute contract
- node-local provenance needed for inspection/debugging

### 3. Make skill binding authoring-flexible but runtime node-local

Skill scope should be treated as **both** graph/workflow-scope and node-scope, but with different jobs.

Authoring-time meaning:

- role-level skill preferences may provide reusable defaults
- workflow-level defaults may provide a common pack/envelope for the whole graph
- node-level overrides may require / prefer / block skills for one execution lane

Runtime/compiled meaning:

- the compiler must collapse those inputs into a **node-local effective skill binding set**
- runtime and OpenClaw dispatch should consume the node-local effective binding, not raw workflow-scope defaults
- workflow/graph-scope skills remain an authoring/defaulting layer, not the final execution truth

The compiler should reject conflicting skill states such as a skill being both required and blocked.

### 3.5 Split definition compile validation from task-time validation

Do not blur reusable-definition validation with task-known runtime validation.

Definition compile validation should handle:

- merge semantics
- allowed binding modes
- shape of `ensure_task_primary`, `ensure_task_root`, and `seed_from`
- definition-time-resolvable references and pins

Task instantiation / replan validation should handle:

- explicit task-selected `use_existing` / `clone_from` resource refs
- task-linked shared roots
- currently active task/flow bindings
- replan-introduced explicit refs against the current active base revision

### 4. Add merged semantic validation

Keep current structural validation, but add a second validation pass against the effective node.

Examples:

- node mode must still be allowed by the effective role
- required skill references must resolve
- explicit task-known workspace/context references must resolve during task instantiation or replan validation
- required / blocked skill conflicts fail compile
- resource binding modes such as `use_existing`, `ensure_task_primary`, `ensure_task_root`, `clone_from`, and `seed_from` must have documented semantics and valid shapes
- metadata required by a selected mode or policy must be present
- override combinations that create impossible execution semantics fail fast
- task-compose/runtime binding must stay explicit enough that runtime does not have to guess how node requirements map onto live resources

### 5. Preserve deterministic compiled output

The richer merge model must not weaken determinism.

Required properties:

- canonical JSON serialization
- stable field ordering
- stable list ordering where semantics permit it
- stable `plan_hash` for equivalent inputs
- immutable compiled output once persisted

Determinism should come from one explicit merge-and-normalize path, not from running the same compiler twice and hoping results match.

### 6. Add compile inspection surfaces for effective nodes

Compiled output should be easy to inspect for debugging and audit.

Minimum desired inspection value:

- exact effective node payload by `compiled_plan_id`
- exact effective skill bindings per node
- exact effective workspace/context bindings per node
- provenance of pinned role/policy/skill versions and resolved resource references
- visible role/workflow/node description context for each compiled node
- enough visibility to explain why a node compiled the way it did without rereading raw source files manually

### 7. Fail fast on unsupported authoring

If authoring semantics are not implemented cleanly, the compiler should reject them instead of guessing.

Examples:

- unsupported partial merge patterns
- ambiguous override combinations
- role/workflow/node fields that look mergeable but do not yet have defined semantics

The compiler should remain strict rather than permissive here.

## Non-goals

This phase should **not**:

- re-litigate the flow-first runtime model
- move control truth from AutoClaw into OpenClaw
- make runtime execution depend on raw source definitions
- introduce a second orchestration layer parallel to `flow` / `flow_revision` / `flow_node`
- turn compile safety into repeated compile passes instead of one explicit canonical merge path

## Suggested implementation shape

### Compiler pipeline target

Move toward this explicit pipeline:

1. parse published definitions
2. resolve pinned versions
3. compute effective node artifacts
4. validate effective nodes + graph structure
5. normalize canonical compiled output
6. compute stable plan hash
7. persist immutable compiled plan

### Data/model direction

The compiled plan should remain the immutable handoff artifact.

Possible implementation options:

- expand `compiled_plan_nodes` to store richer effective-node JSON
- or keep the current relational columns and add a dedicated `effective_payload` JSON field

The exact storage split can vary, but runtime should be able to read one compiled node and know its final meaning without reinterpreting source definitions.

### Authoring rules direction

Prefer explicit authoring contracts such as:

- replace vs merge semantics documented per field
- skill precedence documented separately from generic metadata precedence
- resource-binding precedence documented separately from generic metadata precedence
- role/workflow skill declarations treated as defaults, with node-local effective skill bindings as the execution truth
- task resource intent treated separately from runtime manifests
- replan patch semantics aligned with the same effective-node merge rules rather than inventing a second model
- only `ensure_*` modes may auto-create durable task roots, with deterministic keys and auditable creation events
- auto-create should be limited to task bootstrap unless a later explicit operator-visible task rebinding flow is designed

## Verification strategy

### 1. Golden compile tests

Add snapshot/golden tests that assert:

- same inputs -> same compiled node payloads
- same inputs -> same `plan_hash`
- equivalent authoring forms -> equivalent compiled output where intended

### 2. Negative compile tests

Add tests for:

- conflicting skill declarations
- missing explicit workspace/context references
- illegal `ensure_*` / `use_existing` resource mode combinations
- stale-base replan adoption attempts
- unsupported override semantics
- illegal mode/policy/role combinations
- ambiguous inheritance patterns

### 3. Inspection/debug tests

Add tests that prove inspection surfaces expose enough effective-node detail to debug compile results without runtime transcript dependence.

## Success criteria

Phase 10 is complete when all of these are true:

- compiled nodes carry explicit effective execution meaning, not only lineage ids
- role / workflow / node / replan precedence is documented and enforced
- node description is a first-class compiled/inspectable field rather than an opaque metadata convention
- graph/workflow-scope skill defaults compile into node-local effective skill bindings for execution
- workspace/context intent compiles into explicit node-local effective resource bindings
- compiled output is strong enough to drive runtime dispatch without re-reading raw workflow/role defaults at dispatch time
- bad semantic combinations fail at compile time
- repeated compiles from equivalent inputs remain stable and inspectable
- runtime can rely on compiled output alone without reinterpreting raw authoring definitions

## Migration note

This phase strengthens the compiler contract.
It does **not** invalidate the flow-first runtime or the OpenClaw bridge split.

The intended end state remains:

- AutoClaw owns graph/control truth
- OpenClaw owns delegated execution sessions/tools/skills
- compiled plans are the deterministic handoff between authoring intent and runtime state
