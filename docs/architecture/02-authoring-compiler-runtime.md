# Authoring, Compiler, and Runtime

## Source layer

- role definitions and versions
- policy definitions and versions
- workflow definitions and versions
- task intent (today carried by the `tasks` row and user input payload; a richer `TaskSpec` authoring surface may exist later as YAML or console form)
- skill references

Skill scope rule:

- role/workflow skill declarations are allowed as authoring/default layers
- compiled/runtime execution truth must be node-local effective skill bindings

## Definition, task, and runtime split

Keep these layers separate:

- **WorkflowDefinition** = reusable blueprint for a class of work
- **TaskSpec** = user-owned authoring/import-export shape for one concrete job
- **task** = normalized DB-backed runtime truth for one concrete job
- **CompiledPlan** = immutable resolved executable artifact derived from definition + task inputs + pinned refs
- **Flow** = live runtime execution instance derived from one compiled plan

The authoring surface may offer YAML import/export for task intent, but runtime truth should remain DB-backed task/flow state rather than raw YAML files.

Unless and until AutoClaw introduces a dedicated persisted `TaskSpec` model, **TaskSpec should be treated as an authoring/import-export shape or console projection over task rows**, not as a second live runtime source of truth.
There is no separate persisted live `TaskSpec` authority in the current target model.

## Canonical ownership and editability matrix

| Object | Primary owner | User/console editable? | Generated? | Runtime truth? | Typical storage |
| --- | --- | --- | --- | --- | --- |
| WorkflowDefinition / workflow version | operator / authoring | yes | no | no | definition YAML + version rows |
| Role / policy definitions | operator / authoring | yes | no | no | definition YAML + version rows |
| TaskSpec | user/operator authoring surface | yes | no | no | YAML import/export or console form |
| task | runtime/controller | indirectly, via normalized task edits | no | yes | `tasks` row + related bindings |
| CompiledPlan | compiler | no | yes | immutable compile truth / executable provenance, but not live runtime state | `compiled_plans*` tables |
| workspace root / context space / manifest artifact root | task/controller | task bindings editable, root contents materialized | partially | task-level resource truth | DB metadata + filesystem/object storage |
| context manifest | runtime/controller | no, inspect only | yes | yes, for attempt-scoped execution slice | `context_manifests` row, optional artifact copy |
| flow / flow_revision / node_attempt | runtime/controller | operator can act on runtime, not hand-edit core artifacts | yes | yes | runtime tables |

## Resource ownership model (recommended target)

Treat task resources and runtime projections as different things.

### Task-owned durable roots

A task should own durable resource roots that can survive retries and replans:

- **workspace root** = editable file tree for code, artifacts, patches, and scratch work
- **context space** = reusable wiki/knowledge layer for summaries, docs, facts, and prior decisions
- **manifest artifact root** = storage location for generated manifest files and related audit artifacts

Illustrative default storage layout:

- `data/tasks/{task_id}/workspace/`
- `data/tasks/{task_id}/context/`
- `data/tasks/{task_id}/manifests/`

### Flow-owned runtime projections

A flow or node attempt should own generated runtime projections:

- `context_manifest` rows are per `flow_node` / `node_attempt`
- delegated session mounts and visible context slices are derived from the task-owned roots plus compiled node bindings
- manifests are regenerated when a new attempt or adopted replan changes the effective execution slice

## Logical packaging/runtime layers (recommended next abstraction)

When backend tables, mounts, side effects, and worker-runtime variants start to multiply, AutoClaw should introduce a logical packaging/runtime layer.

This is not a mandate to make Docker the core product boundary.
It is a way to keep ownership clear even when the first backend is still an OpenClaw session plus local filesystem/object-storage roots.

### Task image

Immutable reusable seed for one class of task environment.

Typical contents:

- initial task-resource layout/defaults
- allowed service types
- bootstrap/input schema hints
- default policies or environment profile
- stable content hash

It should not be the mutable source of runtime truth for a live task.

### Task compose

Live task environment topology for one concrete task.

Typical responsibilities:

