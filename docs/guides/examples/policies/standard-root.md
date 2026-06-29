# Standard root policy example

Status: Reference

Use this policy when the root node owns final task closure without human waits or command runs.

This example teaches:

- root policies attach to the `root` node only
- `child_assignment_limit` bounds root child assignments, not worker retries
- root policy owns final closure guardrails, not specialist execution behavior
- the base root policy does not need `instruction`; root behavior comes from role, node kind, and prompt layer

```yaml
kind: policy
id: standard-root
title: Standard Root
description: Guardrails for root orchestration and final closure.
applies_to:
    - root
budget_spec:
    child_assignment_limit: 3
capabilities:
    human_request:
        mode: deny
        allowed_kinds: []
    command_run: deny
```
