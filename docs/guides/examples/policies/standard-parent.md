# Standard parent policy example

Status: Reference

Use this policy when a parent node coordinates children without human waits or command runs.

This example teaches:

- parent policies attach to `parent` nodes only
- `child_assignment_limit` is parent/root-only assignment budget
- parent policy should describe authority and bounds, not planner identity
- the base parent policy does not need `instruction`; parent behavior comes from role, node kind, and prompt layer

```yaml
kind: policy
id: standard-parent
title: Standard Parent
description: Guardrails for parent orchestration without human waits or command runs.
applies_to:
    - parent
budget_spec:
    child_assignment_limit: 20
capabilities:
    human_request:
        mode: deny
        allowed_kinds: []
    command_run: deny
```
