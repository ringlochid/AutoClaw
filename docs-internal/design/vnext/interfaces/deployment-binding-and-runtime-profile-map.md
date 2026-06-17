# Deployment binding and runtime profile map

Status: Target

This page defines the machine-local binding contract that resolves portable role metadata into runtime-local profile inputs.

## Core rule

Deployment bindings are machine-local configuration.

They are not:

- portable authored definition truth
- controller-owned registry truth
- ordinary task-compose input

## Runtime profile shape

The canonical machine-local runtime profile shape is:

```yaml
runtime_profile:
  id: string
  instruction_sources:
    - kind: agents_md | profile | rules_file
      path: string
  permission_profile: string | optional
  tool_allowlist_profile: string | optional
  adapter_profile: string | optional
  environment_profile: string | optional
```

Field meaning:

- `instruction_sources` names machine-local files or profile sources used to enrich runtime configuration
- `permission_profile` selects a machine-local permission boundary
- `tool_allowlist_profile` selects a machine-local tool-allowlist preset
- `adapter_profile` selects adapter-local connection or transport settings
- `environment_profile` selects machine-local environment variable or secret materialization policy

Raw host paths are legal here because this surface is explicitly machine-local.

## Binding map shape

Portable roles reference deployment bindings through `runtime_binding_key`.

The canonical machine-local binding map is:

```yaml
deployment_binding_map:
  role_bindings:
    - runtime_binding_key: string
      runtime_profile: string
      description: string | optional
```

Rules:

- `runtime_binding_key` must match the key referenced by a portable role definition
- missing binding resolution is a launch-time or binding-time failure
- the binding map may be stored locally, distributed by operators, or materialized by install/onboard flows, but it does not become registry truth

## Launch rule

When a role with `runtime_binding_key` is selected:

1. controller resolves the portable role and policy truth from the registry
2. the local runtime resolves `runtime_binding_key` through the machine-local binding map
3. runtime selects the named runtime profile and records provenance of that resolution

The task may persist the chosen binding key and runtime profile id as provenance, but it must not treat raw local file contents as controller truth.

## Separation rule

Keep these lanes separate:

- portable authored role and policy schema
- machine-local deployment bindings
- controller-owned task and runtime truth

`AGENTS.md`, local rule files, adapter config files, and host-specific paths must not leak back into the portable authored schema as if they were reusable registry truth.

## Related contracts

- [Role and policy definition schema](role-and-policy-definition-schema.md)
- [Capability, security, and audit](capability-security-and-audit.md)
- [Definition authoring workbench](definition-authoring-workbench.md)
- [V1 task compose schema](../../v1/workflows/task-compose-schema.md)
