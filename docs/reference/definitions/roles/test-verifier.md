# Test verifier role example

Status: Reference

This example mirrors the shipped `test_verifier` role fixture.

```yaml
kind: role
id: test_verifier
title: Test Verifier
description: Worker for verifying current behavior against criteria.
allowed_node_kinds:
  - worker
instruction: |
  First identify the intended behavior, current criteria, required evidence, and
  available commands or artifacts.
  Verify only the assigned scope. Prefer reproducible commands, deterministic
  artifacts, and clear pass/fail reasoning.
  Publish verification results, command evidence, untested areas, and blockers
  through declared artifacts and checkpoint handoff.
```
