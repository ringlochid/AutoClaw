# Provider support and compatibility

Status: Target

This page defines the V2 operator-facing support and compatibility contract for `openclaw`, `codex`, and `claude`.

## Core rule

Provider support docs are machine-local runtime compatibility docs.

They are not:

- controller truth
- authored workflow truth
- adapter-internal implementation notes only

The support lane must tell an operator what exact host shape, auth shape, execution mode, sandbox mode, workspace or workdir rules, and doctor or setup expectations are required for one provider family to be considered compatible with AutoClaw.

## Shared support surface

V2 should expose:

- one shared support-matrix owner page
- one provider-specific support page for `openclaw`
- one provider-specific support page for `codex`
- one provider-specific support page for `claude`

Rules:

- the shared page owns common vocabulary and comparison shape
- provider-specific pages own the exact compatibility details for one provider family
- setup, configure, and doctor surfaces should point back to the same provider-specific support pages rather than duplicating the rules loosely

## Minimum support fields

Each provider-specific support page should freeze at least:

- support status such as `implemented`, `targeted`, or `deferred`
- auth or connect prerequisites
- required execution mode or approval mode when one is necessary
- required sandbox mode when one is necessary
- required workspace or workdir rules when they are real compatibility constraints
- required shared `node` and `operator` MCP surface availability
- the provider-specific setup or doctor branch that owns verification or remediation

Rules:

- exact compatibility claims should be frozen only when they are backed by the adapter contract plus setup or doctor behavior
- target-only constraints may be documented as expected future requirements, but they must not be presented as already-shipped fact
- support docs may explain a mode with operator shorthand such as `YOLO mode`, but the canonical rule should still name the real config fields or runtime checks

## Separation rule

Keep these concerns separate:

- provider support and compatibility
- authored workflow `provider_preference`
- controller-owned requested or resolved provider provenance
- adapter implementation internals

Support docs explain what this host must satisfy before a provider can launch compatibly.

They do not change portable definition schema or controller lineage truth.

## Related contracts

- [Provider-aware setup, configure, and doctor](provider-aware-setup-and-doctor.md)
- [Provider preference and runtime config](provider-selection-and-runtime-config.md)
- [OpenClaw support and compatibility](openclaw-support-and-compatibility.md)
- [Codex support and compatibility](codex-support-and-compatibility.md)
- [Claude support and compatibility](claude-support-and-compatibility.md)
