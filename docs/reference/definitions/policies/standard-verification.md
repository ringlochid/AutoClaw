# Standard verification policy example

Status: Reference

This example mirrors the shipped `standard-verification` policy fixture.

```yaml
kind: policy
id: standard-verification
title: Standard Verification
description: Default verification worker behavior.
applies_to:
  - worker
instruction: |
  Verification is criteria and evidence first.
  Identify the intended behavior, exact acceptance criteria, current artifact or
  patch under test, and commands or observations that prove the result.
  Publish reproducible pass/fail evidence, untested areas, and blockers through
  declared artifacts and checkpoint handoff.
  Green means verification completed; parent/root still decides release.
```
