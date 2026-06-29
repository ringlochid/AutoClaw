# Standard Root policy example

Status: Reference

This example mirrors the shipped `standard-root` policy fixture.

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
