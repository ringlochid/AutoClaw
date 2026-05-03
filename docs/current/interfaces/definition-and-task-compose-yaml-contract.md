# Current definition and task-compose YAML contract

Status: Current

Last verified: 2026-04-25

This page is the canonical current authoring contract for:

- role YAML
- policy YAML
- workflow YAML
- task-compose launch YAML

It uses a two-tier model:

- the full implemented schema from current code
- the smaller shipped subset used by current packaged definitions

## Core rule

Current contract means both:

- what the current schema and compiler actually accept and process
- what the current packaged definitions actually use in practice

## Keywords

- current YAML contract
- task compose current
- skill_refs current
- workflow seed
- task compose start
- shipped subset

Those are not identical today, so this page keeps them separate on purpose.

## Implemented current schema

### Role YAML

Current role schema is `RoleDefinitionSeed`.

Current fields are:

- `id`
- `kind`
- `description`
- `allowed_modes`
- `default_policy`
- `checkpoint_schema`
- `defaults`
- `skill_refs`

### Policy YAML

Current policy schema is `PolicyDefinitionSeed`.

Current fields are:

- `id`
- `description`
- `rules`

### Workflow YAML

Current workflow schema is `WorkflowDefinitionSeed`.

Current top-level fields are:

- `id`
- `description`
- `extends`
- `policy`
- `defaults`
- `task_defaults`
- `nodes`
- `edges`
- `skill_refs`

### Workflow node YAML

Current node schema is `WorkflowNodeSeed`.

Current fields are:

- `id`
- `role`
- `mode`
- `policy`
- `description`
- `metadata`
- `resources`
- `skill_refs`
- `children`

### Workflow resources

Current node resource schema allows:

- workspace mounts
- context refs
- optional image resource
- optional compose resource
- optional container resource

Current task-default resource schema allows:

- `workspace`
- `context`
- `manifests`

Each task-default binding may carry:

- `mode`
- `auto_create`
- `ref`
- `seed_from`
- `read_only`
- `required`
- `metadata`

### Task-compose launch YAML

Current public task-compose start schema is `TaskComposeStartCreate`.

Current fields are:

- `metadata`
  - `key`
  - `title`
  - `description`
  - `labels`
- `workflow`
  - `key`
  - `entrypoint`
- `input`
- `roots`
  - `workspace`
  - `context`
  - `manifests`
- `context_refs`
- `skill_dependencies`
  - `key`
  - `runtime_name`
  - `required`

## Current merge and validation semantics

### Workflow inheritance

Current `extends` resolution is recursive.

The current merge order is:

- resolve the base workflow first
- then merge the overriding workflow into it

### Defaults merge

Current workflow defaults merge:

- `metadata` by overlay
- `skill_refs` by provider/key identity, later layers winning

### Task-defaults merge

Current task-defaults merge per slot:

- later layer wins for `mode`
- nullable fields fall back to base when the override omits them
- `metadata` overlays

### Node merge

Current workflow nodes are flattened before merge.

Node merge is keyed by `id`, with later workflow layers overriding:

- role
- mode
- policy when set
- description when set
- metadata by overlay
- resources by typed merge
- `skill_refs` by provider/key identity

### Edge merge

Current workflow edges merge by:

- `from`
- `to`
- `kind`
- `when`

Exact duplicates are rejected later by validation.

### `children` flattening

Current schema supports recursive `children`.

Current flattening writes:

- child nodes into the flat node list
- `parent_node_key` into node metadata

### Role and policy resolution precedence

Current effective policy resolution is:

1. node policy
2. workflow policy
3. role default policy

Role resolution is direct from the node `role`.

### Task-default validation

Current validator enforces:

- `workspace` supports `use_existing`, `ensure_task_primary`, `clone_from`
- `context` supports `use_existing`, `ensure_task_primary`, `clone_from`, `seed_from`
- `manifests` supports `ensure_task_root`
- `seed_from` is only valid for context
- ref requirements depend on mode

### Resource ref validation

Current validator enforces:

