# Role and policy definition schema

Status: Target

This page defines the V2 portable authored schema for roles and policies.

## Core rule

Portable authored definitions remain portable by default.

Host paths, `AGENTS.md` locations, machine-local provider config, and adapter-specific local file references do not belong in this schema. They belong in `config.toml` and runtime-owned local configuration.

Provider resolution is also not role or policy metadata. Optional provider preference belongs on workflow nodes and resolves through the separate workflow-node and provider-runtime contracts.

## `RoleDefinitionInput`

V2 role definitions use this authored body:

```yaml
id: string
title: string
description: string
allowed_node_kinds:
    - root | parent | worker
labels:
    - string
instruction: string | optional
```

Field meaning:

- `id` is the stable logical role key
- `title` is the human display name used by authoring and control surfaces
- `description` is reusable descriptive metadata
- `allowed_node_kinds` is the compatibility set for structural nodes
- `labels` are optional portable tags for search, grouping, and UI routing
- `instruction` contributes to prompt assembly only after role and policy resolution

## `PolicyDefinitionInput`

V2 policy definitions use this authored body:

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
labels:
    - string
instruction: string | optional
```

Field meaning:

- `title` is the human display name used by authoring and control surfaces
- `budget_spec` remains the authored bounded-work control object
- `capabilities.human_request.mode` explicitly grants or denies portable human-request permission
- `capabilities.human_request.allowed_kinds` gates which typed human request kinds the current node may open when `mode: allow`
- portable policy lists concrete request kinds; authored reusable policy should stay explicit
- `capabilities.command_run` gates whether the current node may start controller-managed long-running command runs
- authored capability fields are portable inputs to runtime capability resolution; they are not by themselves the final current-dispatch capability truth
- ordinary node MCP access and control-plane actions are not authored policy allow-lists in this model
- `labels` are optional portable tags only

## Validation rules

Validation must enforce:

- `id` and `description` are required; `title` is optional display metadata
- `allowed_node_kinds` and `applies_to` are non-empty
- `labels`, when present, are strings only
- `budget_spec.child_assignment_limit` is legal only for `root` and/or `parent`
- `budget_spec.retry_limit` is legal only for `worker`
- omitted `capabilities.human_request` defaults to `mode: deny`
- omitted `capabilities.command_run` defaults to `deny`
- `capabilities.human_request.mode` accepts only `deny` or `allow`
- `capabilities.human_request.mode: deny` grants no portable human-request permission and ignores `allowed_kinds` when present
- `capabilities.human_request.mode: allow` requires non-empty `allowed_kinds`
- `capabilities.human_request.allowed_kinds`, when effective, accepts only the named request kinds above
- `capabilities.command_run` accepts only the named enum values above

Rejected portable-schema patterns include:

- raw host paths
- `AGENTS.md` file locations
- machine-local provider config
- adapter-native callback or thread identifiers
- hidden runtime-injected default policy grammar

## Effective resolution rule

V2 keeps the same high-level rule as V1:

- role and policy identities resolve from controller-owned current registry truth at launch or structural adopt time
- runtime then pins the resolved revisions
- later registry uploads do not mutate already-launched runtime nodes
- portable capability fields are only one input to the effective capability set; task policy, resolved provider preference, adapter restrictions, and current runtime state may narrow them further
- runtime may snapshot the evaluated capability set into dispatch read models, task events, or prompt-facing projections for one execution, but those snapshots remain controller-derived runtime truth rather than authored definition truth
- ordinary node MCP access comes from provider launch compatibility plus the shared node and operator surface contract, not from authored tool allow-lists
- control-plane action legality comes from task authorization and current task state, not from authored visibility lists

Provider preference participates differently:

- role and policy definitions stay provider-neutral
- a workflow node may express a provider preference through its own portable `provider_preference` field
- machine-local runtime config supplies the default provider and local provider settings
- resolved provider preference may be persisted as dispatch or event provenance without becoming authored definition truth

## Related contracts

- [Workflow node schema](workflow-node-schema.md)
- [Provider preference and runtime config](provider-selection-and-runtime-config.md)
- [Node and operator MCP surface contract](node-and-operator-mcp-surface-contract.md)
- [Human request and approval contract](human-request-and-approval-contract.md)
- [Capability, security, and audit](capability-security-and-audit.md)
- [V1 role and policy definition schema](../../v1/interfaces/role-and-policy-definition-schema.md)
