# Standard release policy example

Status: Reference

This example mirrors the shipped `standard-release` policy fixture.

```yaml
kind: policy
id: standard-release
title: Standard Release
description: Ordinary release or closure worker behavior.
applies_to:
    - worker
instruction: >-
  First identify what release means for the current assignment, what criteria must be
  satisfied, and which refs are authoritative. Use only surfaced release evidence and
  current criteria. Treat unclear release criteria, stale evidence, conflicting refs, or
  missing approval as a release gap, not as implicit approval. Publish ordinary release
  artifacts and checkpoint output. Record release readiness, evidence gaps, or blockers
  in the checkpoint summary and published release artifacts rather than inventing a
  second result enum.
```
