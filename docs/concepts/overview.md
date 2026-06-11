# Overview

Status: Reference

AutoClaw is a local-first workflow control plane for structured work that needs explicit runtime truth, durable artifacts, and operator recovery surfaces.

At a high level it combines:

- authored definitions for roles, policies, and workflows
- authored task-compose launch input that stays separate from the importable definition files
- deterministic compile and task-start behavior
- controller-owned runtime state
- OpenClaw-backed delegated execution
- operator-visible read, control, and recovery surfaces

## Where to go next

- [Core concepts](core-concepts.md) for the main nouns
- [Workflow lanes](workflow-lanes.md) for minimal, normal, and maximal shapes
- [Definitions model](definitions-model.md) for the authored inputs
- [API reference](../reference/api/README.md) and [CLI reference](../reference/cli/README.md) for exact contracts
