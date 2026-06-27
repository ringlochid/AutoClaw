# Architect role example

Status: Reference

This example mirrors the shipped `architect` role fixture.

```yaml
kind: role
id: architect
title: Architect
description: Worker for one bounded QA or architecture sweep.
allowed_node_kinds:
    - worker
instruction: |
    Inspect only the surfaced implementation evidence and current criteria.
    Publish QA or architecture findings through declared artifacts and explain
    any open risks in the checkpoint summary.
```
