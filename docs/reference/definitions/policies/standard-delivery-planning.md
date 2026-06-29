# Standard delivery unit policy example

Status: Reference

This example mirrors the shipped `standard-delivery-planning` policy fixture.

```yaml
kind: policy
id: standard-delivery-planning
title: Standard Delivery Planning
description: Default behavior for planning bounded delivery units.
applies_to:
- worker
instruction: >-
  Translate a larger purpose into bounded work without losing the higher-level goal. Research current artifacts, constraints, dependencies, local precedent, and best-practice shape before proposing the package. Include package objective, scope, prerequisites, consumes, produces, criteria, sequencing, review and verification gates, risks, and open questions. Mark ambiguity as a planning risk when scope, owner, dependency, acceptance criteria, or evidence is not settled by current sources. Do not implement the package unless explicitly assigned.
```
