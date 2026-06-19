# Role and policy definition schema

Status: Target

This page defines the Vnext portable authored schema for roles and policies.

## Core rule

Portable authored definitions remain portable by default.

Host paths, `AGENTS.md` locations, machine-local profiles, and adapter-specific local file references do not belong in this schema. They belong in the deployment-binding map.

## `RoleDefinitionInput`

Vnext role definitions use this authored body:

```yaml
id: string
title: string
description: string
allowed_node_kinds:
  - root | parent | worker
runtime_binding_key: string | optional
labels:
  - string
instruction: string | optional
```

Field meaning:

- `id` is the stable logical role key
- `title` is the human display name used by authoring and control surfaces
- `description` is reusable descriptive metadata
- `allowed_node_kinds` is the compatibility set for structural nodes
- `runtime_binding_key`, when present, is a portable logical reference into the deployment-binding map
- `labels` are optional portable tags for search, grouping, and UI routing
- `instruction` contributes to prompt assembly only after runtime selection and validation

## `PolicyDefinitionInput`

Vnext policy definitions use this authored body:

```yaml
id: string
title: string
description: string
applies_to:
  - root | parent | worker
budget_spec:
  child_assignment_limit: integer | optional
  retry_limit: integer | optional
capabilities:
  human_request:
    mode: deny | allow
    allowed_kinds:
      - direction | approval | input | review
  command_run: deny | allow
  node_tool_allowlist:
    mode: inherited | explicit
    tool_families:
      - checkpoint | boundary | parent_structural_edit | definition_lookup | human_request | command_run
  control_action_visibility:
    - inspect_runtime | pause | continue | cancel | resolve_human_request | cancel_command_run
labels:
  - string
instruction: string | optional
```

Field meaning:

- `title` is the human display name used by authoring and control surfaces
- `budget_spec` remains the authored bounded-work control object
- `capabilities.human_request.mode` explicitly grants or denies portable human-request permission
- `capabilities.human_request.allowed_kinds` gates which typed human request kinds the current node may open when `mode: allow`
- portable policy lists concrete request kinds; effective runtime resolution may expose an internal `any` shorthand, but authored reusable policy should stay explicit
- `capabilities.command_run` gates whether the current node may start controller-managed long-running command runs
- `capabilities.node_tool_allowlist` narrows the portable node-tool families available to matching nodes
- `capabilities.control_action_visibility` names portable control action families that may be shown when runtime state and authorization also allow them
- authored capability fields are portable inputs to runtime capability resolution; they are not by themselves the final current-dispatch capability truth
- omitted `node_tool_allowlist` defaults to inherited runtime resolution
- omitted `control_action_visibility` defaults to runtime-derived visibility with no portable visibility widening
- `labels` are optional portable tags only

## Validation rules

Validation must enforce:

- `id`, `title`, and `description` are required
- `allowed_node_kinds` and `applies_to` are non-empty
- `runtime_binding_key`, when present, is a plain logical key, not a host path
- `labels`, when present, are strings only
- `budget_spec.child_assignment_limit` is legal only for `root` and/or `parent`
- `budget_spec.retry_limit` is legal only for `worker`
- omitted `capabilities.human_request` defaults to `mode: deny`
- `capabilities.human_request.mode` accepts only `deny` or `allow`
- `capabilities.human_request.mode: deny` grants no portable human-request permission and ignores `allowed_kinds` when present
- `capabilities.human_request.mode: allow` requires non-empty `allowed_kinds`
- `capabilities.human_request.allowed_kinds`, when effective, accepts only the named request kinds above
- `capabilities.command_run` accepts only the named enum values above
- `capabilities.node_tool_allowlist.mode: explicit` requires a non-empty `tool_families` list
- `capabilities.node_tool_allowlist.mode: inherited` may omit `tool_families`
- `capabilities.control_action_visibility`, when present, accepts only the named action families above

Rejected portable-schema patterns include:

- raw host paths
- `AGENTS.md` file locations
- machine-local profile paths
- adapter-native callback or thread identifiers
- hidden runtime-injected default policy grammar

## Effective resolution rule

Vnext keeps the same high-level rule as V1:

- role and policy identities resolve from controller-owned current registry truth at launch or structural adopt time
- runtime then pins the resolved revisions
- later registry uploads do not mutate already-launched runtime nodes
- portable capability fields are only one input to the effective capability set; task policy, deployment profile, adapter restrictions, and current runtime state may narrow them further
- runtime may snapshot the evaluated capability set into dispatch read models, task events, or prompt-facing projections for one execution, but those snapshots remain controller-derived runtime truth rather than authored definition truth

`runtime_binding_key` participates differently:

- it is resolved through the machine-local deployment-binding map at launch or other allowed runtime binding points
- it does not become stored registry truth by itself
- it must not carry raw host path data in the portable authored definition

## Related contracts

- [Deployment binding and runtime profile map](deployment-binding-and-runtime-profile-map.md)
- [Human request and approval contract](human-request-and-approval-contract.md)
- [Capability, security, and audit](capability-security-and-audit.md)
- [V1 role and policy definition schema](../../v1/interfaces/role-and-policy-definition-schema.md)