- own and wire task-scoped workspace/context/manifest roots
- own optional task-scoped services such as repo checkouts, browsers, caches, or databases
- expose typed binding slots that node execution can consume
- keep environment lifecycle separate from flow/node execution truth

This is the task-level equivalent of a compose topology.
It is a better fit for mutable task infrastructure than treating a live task itself as an image.

### Runtime image

Immutable node execution contract derived from compiled effective-node meaning.

Typical contents:

- effective role / mode / policy
- allowed and required skill bindings
- required resource slots and mount schema
- backend hint such as `openclaw_session`, `sandbox`, or later `oci`
- bootstrap/execute contract
- stable content hash

It answers: what kind of worker this node needs.

### Runtime container

Live execution instance for one `flow_node` / `node_session` binding.

Typical responsibilities:

- bind a runtime image to one task/flow/node
- bind task-compose resources into runtime slots
- track bootstrap state, manifest ack state, current backend handle, and lifecycle state
- expose typed runtime events and raw logs for debugging

Recommended lifetime rule:

- container scope aligns with the logical node identity, not every retry attempt
- retries may reuse the same runtime container when the node identity is unchanged
- replans that replace the node should create a new runtime container

### Ownership boundary

Keep this split explicit:

- task resources remain task-owned durable truth
- task compose wires task resources/services into a usable environment
- runtime image declares what a node execution instance requires
- runtime container is the live instantiated worker binding
- flow / attempt / checkpoint / manifest remain orchestration truth

### Logs and events

Runtime containers should expose both:

- typed runtime events for operator/query-model inspection
- raw log streams for debugging and replay context

But logs must not become the source of runtime truth.
Control truth still lives in typed task/flow/node/attempt/checkpoint/manifest state.

### Why this layer is worth having

Without this split, the system tends to blur:

- template vs live environment
- task-owned resources vs node-scoped runtime mounts
- worker session reuse vs fresh runtime instantiation
- audit truth vs transcript/debug text

That leads to the usual complaints:

- users cannot tell why retry/replan behaved differently
- workers do not get a clear typed contract for resources and lifecycle
- the controller accumulates backend-specific cleanup/reuse hacks
- operator inspection drifts toward transcript scraping instead of typed runtime state

## Resource wiring responsibilities

Use one clear split:

- **workflow** owns the main resource intent and task bootstrap defaults
- **role** may provide light reusable resource-profile hints only
- **policy** enforces visibility, writability, sharing, and publishback rules
- **manifest** is generated runtime output, not hand-authored definition input

Recommended binding modes:

- `use_existing` = explicit key/reference that must resolve
- `ensure_task_primary` = ensure a task-owned primary root exists, auto-creating it at task bootstrap if needed
- `ensure_task_root` = ensure a task-owned storage root exists for generated artifacts such as manifests
- `clone_from` = create task-owned materialization from an existing reusable source
- `seed_from` = populate a task-owned context space from task input, workspace docs, or controller summaries

Validation rule:

- explicit references such as a workspace/context key must resolve in the first phase where the needed identifier is actually known
- `ensure_*` modes validate configuration shape at definition compile time and are materialized by runtime bootstrap if absent
- missing required resources should fail closed, not silently degrade into prompt luck

## Validation phases (recommended target)

Keep two explicit validation phases:

### 1. Definition compile validation

This phase validates reusable definition semantics before a concrete task exists.

It should validate:

- workflow/role/policy syntax and merge semantics
- allowed resource binding modes
- shape of `ensure_task_primary`, `ensure_task_root`, and `seed_from` directives
- skill reference shape and any definition-time-resolvable pins

It should **not** pretend to resolve task-specific bindings that depend on a concrete task or task-linked roots.

### 2. Task instantiation / replan validation

This phase runs when task inputs and task-linked resources are known.

It should validate:

- explicit `use_existing` / `clone_from` resource references
- any task-selected shared workspace/context keys
- replan-introduced resource references against the currently active task and flow revision
- whether required skills/resources are still resolvable for the delegated session

