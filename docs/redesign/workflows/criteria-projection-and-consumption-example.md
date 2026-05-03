# Criteria projection and consumption example

Status: Target

This page is the canonical end-to-end explanation of maximal criteria semantics under the parent-first verification model.

It expands the staged maximal example without changing the frozen target behavior.

## Declaration inventory

| Source owner        | Kind     | Slot                                 | Purpose                                              |
| ------------------- | -------- | ------------------------------------ | ---------------------------------------------------- |
| root                | criteria | `root_delivery_rules`                | delivery and escalation rules before green or replan |
| root                | criteria | `root_closure_criteria`              | final root closure requirements                      |
| gather_evidence     | criteria | `gather_evidence_delivery_criteria`  | discovery-step delivery criteria                     |
| implementation_loop | criteria | `implementation_loop_requirements`   | shared implementation requirements for the subtree   |
| review_change       | criteria | `implementation_review_criteria`     | review-step verification criteria                    |
| implement_change    | criteria | `implement_change_delivery_criteria` | engineering delivery criteria                        |

## Projection map

- parent-owned criteria project downward in ancestor-to-local order
- workers consume projected criteria refs plus their own local criteria
- review worker consumes the current owning subtree evidence and configured review criteria refs through ordinary child execution
- ordinary release work consumes surfaced release evidence through authored `consumes.artifacts` plus configured root-owned closure criteria refs

## Discovery subtree

`gather_evidence` is a worker leaf under `discovery`.

It sees:

- its own local `gather_evidence_delivery_criteria`
- any currently projected ancestor criteria that the controller exposes from the active root scope

It does not invent new acceptance criteria at runtime.

### Concrete discovery view

If `gather_evidence` is the current worker, its assignment should surface:

- `summary`
- `instruction`
- `criteria` refs for the current discovery criteria in force
- any authored `consumes`
- optional task-memory hints toward `context/wiki/` or curated docs

It should not receive hidden ancestor bundles or invisible scope summaries.

## Implementation subtree

`implementation_loop` is a parent node with local criteria and ordinary review work.

The implementation subtree semantics are:

- `implementation_loop_requirements` defines the shared subtree acceptance contract
- `child_defaults.criteria` projects that slot onto direct children
- `plan_iteration` and `implement_change` therefore see both the projected subtree requirements and their own local delivery criteria
- `implement_change` still depends on authored hard inputs such as `findings_report` and `delivery_plan`; criteria projection does not replace typed-input legality

## Review child

When `implementation_loop` reaches review:

- `review_change` is an ordinary authored child node
- it consumes the current subtree evidence and the configured `implementation_review_criteria`
- parent verification still decides whether the subtree may release `green`

## Root release work

Root release work is bounded:

- it consumes only the surfaced release evidence declared through authored `consumes.artifacts`
- it consumes only the selected root-owned `root_closure_criteria`
- it does not reopen planning or implementation scope

Example surfaced release evidence for `release_closure`:

- `findings_report`
- `delivery_plan`
- `change_patch`
- `verification_report`
- `review_report`
- `qa_report`

## Attempt pinning rule

Attempts pin exact criteria refs they consumed.

That means:

- `gather_evidence` pins the refs behind its active delivery criteria
- implementation children pin the projected subtree criteria plus any local criteria they consumed
- `review_change` pins the same subtree criteria plus the review-step criteria refs
- `release_closure` pins the surfaced release artifact refs and the root-closure criteria refs

## Parent verification consequence

Parent verification is controller-assembled over:

- current direct-child outputs
- current ordinary review outputs when present
- current consumed criteria refs
- current subtree evidence

Parent or root does not treat a criteria slot as satisfied merely because it was declared. The current evidence must support it.

## Related contracts

- [Maximal example](examples/maximal.md)
- [Criteria and parent verification](criteria-and-parent-verification.md)
- [Workflow schema appendix](workflow-schema-appendix.md)
- [Review findings contract](review-findings-contract.md)
