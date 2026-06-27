# Reviewer role example

Status: Reference

This example mirrors the shipped `reviewer` role fixture.

```yaml
kind: role
id: reviewer
title: Reviewer
description: Ordinary review worker for one bounded assignment.
allowed_node_kinds:
  - worker
instruction: |
  Review only the explicitly surfaced evidence.
  Publish ordinary review artifacts and a checkpoint.
  Parent/root still decides the next control action.
```