Compiled plans should therefore freeze **definition-level intent and resolved definition provenance**.
Task-owned roots remain runtime bindings, even when a compiled node stores validated symbolic refs or resolved external keys in its effective payload for inspection.

## Effective-payload merge contract (minimum target)

Outside of storage shape, the compiler contract should stay explicit:

- scalar fields such as `mode` or `description` use highest-precedence replace semantics
- structured maps must document deep-merge vs replace field by field
- keyed lists such as skill bindings or resource bindings merge by stable identity, not by raw array position
- replan patches use the same merge/delete/null rules as normal compilation, not a second ad hoc model

## Context substrate boundary

Keep the context model split explicit:

- **context spaces** store durable curated knowledge substrates such as wiki pages, summaries, docs, and reusable notes
- **context items** store published runtime metadata about facts, decisions, artifacts, and notes emitted by tasks/flows/nodes
- **context manifests** project one attempt-scoped visible slice from those sources for delegated execution

Curated long-lived knowledge should live in context spaces.
`context_items` are published runtime metadata records, not a second interchangeable wiki store.
A context space is not the same thing as a context manifest, and a context manifest is not the canonical home of long-lived curated knowledge.

## Illustrative authoring example (recommended target)

A workflow may describe task bootstrap defaults and per-node resource intent:

```yaml
id: default-bugfix-with-task-roots
description: Default bugfix workflow with task resource bootstrap.

task_defaults:
  workspace:
    mode: ensure_task_primary
    auto_create: true
  context:
    mode: ensure_task_primary
    auto_create: true
    seed_from:
      - task_input
      - workspace_docs
  manifests:
    mode: ensure_task_root
    auto_create: true

nodes:
  - id: root
    role: planner-supervisor
    mode: plan
    resources:
      workspace:
        mounts:
          - ref: task.primary_workspace
            access: read_only
      context:
        refs:
          - ref: task.primary_context

  - id: loop
    role: main-loop-worker
    mode: persistent_execute
    resources:
      workspace:
        mounts:
          - ref: task.primary_workspace
            access: read_write
      context:
        refs:
          - ref: task.primary_context
```

A user-authored task spec or console form may stay smaller:

```yaml
title: Fix approval resume bug
workflow_ref:
  key: default-bugfix-with-task-roots
workspace:
  mode: ensure_task_primary
context:
  mode: ensure_task_primary
input:
  repo: autoclaw
  goal: Investigate why approval resolution does not resume node execution.
```

## Compiler layer

The compiler:

- validates source definitions
- resolves pinned versions
- computes an explicit effective-node artifact from role / workflow / node / replan inputs
- validates merged effective-node semantics, not only raw graph structure
- normalizes graph structure
- emits immutable `compiled_plans`, `compiled_plan_nodes`, and `compiled_plan_edges`

Each compiled node carries version provenance and effective execution meaning:

- `role_version_id`
- `policy_version_id`
- `skill_bindings[*].skill_version_id`
- effective mode / metadata / skill state after merge
- effective resource intent (for example workspace/context bindings) inside the compiled effective payload

Graph/workflow-scope skill declarations should therefore compile into node-local effective skill bindings rather than remaining graph-scoped at runtime.

## Skill reference contract (recommended target)

AutoClaw should treat skills as **pinned OpenClaw artifacts plus extracted manifest summary**, not as a second skill-logic format.

Definition/registry storage should keep enough information to pin, inspect, search, and materialize a skill safely:

- `provider`
- `key`
- `version_label`
- `skill_version_id`
- `runtime_name` (the exact `name` from `SKILL.md`)
- `source_uri` / `source_ref`
- `artifact_ref` (for example `.skill` blob or unpacked skill directory reference)
- `artifact_sha256`
- `manifest_summary` parsed from `SKILL.md` frontmatter
  - `name`
  - `description`
  - `user-invocable`
  - `disable-model-invocation`
  - selected `metadata.openclaw.*` fields such as `primaryEnv`, `requires`, and `install`

The compiler should collapse role/workflow/node/replan skill declarations into a **node-local effective binding set**.
Each resolved binding should be strong enough to drive runtime dispatch without re-reading authoring defaults.

