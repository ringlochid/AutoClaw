# Definition Registry And Upload Contract

Status: Target

This page defines the frozen v1 definition registry lifecycle: list, detail, history, guarded upload, and launch-time resolution.

Use this page for lifecycle, authority, DB-truth ownership, and guarded-write rules. Use [api-schema-appendix.md](api-schema-appendix.md) for exhaustive request and response coverage and [api-machine-catalog.yaml](api-machine-catalog.yaml) for exact machine-readable query and tool-argument definitions.

## Canonical definition kinds

The canonical singular kind tokens are:

- `role`
- `policy`
- `workflow`

The plural list routes are:

- `/definitions/roles`
- `/definitions/policies`
- `/definitions/workflows`

## Core routes

The canonical definition-registry routes are:

- `GET /definitions/roles`
- `GET /definitions/policies`
- `GET /definitions/workflows`
- `GET /definitions/{kind}/{key}`
- `GET /definitions/{kind}/{key}/versions`
- `POST /definitions`

## Quick lifecycle examples

- upload one new current revision for one role, policy, or workflow key
- read current role/policy definitions before `add_child` or `update_child` so structural edits use real current keys instead of prompt guesses

## Registry truth model

After successful ingest or guarded upload:

- imported files are provenance and authoring inputs
- registry identity rows plus immutable revision rows are authoritative definition truth
- stored definition revisions may keep the exact authored body as a structured document column for later reread
- launch-time compilation uses the current workflow revision
- runtime structural edits validate role/policy references against current registry truth
- compiled plan and runtime node truth pin the exact resolved workflow, role, and policy revisions used for that task or structural revision

Imported files do not outrank registry truth after successful ingest.

Registry persistence closure:

- `workflow_definitions`, `role_definitions`, and `policy_definitions` are stable identity tables
- `workflow_revisions`, `role_revisions`, and `policy_revisions` are append-only revision tables
- identity tables own stable logical keys plus the current revision pointer
- revision tables own immutable authored content snapshots, revision numbers, actor/audit fields when recorded, and timestamps
- guarded upload appends new revision rows and atomically advances the current revision pointer
- concurrent uploads are serialized in DB and may both succeed as distinct revisions
- the current revision pointer advances in DB commit order
- the redesign does not use a single-table mutable version-column history model for registry truth
- the redesign does not use a draft/publish definition state machine

Concrete example:

If `C:/defs/review-role.yaml` was imported successfully, later runtime structural validation uses the stored registry row for `role/review-role`, not the original file path.

## Registry reads for runtime structural edits

The definition registry is the canonical discovery lane for valid role and policy choices.

That means:

- parent/root structural-edit preparation may search role and policy summaries and then read chosen current role/policy detail
- trusted automation may do the same through the public read routes or an adapter-specific plugin surface
- `add_child` and `update_child` do not guess role or policy names from prompt prose or transcript memory
- runtime still revalidates those references at commit time

Parent/root current-only rule:

- parent/root planning uses list/search plus current detail only
- parent/root does not use revision-history read as a normal planning input
- revision history is for operator, audit, provenance, and trusted automation investigation rather than normal dispatched parent/root planning

Concrete example:

1. read `GET /definitions/roles?q=review&allowed_node_kind=parent`
2. read `GET /definitions/policies?q=review&applies_to=parent`
3. read `GET /definitions/role/review-role`
4. read `GET /definitions/policy/review-policy`
5. choose a valid role/policy pair for the new child draft
6. call `add_child` through the bound callback semantic tool lane
7. let the runtime validator re-check the chosen ids against current registry truth and pin the exact resolved role/policy revision numbers at commit time

## List, detail, and history reads

List routes return `DefinitionSummaryListResponse`. Detail reads return `DefinitionRevisionDetailResponse`. Revision-history routes return `DefinitionRevisionHistoryResponse`.

These surfaces exist so operators and automation can answer:

- what keys exist
- what the current definition body is
- which revision is current
- which earlier revisions exist in history

Audience split:

- list/search plus current detail are the normal role/policy discovery surfaces for dispatched parent/root planning
- revision-history read is an operator/trusted-automation audit surface by default

List, search, and history query rules:

- definition list/search routes use `q`, `limit`, `cursor`, and `sort`
- role list/search may additionally use `allowed_node_kind`
- policy list/search may additionally use `applies_to`
- detail read returns the current definition revision for that logical key
- version-history read uses `limit`, `cursor`, and `sort`

Machine-readable parameter descriptions live in [api-machine-catalog.yaml](api-machine-catalog.yaml).

## Guarded upload rule

`POST /definitions` requires:

- `kind`
- `content` as exactly one definition body of the selected kind
- logical key from `content.id`

Guarded upload semantics:

