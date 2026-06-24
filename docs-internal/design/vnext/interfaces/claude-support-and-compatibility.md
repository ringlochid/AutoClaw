# Claude support and compatibility

Status: Target

This page defines the Vnext operator-facing support and compatibility contract for the `claude` provider family.

## Core rule

Claude support docs must freeze the exact Agent SDK auth, permission-mode, sandbox, workspace or workdir, and MCP-surface requirements needed for AutoClaw to treat Claude as launch-compatible.

Until those setup and doctor checks are implemented, this page may describe required support fields and target expectations, but it must not present OpenClaw-specific compatibility rules as if they were already proven for Claude.

## Minimum support fields

Claude support docs should eventually freeze:

- the supported Claude runtime family such as Agent SDK launch shape
- required auth or local startup prerequisites
- required permission or approval mode when one is necessary
- required sandbox mode when one is necessary
- required workspace or workdir rule when one is a real compatibility constraint
- required shared `node` and `operator` MCP surface availability
- the `autoclaw claude ...` setup or doctor branch that verifies the same rules

Rules:

- do not assume the OpenClaw managed rule set such as non-sandbox gateway execution or a home-rooted workspace also applies to Claude unless the Claude adapter and doctor path explicitly prove it
- if operator-facing guidance uses shorthand such as `YOLO mode`, the canonical contract must still freeze the actual Claude-side permission or runtime check name
- target support docs may say that exact mode or workdir constraints are still pending implementation, but they should name the unresolved fields explicitly rather than leaving them implicit

## Non-goals

This page does not define:

- controller lineage truth
- portable workflow provider preference semantics
- OpenClaw or Codex support rules

## Related contracts

- [Provider support and compatibility](provider-support-and-compatibility.md)
- [Provider-aware setup, configure, and doctor](provider-aware-setup-and-doctor.md)
- [Claude Agent SDK adapter](../architecture/adapters/claude-agent-sdk.md)