Illustrative binding shape:

```json
{
  "provider": "openclaw",
  "key": "contract-checker",
  "runtime_name": "contract-checker",
  "version_label": "2026-04-17",
  "skill_version_id": "8c3b4c2d-...",
  "source_ref": "clawhub://openclaw/contract-checker@2026-04-17",
  "artifact_ref": "s3://autoclaw-skills/contract-checker/2026-04-17.skill",
  "artifact_sha256": "abc123...",
  "manifest": {
    "name": "contract-checker",
    "description": "Check frontend/backend contract drift",
    "user_invocable": false,
    "disable_model_invocation": false,
    "metadata": {
      "openclaw": {
        "primaryEnv": "OPENAI_API_KEY",
        "requires": {
          "bins": ["node"],
          "env": ["OPENAI_API_KEY"]
        }
      }
    }
  },
  "state": "required",
  "provenance": {
    "effective_layer": "workflow"
  }
}
```

## Runtime layer (target)

The runtime should:

1. create or load a task from user-owned intent
2. resolve or auto-create task-owned workspace/context/manifest artifact roots according to the selected binding mode
3. create a `flow` for a task
4. create an initial `flow_revision` from a `compiled_plan`
5. materialize `flow_nodes` and `flow_edges`
6. pick runnable nodes
7. create `node_attempts` for actual execution slices
8. project a policy-filtered context slice for the node attempt
9. persist a `context_manifest` for that projected slice
10. resolve the node-local effective skill binding set for dispatch
11. resolve the node-local effective workspace/context bindings for dispatch
12. materialize or verify the pinned OpenClaw skill packages and required task resources for the delegated session
13. dispatch bootstrap instructions to OpenClaw for read + acknowledge
14. only after successful context acknowledgement, and only with required skills/resources available, dispatch delegated node work to OpenClaw with a session-level skill filter and resource mounts that reflect the node-local bindings
15. persist `node_checkpoints`
16. advance node/flow state only from checkpoint or operator events

## Context bootstrap boundary

AutoClaw should not rely on "please read this first" prompt wording alone.

Before delegated execution:

- the controller projects a node-scoped context slice from shared/private workspace items
- the slice is filtered by role, skill bindings, resource bindings, and policy visibility
- the controller persists a `context_manifest` containing required and optional items plus hashes
- the controller includes the node-local skill contract in the manifest or sibling dispatch payload, including required/allowed/blocked runtime skill names plus pinned binding summaries
- the controller includes the resolved workspace mounts and context references for that node attempt
- required skills and required task resources are materialized in the delegated session before execute-phase work starts
- the delegated session enters a bootstrap/read phase first

Execution should begin only after the delegated node acknowledges the manifest.

That acknowledgement may be recorded in manifest metadata directly or linked to a checkpoint, but it is a controller-enforced gate rather than a soft convention.

## Skill and resource availability rule

If a node declares a skill or resource as `required` and AutoClaw cannot materialize or verify it for the delegated session, the node should block before execute rather than relying on prompt luck.

## Replan rule

Replans should preserve task-owned durable roots when possible:

- task-owned workspace/context/manifest artifact roots remain stable across retries and adopted replans unless the replan explicitly changes the binding target
- explicit new resource references introduced by a replan must validate before candidate adoption
- auto-create of new durable roots should be limited to task bootstrap unless a later explicit operator-visible task rebinding flow is introduced
- manifests are regenerated for the new revision/attempt set
- a new attempt or a newly projected manifest always requires a fresh ack, even if the delegated session is reused
- prior manifests and node sessions remain auditable even after replacement or retirement

## Hard boundary

- Runtime never executes raw source definitions directly.
- Runtime never mutates graph shape in place during a node call.
- Structural changes go through proposal -> validate -> compile -> adopt.
- Shared workspace publication should happen at checkpoint boundaries or explicit operator action, not as uncontrolled transcript residue.

## Legacy note

The old `run -> attempt -> flow` shape is historical only.
The live runtime contract is `task -> flow -> flow_revision -> flow_node -> node_attempt`.
