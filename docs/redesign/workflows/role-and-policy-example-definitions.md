# Role and policy example definitions

Status: Target

This page provides canonical standalone example snippets only. It does not own the v1 role or policy schema.

V1 uses one file per definition. Do not treat this page as a many-definitions-per-file ingest example.

Exact role and policy schema authority lives in [Role and policy definition schema](../interfaces/role-and-policy-definition-schema.md).

In this repo, `definitions/{roles,policies}/**` and the packaged seed mirrors under `apps/api/app/resources/definitions/**` should stay aligned with these examples. Those files are authoring, docs, test, and bootstrap mirrors only; after seed or upload, registry current revisions are authoritative.

## How to read these examples

Read every policy example here under these guardrails:

- canonical ingest accepts only `id`, `description`, `applies_to`, optional `budget_spec`, and optional `instruction`
- `budget_spec` may contain only:
  - `child_assignment_limit`
  - `retry_limit`
- policy text contributes descriptive/provider instruction only; it does not define machine tool legality, boundary legality, runtime counters, or provider truth
- same-attempt redispatch and same-session continuation are runtime continuity/recovery behavior, not authored policy grammar
- richer policy grammar is invalid for v1 ingest even if old notes or stale examples once showed it

Canonical reject examples include:

- `default_policy`
- `defaults`
- `defaults.retry_budget`
- `rules`
- `rules.allowed_tools`
- `rules.allowed_boundaries`
- `same_attempt_continue_limit`
- `same_attempt_redispatch_limit`
- `budget_spec.same_attempt_continue_limit`
- `budget_spec.same_attempt_redispatch_limit`

Valid live `budget_spec` examples:

```yaml
budget_spec:
  child_assignment_limit: 4
```

```yaml
budget_spec:
  retry_limit: 1
```

## Example role definitions

These snippets are intentionally concrete. They show the tone and scope of reusable role/policy definitions without teaching hidden runtime powers.

Each snippet below is shown in canonical one-file-per-definition form for CLI scan/import, so the required top-level `kind` is present.

```yaml
# planning_lead.yaml
kind: role
id: planning_lead
description: Parent/root coordinator for one owned subtree.
allowed_node_kinds:
  - root
  - parent
instruction: |
  Coordinate only the current owned subtree.
  Use the current workflow manifest, assignment, child checkpoints, referenced
  artifacts, surfaced criteria, optional transient refs, and task-memory hints
  to decide what to do next.
  Use explicit control tools during an open dispatch.
```

```yaml
# root_planning_lead.yaml
kind: role
id: root_planning_lead
description: Root coordinator for whole-flow closure decisions.
allowed_node_kinds:
  - root
instruction: |
  Coordinate the whole flow from current manifest, child checkpoints,
  referenced artifacts, and current criteria.
  Only root may commit whole-flow blocked state.
```

```yaml
# engineer.yaml
kind: role
id: engineer
description: Worker for one bounded engineering assignment.
allowed_node_kinds:
  - worker
instruction: |
  Complete only the current assignment.
  Publish required durable outputs, record a checkpoint, and close with green,
  retry, or blocked only when the current assignment truly reaches that state.
```

```yaml
# reviewer.yaml
kind: role
id: reviewer
description: Ordinary review worker for one bounded assignment.
allowed_node_kinds:
  - worker
instruction: |
  Review only the explicitly surfaced evidence.
  Publish ordinary review artifacts and a checkpoint.
  Parent/root still decides the next control action.
```

```yaml
# release_operator.yaml
kind: role
id: release_operator
description: Ordinary bounded release worker.
allowed_node_kinds:
  - worker
instruction: |
  Use only the explicitly surfaced release evidence and current criteria.
  Do not reopen planning or implementation scope.
```

## Example policy definitions

The policy examples below keep the surface explicit:

- policy text may remind the node how to operate inside the already-frozen runtime model
- policy text does not add machine control grammar beyond optional `budget_spec`
- examples do not invent hidden fallback, transport, or provider-native runtime powers
- when an example uses narrower descriptive wording than the global runtime model, that wording is local guidance only and does not rewrite the canonical legality model
- parent/root policies use only `child_assignment_limit`
- worker policies use only `retry_limit`

```yaml
# standard-parent-planning.yaml
kind: policy
id: standard-parent-planning
description: Default parent planning behavior.
applies_to:
  - parent
budget_spec:
  child_assignment_limit: 4
instruction: |
  Stage child work with assign_child.
  Use structural edits only on current direct children.
  Explain later-sensitive decisions in checkpoints rather than transcript
  memory.
```

```yaml
# standard-root-planning.yaml
kind: policy
id: standard-root-planning
description: Default root planning and closure behavior.
applies_to:
  - root
budget_spec:
  child_assignment_limit: 4
instruction: |
  Root owns final closure.
  Commit release_green only when current whole-flow evidence is sufficient.
  Commit release_blocked only when whole-flow terminal blocked state is
  explicit and current.
```

```yaml
# standard-worker.yaml
kind: policy
id: standard-worker
description: Default worker behavior for bounded work.
applies_to:
  - worker
budget_spec:
  retry_limit: 1
```

```yaml
# standard-review.yaml
kind: policy
id: standard-review
description: Ordinary review worker behavior.
applies_to:
  - worker
instruction: |
  Green means the review assignment completed, not that the reviewed target
  automatically passes parent/root closure.
  Record approval, rejection, or evidence gaps in the checkpoint summary and
  published review artifacts rather than inventing a second result enum.
```

```yaml
# standard-release.yaml
kind: policy
id: standard-release
description: Ordinary release or closure worker behavior.
applies_to:
  - worker
instruction: |
  Use only the surfaced release evidence and current criteria.
  Publish ordinary release artifacts and checkpoint output.
  Record release readiness or blockers in the checkpoint summary and published
  release artifacts rather than inventing a second result enum.
```

## Shared-id rule

The canonical workflow exemplars may use these shared ids:

- `planning_lead`
- `root_planning_lead`
- `engineer`
- `researcher`
- `architect`
- `planner`
- `reviewer`
- `release_operator`
- `standard-parent-planning`
- `standard-root-planning`
- `standard-worker`
- `standard-review`
- `standard-release`

## Related contracts

- [Role and policy definition schema](../interfaces/role-and-policy-definition-schema.md)
- [Definition registry and upload contract](../interfaces/definition-registry-and-upload-contract.md)
- [Mode contract and legality matrix](mode-contract-and-legality-matrix.md)
