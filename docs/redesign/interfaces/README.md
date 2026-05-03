# Redesign Interfaces

Status: Target

This folder owns the frozen external and adapter-facing contracts for:

- definition registry reads and guarded writes
- task start
- public operator runtime reads and flow control
- adapter-specific plugin parity
- CLI/package/install surfaces

`tool` is the canonical runtime term. `plugin` is adapter-specific only.

## Start Here

Read in this order:

1. [INDEX.md](INDEX.md)
2. [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md)
3. [api-schema-appendix.md](api-schema-appendix.md)
4. [api-machine-catalog.yaml](api-machine-catalog.yaml)
5. [definition-registry-and-upload-contract.md](definition-registry-and-upload-contract.md)
6. [role-and-policy-definition-schema.md](role-and-policy-definition-schema.md)
7. [plugin-tool-reference.md](plugin-tool-reference.md)

## Canonical Live Owners

- [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md) route families, trust lanes, and stale-write guards
- [api-schema-appendix.md](api-schema-appendix.md) named requests, responses, shared enums, and shared nested shapes
- [api-machine-catalog.yaml](api-machine-catalog.yaml) machine-readable query, filter, sort, and tool-argument catalog
- [definition-registry-and-upload-contract.md](definition-registry-and-upload-contract.md) registry lifecycle, upload rules, and registry-read discovery for structural edits
- [role-and-policy-definition-schema.md](role-and-policy-definition-schema.md) authored role/policy shapes and validation rules
- [plugin-tool-reference.md](plugin-tool-reference.md) adapter-specific plugin parity surface over canonical tools and reads

## Supporting Surfaces

- [human-and-operator-control-surface.md](human-and-operator-control-surface.md)
- [cli-surface-and-operator-workflows.md](cli-surface-and-operator-workflows.md)
- [cli-api-and-package-shape.md](cli-api-and-package-shape.md)
- [definition-ingest-and-upload-contract.md](definition-ingest-and-upload-contract.md)
- [release-and-install-strategy.md](release-and-install-strategy.md)
- [distribution-and-database-support-matrix.md](distribution-and-database-support-matrix.md)
- [testing-and-release-checklist.md](testing-and-release-checklist.md)

## Search-First Questions

- "Which routes are public and which are internal?" [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md)
- "What are the exact request/response shapes?" [api-schema-appendix.md](api-schema-appendix.md)
- "What exact query params, filters, sorts, and tool aliases may a model caller use?" [api-machine-catalog.yaml](api-machine-catalog.yaml)
- "How are roles and policies discovered and uploaded into current registry revisions?" [definition-registry-and-upload-contract.md](definition-registry-and-upload-contract.md)
- "What does the adapter-specific plugin expose?" [plugin-tool-reference.md](plugin-tool-reference.md)
- "What is the operator boundary?" [operator-definition-and-role-boundary.md](operator-definition-and-role-boundary.md)
- "What CLI/package/install behavior is in scope?" [cli-api-and-package-shape.md](cli-api-and-package-shape.md) and [release-and-install-strategy.md](release-and-install-strategy.md)
- "What does the root CLI actually expose day to day?" [cli-surface-and-operator-workflows.md](cli-surface-and-operator-workflows.md)

## Fast Route Examples

- "I want to understand how upload-triggered internal validation works for a workflow definition." Read [definition-registry-and-upload-contract.md](definition-registry-and-upload-contract.md) first, then the exact request/response shape in [api-schema-appendix.md](api-schema-appendix.md).
- "I want to start a task from a local file." Read [definition-ingest-and-upload-contract.md](definition-ingest-and-upload-contract.md) for file-entry rules, then [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md) for `POST /tasks/start`.
- "I want to pause or continue a live flow." Read [human-and-operator-control-surface.md](human-and-operator-control-surface.md) for the authority boundary, then [api-surface-and-trust-lane-map.md](api-surface-and-trust-lane-map.md) and [api-schema-appendix.md](api-schema-appendix.md).
- "I want the shortest root-command list before I read route details." Start with [cli-surface-and-operator-workflows.md](cli-surface-and-operator-workflows.md), then read [cli-api-and-package-shape.md](cli-api-and-package-shape.md) for the split between CLI, API, and adapter/package surfaces.
- "I want to know whether the standard external plugin may call `assign_child`." Read [plugin-tool-reference.md](plugin-tool-reference.md) and [human-and-operator-control-surface.md](human-and-operator-control-surface.md). The answer is no: that is an internal dispatch-bound adapter capability, not a standard operator-safe parity capability.
