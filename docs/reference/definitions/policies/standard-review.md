# Standard review policy example

Status: Reference

This example mirrors the shipped `standard-review` policy fixture.

```yaml
kind: policy
id: standard-review
title: Standard Review
description: Ordinary review worker behavior.
applies_to:
  - worker
instruction: |
  Review is criteria and evidence first.
  Green means the review assignment completed, not that the reviewed target
  automatically passes parent/root closure.
  Record approval, rejection, evidence gaps, reasoning quality, and residual
  risk in the checkpoint summary and published review artifacts rather than
  inventing a second result enum.
```
