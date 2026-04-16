# 10 — Phase 10: Effective-node Compiler Semantics and Authoring Safety

## Goal

Finish the compiler contract so compiled output is not only deterministic, but also semantically explicit, inspectable, and safe for richer authoring patterns.

Target end state:

- the compiler computes an explicit **effective node** for each workflow node
- merge precedence across role / workflow / node / replan inputs is defined, not implied
- validation runs on the merged effective node, not just on raw graph structure
- compiled output remains canonical, hash-stable, and inspectable
- unsupported or ambiguous authoring patterns fail fast instead of being guessed at compile time

## Why this phase exists

Phase 2 established the baseline deterministic compiler contract:

- published definitions are resolved to pinned versions
- graph structure is normalized and persisted as immutable compiled output
- repeated compiles from equivalent inputs should stay stable

That baseline remains correct and useful.

But the current compiler still leaves an important semantic gap between **pinned lineage** and **fully explicit executable meaning**:

- workflow inheritance is still shallow rather than field-aware
- skill bindings are currently too coarse for node-local execution semantics
- role / workflow / node overrides do not yet compile into a single effective-node artifact
- validation focuses mostly on graph/source integrity rather than merged execution semantics

That is acceptable for the current narrow v1 definitions.
It is not strong enough as the long-term authoring/compiler contract if AutoClaw is going to support richer workflow packs, role defaults, node-level overrides, and safer externalized definitions.

## Why this is a separate later phase

This work should not block:

- **Phase 8** bridge hardening
- **Phase 9** packaging / local-first productization

Those phases are already large and have clearer product/runtime urgency.

Phase 10 exists to finish the compiler properly once the bridge and install story are real enough that stronger authoring semantics are worth locking down.

## Current problem statement

Today the compiler is deterministic enough for current controlled definitions, but the semantic contract is still thinner than the roadmap and architecture want.

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

### 2. Introduce effective-node compilation

For each node, compile a deterministic effective artifact that includes at least:

- node identity
- effective role key + pinned role version
- effective policy key + pinned policy version
- effective mode
- effective skill bindings
- effective metadata / execution hints
- provenance showing which layer supplied each merged field when useful for inspection

This effective-node artifact becomes the semantic truth for runtime handoff.

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

### 4. Add merged semantic validation

Keep current structural validation, but add a second validation pass against the effective node.

Examples:

- node mode must still be allowed by the effective role
- required skill references must resolve
- required / blocked skill conflicts fail compile
- metadata required by a selected mode or policy must be present
- override combinations that create impossible execution semantics fail fast

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
- provenance of pinned role/policy/skill versions
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
- role/workflow skill declarations treated as defaults, with node-local effective skill bindings as the execution truth
- replan patch semantics aligned with the same effective-node merge rules rather than inventing a second model

## Verification strategy

### 1. Golden compile tests

Add snapshot/golden tests that assert:

- same inputs -> same compiled node payloads
- same inputs -> same `plan_hash`
- equivalent authoring forms -> equivalent compiled output where intended

### 2. Negative compile tests

Add tests for:

- conflicting skill declarations
- unsupported override semantics
- illegal mode/policy/role combinations
- ambiguous inheritance patterns

### 3. Inspection/debug tests

Add tests that prove inspection surfaces expose enough effective-node detail to debug compile results without runtime transcript dependence.

## Success criteria

Phase 10 is complete when all of these are true:

- compiled nodes carry explicit effective execution meaning, not only lineage ids
- role / workflow / node / replan precedence is documented and enforced
- graph/workflow-scope skill defaults compile into node-local effective skill bindings for execution
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
