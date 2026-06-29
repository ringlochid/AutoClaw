# OpenClaw support and compatibility

Status: Target

This page defines the V2 operator-facing support and compatibility contract for the `openclaw` provider family.

## Core rule

The OpenClaw provider lane is compatible only when the host can launch AutoClaw-owned OpenClaw worker and operator agent profiles with the required gateway, MCP, execution, and sandbox shape.

## Minimum compatible managed profile

The managed OpenClaw worker and operator profiles should use a host shape such as:

```yaml
workspace: ~/.openclaw/workspaces/<agent_id>
agentDir: ~/.openclaw/agents/<agent_id>/agent
tools:
    profile: full
    exec:
        host: gateway
        security: full
        ask: off
        backgroundMs: 30000
        timeoutSec: 3600
sandbox:
    mode: off
```

Rules:

- the exact managed workspace root is the OpenClaw workspace lane under the operator's home directory rather than an arbitrary detached temp path
- `sandbox.mode: off` is a real compatibility rule for the AutoClaw-managed OpenClaw provider lane
- `tools.profile: full` plus `tools.exec.ask: off` is the operator-facing equivalent of the informal `YOLO mode` description, but the canonical contract should use the real field names
- support docs should freeze the actual managed workspace root rather than paraphrasing it loosely as "some workdir under `~/`"

## Gateway and setup ownership

OpenClaw support also owns:

- gateway auth and connect compatibility
- AutoClaw-managed OpenClaw worker or operator agent profile patching
- AutoClaw-managed OpenClaw MCP server registration
- provider-specific `check`, `setup`, and `doctor` remediation ownership

Rules:

- setup and doctor must verify or reconcile the managed profile shape rather than assuming the host already matches it
- support docs may summarize the lane as "non-sandbox full-access gateway execution", but they should not replace the exact config names with slang alone
- provider-specific support rules stay machine-local and must not leak into portable authored workflow schema

## Non-goals

This page does not define:

- portable workflow node fields
- controller lineage truth
- Codex or Claude compatibility rules

## Related contracts

- [Provider support and compatibility](provider-support-and-compatibility.md)
- [Provider-aware setup, configure, and doctor](provider-aware-setup-and-doctor.md)
- [Provider preference and runtime config](provider-selection-and-runtime-config.md)
