# Standard long command worker policy example

Status: Reference

This example mirrors the shipped `standard-long-command-worker` policy fixture.

```yaml
kind: policy
id: standard-long-command-worker
title: Standard Long Command Worker
description: Worker behavior for bounded assignments that may need controller-managed long command runs.
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
  Use controller-managed command runs only for commands expected to be long, asynchronous, or log-heavy enough that inline execution is the wrong surface. Normal shell commands should stay inline and comfortably under two minutes. If duration is ambiguous, estimate from command history, scope, cache state, test size, and repo conventions before choosing the surface. If an inline command is likely to exceed two minutes, switch to the command-run capability when available or report the need instead of letting a dispatch stall. Publish command intent, command identifiers or log refs, result status, evidence, untested areas, and blockers through declared artifacts and checkpoint handoff.
```

