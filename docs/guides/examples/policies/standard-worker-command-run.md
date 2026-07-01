# Standard worker command-run policy example

Use this policy when a worker may need controller-managed long command runs.

This example teaches:

- command-run capability is separate from human-request capability
- ordinary commands should stay inline and finish comfortably under about two minutes
- command-run evidence should be published as logs, result status, and blockers

```yaml
kind: policy
id: standard-worker-command-run
title: Standard Worker Command Run
description: Guardrails for worker assignments that may need controller-managed long command runs.
applies_to:
    - worker
budget_spec:
    retry_limit: 1
capabilities:
    human_request:
        mode: deny
        allowed_kinds: []
    command_run: allow
instruction: >-
  Any command that requires longer than 2 minutes should use command runner to run. Use controller-managed command runs only for commands expected to be long, or log-heavy enough that inline execution is the wrong surface.
```
