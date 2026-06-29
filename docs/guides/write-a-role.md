# Write a role

Status: Reference

Write a role when you need a reusable specialist for your automation. A role describes the lens a node brings to work across many tasks.

Do not start from the shipped roles as a menu. Treat them as examples. Your automation should have roles named for its own durable responsibilities.

## Start with one capability

A good role has one stable capability profile:

- `market_researcher`
- `scope_reviewer`
- `bug_triage`
- `release_operator`
- `customer_support_classifier`
- `invoice_reconciliation_reviewer`

Avoid generic names such as `assistant`, `helper`, or `worker`. Generic roles hide responsibility and make workflow review harder.

## Decide what the role owns

Before writing YAML, answer:

- what evidence should this role read first?
- what work mode is it in?
- what output should a parent/root expect?
- what should it refuse to widen?
- what ambiguity should it surface?
- which node kinds can use this role?

Keep launch detail out of the role. Paths, one-off user requests, concrete task scope, and secrets belong outside reusable role definitions.

## Choose the node kind

Most roles should be worker-only:

```yaml
allowed_node_kinds:
    - worker
```

Use `parent` or `root` only for roles whose durable job is orchestration, routing, evidence inspection, or closure. A parent/root role should not become a general specialist that also implements, verifies, and releases.

## Write the instruction

Role instruction should teach stable behavior:

```yaml
kind: role
id: scope_reviewer
title: Scope Reviewer
description: Worker for one bounded scope, contradiction, feasibility, or risk review.
allowed_node_kinds:
    - worker
instruction: >-
    First identify the accepted purpose, proposed scope, evidence, constraints, criteria,
    and what decision the review should unblock. Research current contracts, dependencies,
    local precedent, and best-practice fit before judging scope. Do not implement or
    expand the plan. Publish pass/fail reasoning, required corrections, risk severity, and
    decision implications.
```

That role can be reused anywhere a scope review is needed.

## Add a research lens

Research belongs in roles only when it is part of the specialist lens.

Good:

- an engineer inspects local code patterns, contracts, docs, and tests
- a market researcher gathers source-grounded audience or competitor evidence
- a verifier researches expected behavior before choosing a test oracle
- a reviewer researches criteria and risk before judging

Bad:

- every role says "do research first" with no domain evidence target
- a role tells workers to rewrite contracts or replan the workflow
- a role asks for broad research when the node needs a bounded output

Use policies for the shared ambiguity protocol. Use workflow nodes to route research to the right place.

## Good role checklist

- the role name describes a real specialist
- `allowed_node_kinds` is narrow
- the instruction says what to read first
- the instruction names the role's evidence lens
- the instruction says what to publish
- the instruction says what not to do
- the role does not mention task-specific paths or users
- the role does not duplicate policy capability rules
- ambiguity is surfaced rather than hidden

## Related pages

- [Write layered instructions](write-layered-instructions.md)
- [Write a policy](write-a-policy.md)
- [Write a workflow](write-a-workflow.md)
- [Authoring model](../concepts/authoring-model.md)
- [Role reference examples](../reference/definitions/roles/README.md)
