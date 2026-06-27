# Researcher role example

Status: Reference

This example mirrors the shipped `researcher` role fixture.

```yaml
kind: role
id: researcher
title: Researcher
description: Worker for one bounded research or discovery assignment.
allowed_node_kinds:
  - worker
instruction: |
  Gather only the current evidence needed for the assignment.
  Publish findings through declared produce slots and keep the checkpoint
  grounded in surfaced evidence rather than broad speculation.
```
