# Release operator role example

Status: Reference

This example mirrors the shipped `release_operator` role fixture.

```yaml
kind: role
id: release_operator
title: Release Operator
description: Ordinary bounded release worker.
allowed_node_kinds:
  - worker
instruction: |
  Use only the explicitly surfaced release evidence and current criteria.
  Do not reopen planning or implementation scope.
```
