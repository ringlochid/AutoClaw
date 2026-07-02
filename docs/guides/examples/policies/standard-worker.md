# Standard worker policy example

Use this policy when a worker assignment should stay bounded and should not wait on humans or start controller-managed command runs.

This example shows:

- worker policy is attached to worker nodes only
- `retry_limit` is worker-only retry budget
- the base worker policy grants no human request or command-run capability
- worker nodes are AutoClaw's executable leaf nodes when they have no children
- the base worker policy does not need `instruction`; the role and node mission define behavior

```yaml
kind: policy
id: standard-worker
title: Standard Worker
description: Guardrails for bounded worker assignments without human waits or command runs.
applies_to:
    - worker
budget_spec:
    retry_limit: 1
capabilities:
    human_request:
        mode: deny
        allowed_kinds: []
    command_run: deny
```
