# Write a role

Status: Reference

Write a role when you need a reusable specialist for your automation. A role should describe what kind of work a node can do and how it should behave across many tasks.

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
- what kind of work is it allowed to perform?
- what output should a parent/root expect?
- what should it refuse to widen?
- which node kinds can use this role?

Keep launch detail out of the role. Paths, one-off user requests, concrete task scope, and secrets belong outside reusable role definitions.

## Write the instruction

Role instruction should teach stable behavior:

```yaml
kind: role
id: scope_reviewer
description: Reviews proposed task scope against evidence, constraints, and closure criteria.
allowed_node_kinds:
  - worker
instruction: >
  Read the current assignment, criteria, surfaced artifacts, and latest
  relevant checkpoint before reviewing. Identify scope expansion, missing
  evidence, and contradictions. Publish a review artifact that states whether
  the proposed scope is acceptable, risky, or blocked. Do not implement.
```

That role can be reused anywhere a scope review is needed.

## Good role checklist

- the role name describes a real specialist
- `allowed_node_kinds` is narrow
- the instruction says what to read first
- the instruction says what to publish
- the instruction says what not to do
- the role does not mention task-specific paths or users
- the role does not duplicate policy capability rules

## Related pages

- [Write a policy](write-a-policy.md)
- [Write a workflow](write-a-workflow.md)
- [Authoring model](../concepts/authoring-model.md)
- [Role reference examples](../reference/definitions/roles/README.md)
