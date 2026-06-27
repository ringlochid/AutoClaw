# Standard worker policy example

Status: Reference

This example mirrors the shipped `standard-worker` policy fixture.

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
