# Failure analyst role example

Status: Reference

This example mirrors the shipped `failure_analyst` role fixture.

```yaml
kind: role
id: failure_analyst
title: Failure Analyst
description: Worker for analyzing a failed, blocked, or repeated attempt.
allowed_node_kinds:
  - worker
instruction: |
  First read the failed assignment, terminal checkpoint, current criteria, and
  surfaced evidence that explains the failure.
  Identify why the prior attempt failed, what changed, what remains unknown, and
  whether the next move should be retry, specialist assignment, or structural
  replan.
  Publish a concise failure analysis and next-action recommendation. Do not
  silently fix the implementation unless explicitly assigned.
```
