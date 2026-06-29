# Definition and task-compose YAML contract

Status: Reference

Last verified: 2026-05-12

This page is the shipped authoring contract for:

- role YAML
- policy YAML
- workflow YAML
- task-compose launch input

For copyable public examples that stay close to the shipped fixtures, use [Definitions reference](../definitions/README.md).

Current code already uses the tree-only workflow model. Older `edges`/`extends`/`skill_refs`/flat-flow docs are stale and should not be treated as current truth.

## Core rule

Current contract means the shapes accepted by the definition models plus the mirrored seed fixtures used for bootstrap and examples.

Once seeding finishes, compiler and runtime paths read definition truth from the registry rows rather than rereading the seed trees as live authority.

## Implemented current schema

Current file wrappers are:

- `RoleDefinitionFile`
- `PolicyDefinitionFile`
- `WorkflowDefinitionFile`

Their runtime/service inputs use the same payload shapes without the top-level `kind` field.

### Role YAML

Current role schema is `RoleDefinitionFile`.

Current fields are:

- `kind`
- `id`
- `title`
- `description`
- `allowed_node_kinds`
- `labels`
- `instruction`

`allowed_node_kinds` is a non-empty list of `root | parent | worker`. `title` is optional display metadata. `labels` is an optional list of portable search or grouping tags and defaults to an empty list.

`description` should explain the reusable role purpose. `instruction` should explain the role's mode, evidence posture, criteria posture, and checkpoint expectations without assuming the node already knows AutoClaw terms.

### Policy YAML

Current policy schema is `PolicyDefinitionFile`.

Current fields are:

- `kind`
- `id`
- `title`
- `description`
- `applies_to`
- `budget_spec`
- `capabilities`
- `labels`
- `instruction`

`budget_spec` currently allows:

- `child_assignment_limit`
- `retry_limit`

`capabilities` currently allows:

- `human_request`
  - `mode`: `deny | allow`
  - `allowed_kinds`: `direction | approval | input | review`
- `command_run`: `deny | allow`

Current validator rules include:

- `applies_to` must not repeat values
- `child_assignment_limit` requires `root` or `parent`
- `retry_limit` requires `worker`
- one policy budget spec must not mix both limits
- omitted `capabilities.human_request` defaults to `mode: deny`
- omitted `capabilities.command_run` defaults to `deny`
- `capabilities.human_request.mode: allow` requires non-empty `allowed_kinds`
- `capabilities.human_request.mode: deny` grants no portable human-request permission

`description` should summarize policy purpose. `instruction` should explain constraints, evidence gates, capabilities, allowed posture, and checkpoint expectations.

### Workflow YAML

Current workflow schema is `WorkflowDefinitionFile`.

Current top-level fields are:

- `kind`
- `id`
- `description`
- `root`

Current root node shape is:

- `id` and it must be `root`
- `title`
- `role`
- `policy`
- `provider_preference`
- `description`
- `instruction`
- `produces`
- `criteria`
- `child_defaults`
- `children`

Current non-root node shape is:

- `id`
- `title`
- `role`
- `policy`
- `provider_preference`
- `description`
- `instruction`
- `consumes`
- `produces`
- `criteria`
- `child_defaults`
- `children`

`title` is optional node display metadata. `instruction` is optional node-local prompt guidance. `provider_preference`, when present, must be one of `openclaw`, `codex`, or `claude`; omission means runtime resolves through the machine-local default provider.

Node `description` is node purpose: why this node exists and what success means. Node `instruction` is node-local guidance: how to behave for this node without replacing role or policy guidance. Mode words such as planning, implementation, review, verification, failure analysis, replan, or release belong in role/policy/node instruction text, not in a separate workflow field.

### Consume, produce, criteria, and child-default shapes

Current consume shape is `ConsumeBuckets`:

- `artifacts`
- `criteria`

Each selector is:

- `slot`
- `required`

Current produce shape is `ProduceBuckets`:

- `artifacts`

Each produced artifact declaration is:

- `slot`
- `description`
- `file_hint`

Current criteria declaration is:

- `slot`
- `description`
- `criteria`

Current child-default shape is:

- `consumes`
- `criteria`

`child_defaults.criteria` must reference criteria declared on that same node.

Concept meanings:

- `criteria` are hard acceptance or guardrail requirements
- `consumes` are durable artifact or criteria slots the node needs to read
- `produces` are required output slots, not already-published refs
- runtime `assignment`, `checkpoint`, `consumed_durable_refs`, `transient_refs`, and boundaries are generated during execution and are not authored in workflow YAML

### Task-compose launch input

Current launch input shape is `TaskComposeInput`.

Current fields are:

- `task`
  - `key`
  - `title`
  - `summary`
  - `instruction`
- `workflow`
  - `key`
- `roots`
  - `workspace`
  - `context`

Each current root binding uses:

- `mode`
- `host_path`

Current root modes are:

- `ensure_task_default`
- `ensure_host_path`
- `use_existing_host`

The current task-compose model is the runtime launch contract. The shipped router does not expose a public `/tasks/composes/start` surface today.

## Current validation semantics

Current workflow validation enforces:

- tree-only authoring rooted at `root`
- unique node ids
- unique produced artifact slots across the workflow
- unique criteria slots across the workflow
- consume selectors must resolve to declared artifact or criteria providers
- child-default consume selectors participate in dependency validation
- child-default criteria refs must be local to the declaring node
- dependency graph must be acyclic
- role and policy ids can be validated against the current registry when a registry-backed validation context is provided

Current removed/stale fields are rejected by schema validation, including:

- `inputs`
- `edges`
- top-level `skill_refs`
- node-level `skill_refs`
- root-level `consumes`

## Shipped current fixtures

Current shipped workflow fixtures are:

- `bugfix-review-release`
- `core-only-build`
- `feature-implementation`
- `idea-discovery`
- `minimal-implement-change`
- `normal-parent-first-release`
- `maximal-parent-first-release`
- `delivery-batch`
- `marketing-campaign`
- `mvp-build`
- `planning-only`
- `project-management-delivery`

The packaged bootstrap mirror under `apps/api/src/autoclaw/definitions/seeds/workflows/*.yaml` is the committed authored and shipped seed source for those fixtures. No repo-root definitions mirror is required by shipped paths.

## Minimal shape example

```yaml
kind: workflow
id: minimal-implement-change
description: Execute one bounded engineering change under parent ownership with explicit purpose, evidence, criteria, and verification handoff.
root:
  id: root
  role: planning_lead
  description: Preserve the task purpose, delegate one bounded engineering change, and release only when current evidence satisfies criteria.
  instruction: >-
    Read manifest, assignment, checkpoint, surfaced refs, and criteria before assigning or releasing. Verify worker evidence instead of trusting green alone.
  criteria:
    - slot: implementation_rules
      description: Parent acceptance criteria.
      criteria:
        - keep the child inside the current bounded assignment
        - root verifies current patch and verification evidence before release
  children:
    - id: implement_change
      role: engineer
      policy: standard-worker
      description: Understand the purpose, implement the bounded change, and publish patch plus verification evidence for the current assignment.
      instruction: >-
        Read current criteria and any surfaced refs before editing. Keep the patch scoped, verify the intended behavior, and checkpoint reasoning plus criteria status.
      produces:
        artifacts:
          - slot: change_patch
            description: Patch for the bounded change.
            file_hint: change_patch.diff
          - slot: verification_report
            description: Verification evidence for the bounded change.
            file_hint: verification_report.md
```
