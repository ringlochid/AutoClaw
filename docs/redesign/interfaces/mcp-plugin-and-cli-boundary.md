# MCP, Plugin, and CLI Boundary

Status: Target

This page is the front-door owner for how AutoClaw exposes tools in Phase 4 and
how `MCP`, `plugin`, `bundle`, and `CLI` terminology split.

## Core rules

- AutoClaw has exactly two canonical MCP tool surfaces:
  - `operator MCP`
  - `node MCP`
- `operator MCP` is the standard external parity surface.
- `node MCP` is private, internal, and dispatch-bound.
- `tool` is the canonical runtime term.
- `plugin` and `bundle` are packaging or parity-wrapper terms only.
- no canonical shared MCP catalog or session may mix operator-safe tools and
  dispatch-bound node tools
- operator identity is an external caller fact, not canonical runtime DB truth
- Phase 4 freezes the boundary only; Phase 5 owns the detailed CLI
  lifecycle/style contract and should mirror OpenClaw's CLI posture

## Surface map

| Surface | Caller | Scope | Canonical use | Not allowed |
| --- | --- | --- | --- | --- |
| `operator MCP` | external operator or trusted external automation | task-scoped external authority | definition discovery and guarded upload, task start, runtime reads and control, operator snapshot and trace, and any explicitly allowed task-scoped observability reads | dispatch-bound parent/root tools, checkpoint publication, boundary return |
| `node MCP` | the currently bound node execution context | one live dispatch authority | `record_checkpoint`, `return_boundary`, and legal parent/root tool calls during the open dispatch | operator pause/continue/cancel, shared operator catalogs, generic external automation use |
| `CLI` | local human or local trusted automation | local machine bootstrap | install, doctor, DB flows, local file import, local task start, OpenClaw checks | becoming a third tool-runtime authority model |

## OpenClaw attachment rule

When OpenClaw carries one of these MCP surfaces, the attachment belongs to the
OpenClaw package or wrapper bootstrap, not to controller runtime truth.

Rules:

- an OpenClaw package or parity wrapper may attach one MCP surface to an
  OpenClaw agent/profile pair
- if one package ships both MCP surfaces, they still remain separate surfaces
  with separate trust boundaries
- do not teach one shared mixed MCP catalog or one shared mixed MCP session as
  the canonical model
- OpenClaw agent or profile attachment does not become task, flow, assignment,
  attempt, or operator truth in the runtime DB
- operator identity remains an external authority fact on CLI, API, and MCP
  boundaries rather than a canonical runtime object family

## Recommended transports

- OpenClaw-backed dispatch lifecycle uses Gateway WS RPC `agent`,
  `agent.wait`, and `sessions.abort` as the canonical machine control path.
- HTTP `POST /v1/responses` is compatibility or fallback transport only.
- `operator MCP` mirrors the operator-safe route families under `/definitions`,
  `/tasks/start`, `/runtime`, `/operator`, and any explicitly allowed
  task-scoped `/observability` reads.
- `node MCP` binds privately to callback semantics. If it rides HTTP,
  `/callback/tasks/{task_id}/...` is an internal binding example only, not a
  public external contract.

## Vocabulary rule

Use these terms exactly:

- `tool`: a canonical runtime action or read surface
- `MCP surface`: one exposed tool inventory with one trust boundary
- `plugin` or `bundle`: OpenClaw packaging, parity-wrapper, or bootstrap
  terminology only
- `operator`: an external authority shape, not a runtime DB identity family

## Related contracts

- [API surface and trust-lane map](api-surface-and-trust-lane-map.md)
- [MCP tool reference](plugin-tool-reference.md)
- [Human and operator control surface](human-and-operator-control-surface.md)
- [CLI surface and operator workflows](cli-surface-and-operator-workflows.md)
- [CLI, API, and package shape](cli-api-and-package-shape.md)
- [OpenClaw worker and gateway contract](../architecture/openclaw-worker-and-gateway-contract.md)
