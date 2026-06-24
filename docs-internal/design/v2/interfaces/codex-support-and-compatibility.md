# Codex support and compatibility

Status: Target

This page defines the V2 operator-facing support and compatibility contract for the `codex` provider family.

## Core rule

Codex support docs must freeze the exact local app-server, auth, execution-mode, sandbox, workspace or workdir, and MCP-surface requirements needed for AutoClaw to treat Codex as launch-compatible.

Until those setup and doctor checks are implemented, this page may describe required support fields and target expectations, but it must not present OpenClaw-specific compatibility rules as if they were already proven for Codex.

## Minimum support fields

Codex support docs should eventually freeze:

- the supported Codex runtime family such as app-server or SDK wrapper shape
- required auth or local startup prerequisites
- required execution or approval mode when one is necessary
- required sandbox mode when one is necessary
- required workspace or workdir rule when one is a real compatibility constraint
- required shared `node` and `operator` MCP surface availability
- the `autoclaw codex ...` setup or doctor branch that verifies the same rules

Rules:

- do not assume the OpenClaw managed rule set such as `sandbox.mode: off` or a home-rooted workspace also applies to Codex unless the Codex adapter and doctor path explicitly prove it
- if operator-facing guidance uses shorthand such as `YOLO mode`, the canonical contract must still freeze the actual Codex-side config or runtime check name
- target support docs may say that exact mode or workdir constraints are still pending implementation, but they should name the unresolved fields explicitly rather than leaving them implicit

## Non-goals

This page does not define:

- controller lineage truth
- portable workflow provider preference semantics
- OpenClaw or Claude support rules

## Related contracts

- [Provider support and compatibility](provider-support-and-compatibility.md)
- [Provider-aware setup, configure, and doctor](provider-aware-setup-and-doctor.md)
- [Codex app-server adapter](../architecture/adapters/codex-app-server.md)