- workspace refs must match current task workspace patterns
- context refs must match current task context patterns
- required image, compose, and container passthrough resources must have their required identifying fields

## Shipped current subset

### Roles actually shipped

Current packaged roles under `autoclaw-main/definitions/roles` use a small subset:

- `id`
- `kind`
- `description`
- `allowed_modes`
- `default_policy`
- `checkpoint_schema`
- small `defaults` bags on some roles

Known shipped role-default keys include:

- `replan_style`
- `prefers_local_retry_first`

### Policies actually shipped

Current packaged policies under `autoclaw-main/definitions/policies` use:

- `id`
- `description`
- `rules`

`rules` remains an open-ended current bag, but known shipped keys include:

- `approval_required_for`
- `max_child_local_retries`
- `replan_after_same_failure_count`
- `require_review_before_sync`

### Workflows actually shipped

Current packaged workflows under `autoclaw-main/definitions/workflows` are mostly:

- flat `nodes + edges`
- dotted node ids for hierarchy-like naming
- top-level `skill_refs`

Current packaged workflows do **not** normally use `children:` today, even though the implemented schema supports it.

### Task-compose in practice

Task-compose is a launch payload, not a packaged definition family.

Current practical usage is the public start payload shape:

- metadata
- workflow key
- input
- roots booleans
- context refs
- skill dependencies

## Out-of-contract tolerated legacy material

Some current packaged or historical workflow files still contain passive metadata such as:

- `can_spawn_children`
- `can_loop`
- other old control-shaping hints

These may still appear in current YAML and flow through metadata merge, but they are **not** part of the canonical current contract.

Current docs must not promote them into trusted current semantics.

## Minimal current examples

### Role

```yaml
id: reviewer
kind: worker
description: Lightweight review lane before sync or escalation.
allowed_modes:
  - review
default_policy: cautious
checkpoint_schema: review_result_v1
```

### Policy

```yaml
id: cautious
description: More conservative review and retry posture.
rules:
  max_child_local_retries: 1
  replan_after_same_failure_count: 1
  require_review_before_sync: true
```

### Workflow

```yaml
id: default-bugfix
description: Small default workflow pack.
nodes:
  - id: root
    role: planner-supervisor
    mode: plan
  - id: loop
    role: main-loop-worker
    mode: persistent_execute
edges:
  - from: root
    to: loop
skill_refs:
  - provider: openclaw
    key: contract-checker
    runtime_name: autoclaw-contract-checker
```

### Task compose

```yaml
metadata:
  title: Fix approval resume
  description: Reproduce and fix the approval resume path.
workflow:
  key: default-bugfix
input:
  source: test
roots:
  workspace: true
  context: true
  manifests: true
context_refs: []
skill_dependencies: []
```

## Evidence

- inspected code in `autoclaw-main/apps/api/app/schemas/registry.py`
- inspected code in `autoclaw-main/apps/api/app/schemas/runtime.py`
- inspected code in `autoclaw-main/apps/api/app/compiler/parse.py`
- inspected code in `autoclaw-main/apps/api/app/compiler/resolve.py`
- inspected code in `autoclaw-main/apps/api/app/compiler/validate.py`
- inspected code in `autoclaw-main/apps/api/app/compiler/nesting.py`
- inspected packaged definitions in `autoclaw-main/definitions/**`

## Related current pages

- [Definitions compiler and launch](definitions-compiler-and-launch.md)
- [Definition precedence and skill-version defaults](definition-precedence-and-skill-version-defaults.md)
- [Prompt layer and worker delivery](prompt-layer-and-worker-delivery.md)
- [Definition registry and publish lifecycle](definition-registry-and-publish-lifecycle.md)
- [Current registry bootstrap ingest and task file upload](current-definition-bootstrap-and-task-upload.md)
- [API surface and route map](api-surface-and-route-map.md)
- [CLI surface and config precedence](cli-surface-and-config-precedence.md)

## Redesign pointer

For the target authoring contracts, see [Workflow definition schema](../../redesign/workflows/workflow-definition-schema.md) and [Task compose schema](../../redesign/workflows/task-compose-schema.md).
