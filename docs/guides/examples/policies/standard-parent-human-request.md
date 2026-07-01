# Standard parent human-request policy example

Use this policy when a parent may need a typed human wait while routing a subtree.

This example teaches:

- human-request capability is separate from command-run capability
- parent human requests are for material direction, approval, missing input, or review
- parent should try to settle the question from subtree evidence and child work first

```yaml
kind: policy
id: standard-parent-human-request
title: Standard Parent Human Request
description: Guardrails for parent orchestration that may wait for human judgment.
applies_to:
    - parent
budget_spec:
    child_assignment_limit: 20
capabilities:
    human_request:
        mode: allow
        allowed_kinds:
            - direction
            - approval
            - input
            - review
    command_run: deny
instruction: >-
  Open a human request only for material direction, approval, missing input, or review that cannot be settled from current task evidence, try to solve it in current subtree first, if the worker can't provide best practices plus sufficient evidence, then use human request.
```
