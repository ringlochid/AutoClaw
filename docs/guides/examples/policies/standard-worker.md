# Standard worker policy example

Status: Reference

Use this policy when a worker assignment should stay bounded and get one ordinary retry.

This example teaches:

- worker policy is attached to worker nodes only
- `retry_limit` expresses bounded retry behavior
- the policy does not redefine the role instruction; it adds budget behavior

```yaml
kind: policy
id: standard-worker
title: Standard Worker
description: Default worker behavior for bounded work.
applies_to:
    - worker
budget_spec:
    retry_limit: 1
```