- same `kind` plus logical key plus identical canonical normalized content hash as the current stored revision is a no-op
- changed accepted canonical content stores the next immutable revision row for that definition key and atomically advances the current revision pointer
- does not mutate the current or any historical revision row in place
- returns `200` on a no-op identical-content write
- returns `201` on successful guarded upload that created a new current revision
- returns `422` on invalid definition content

Canonical hash basis:

- hash the accepted canonical normalized definition body
- exclude transport-only wrapper fields such as request `kind`

For `PolicyDefinitionInput`, invalid definition content includes:

- `default_policy`
- `defaults`
- `defaults.retry_budget`
- `rules`
- `rules.allowed_tools`
- `rules.allowed_boundaries`
- `same_attempt_continue_limit`
- `same_attempt_redispatch_limit`
- authored same-session or continue-session preferences
- any `budget_spec` key other than `child_assignment_limit` or `retry_limit`

Canonical behavior is reject, not silent ignore, for richer-than-live policy grammar.

There is no required actor header in the frozen core contract. Authenticated lane identity may be recorded for audit, but actor transport is not frozen here.

Worked create example:

```text
POST /definitions
kind=workflow
content=<one exact WorkflowDefinitionInput with id "retry-review">

-> 201 Created
-> DefinitionRevisionDetailResponse { key: "retry-review", revision_no: 1, ... }
```

No-op example:

```text
POST /definitions
kind=workflow
content=<canonical content identical to current stored workflow/retry-review>

-> 200 OK
-> DefinitionRevisionDetailResponse { key: "retry-review", revision_no: 8, ... }
```

Worked update example:

```text
POST /definitions
kind=workflow
content=<one exact WorkflowDefinitionInput with id "retry-review">

-> 201 Created
-> DefinitionRevisionDetailResponse { key: "retry-review", revision_no: 8, ... }
```

Concurrent upload rule:

- if two callers upload different new content for the same logical key concurrently, DB serialization may commit both as distinct new revisions
- whichever upload commits later becomes the new current revision
- earlier committed revisions remain preserved in history
- there is no caller-supplied compare token in the public upload contract

## Launch-time compiler rule

Standard task start resolves:

- the current workflow revision for `workflow.key`
- any referenced role and policy definitions required by that workflow

The launch-time compiler owns:

- current workflow + role/policy definitions + task compose
- normalized compiled plan
- initial runtime graph/materialization at task start

Internal validation rule:

- guarded definition upload validates schema legality, role/policy reference legality, and dependency legality before the current revision pointer moves
- task start validates again against current truth before runtime materialization commits
- runtime structural adopt validates again before a new structural revision commits
- the validator is internal by design; it is not exposed as a public API or standard plugin surface

## Runtime structural-edit rule

Runtime structural CRUD is not a definition-registry write and does not invoke the launch-time compiler.

For `add_child` and `update_child`:

- the runtime validator checks candidate role/policy references against current registry truth
- the runtime validator pins the exact resolved role/policy revision numbers into the new adopted runtime truth
- explicit node `policy` resolves when present; otherwise no policy resolves
- runtime structural edits never inject a hidden workflow-level or role-level default policy
- if a policy resolves, only its `description`, `instruction`, and optional `budget_spec` participate
- parent/root policies may author only `child_assignment_limit`
- worker policies may author only `retry_limit`
- same-attempt redispatch and same-session continuity remain controller recovery/continuity behavior rather than authored policy
- the controller commits runtime truth only after that validation passes
- the runtime materializer/projector then regenerates `_runtime` projections

This keeps definition upload separate from runtime mutation.

That separation is important:

- definition-registry work changes reusable authored truth through guarded upload
- runtime structural CRUD changes one running flow only
- the two surfaces may validate against one another, but they are never the same lane
- after commit, execution follows pinned compiled/runtime revision truth rather than rereading moving registry head on every dispatch

## Named response coverage

The canonical named responses used by this surface are:

- `DefinitionSummaryListResponse`
- `DefinitionRevisionDetailResponse`
- `DefinitionRevisionHistoryResponse`

Field-level definitions live in [api-schema-appendix.md](api-schema-appendix.md).

## Removed from the live registry model

Do not keep these as live registry semantics:

- callback-bound runtime mutation through definition routes
- a draft/publish state machine for definitions
- provider/plugin-specific authored definition fields
- `parent_gate`-specific compatibility rules
- `BoundaryAction`-era legal-outcome matrices
- `url` or `uri` as surfaced runtime ref requirements

## Related contracts

- [API surface and trust-lane map](api-surface-and-trust-lane-map.md)
- [API schema appendix](api-schema-appendix.md)
- [Role and policy definition schema](role-and-policy-definition-schema.md)
- [Workflow definition schema](../workflows/workflow-definition-schema.md)
- [Guarded registry and runtime writes](guarded-registry-and-runtime-writes.md)
- [Definition ingest and task-start file contract](definition-ingest-and-upload-contract.md)
