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
- `title` is the human display name used by authoring and operator surfaces
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
    allowed_kinds:
      - direction | approval | input | review
  async_job: deny | allow
  node_tool_allowlist:
    mode: inherited | explicit
    tool_families:
      - checkpoint | boundary | parent_structural_edit | definition_lookup | human_request | async_job
  operator_control_visibility:
    - inspect_runtime | pause | continue | cancel | resolve_human_request | cancel_async_job
labels:
  - string
instruction: string | optional
```

Field meaning:

- `title` is the human display name used by authoring and operator surfaces
- `budget_spec` remains the authored bounded-work control object
- `capabilities.human_request.allowed_kinds` gates which typed human request kinds the current node may open
- portable policy lists concrete request kinds; effective runtime resolution may expose an internal `any` shorthand, but authored reusable policy should stay explicit
- `capabilities.async_job` gates whether the current node may start controller-managed async jobs
- `capabilities.node_tool_allowlist` narrows the portable node-tool families available to matching nodes
- `capabilities.operator_control_visibility` names portable operator action families that may be shown when runtime state and authorization also allow them
- omitted `node_tool_allowlist` defaults to inherited runtime resolution
- omitted `operator_control_visibility` defaults to runtime-derived visibility with no portable visibility widening
- `labels` are optional portable tags only

## Validation rules

Validation must enforce:

- `id`, `title`, and `description` are required
- `allowed_node_kinds` and `applies_to` are non-empty
- `runtime_binding_key`, when present, is a plain logical key, not a host path
- `labels`, when present, are strings only
- `budget_spec.child_assignment_limit` is legal only for `root` and/or `parent`
- `budget_spec.retry_limit` is legal only for `worker`
- `capabilities.human_request.allowed_kinds`, when present, accepts only the named request kinds above
- omitted or empty `capabilities.human_request.allowed_kinds` means no portable human-request permission is granted by this policy
- `capabilities.async_job` accepts only the named enum values above
- `capabilities.node_tool_allowlist.mode: explicit` requires a non-empty `tool_families` list
- `capabilities.node_tool_allowlist.mode: inherited` may omit `tool_families`
- `capabilities.operator_control_visibility`, when present, accepts only the named action families above

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

`runtime_binding_key` participates differently:

- it is resolved through the machine-local deployment-binding map at launch or other allowed runtime binding points
- it does not become stored registry truth by itself
- it must not carry raw host path data in the portable authored definition

## Related contracts

- [Deployment binding and runtime profile map](deployment-binding-and-runtime-profile-map.md)
- [Human request and approval contract](human-request-and-approval-contract.md)
- [Capability, security, and audit](capability-security-and-audit.md)
- [V1 role and policy definition schema](../../v1/interfaces/role-and-policy-definition-schema.md)
