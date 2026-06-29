# OpenClaw integration problems

Status: Reference

Last verified: 2026-06-28

Use this page when `openclaw check`, OpenClaw setup, wrapper repair, or OpenClaw-gated service startup fails.

## What the check means

`autoclaw openclaw check` is the read-only compatibility probe. It checks direct config, wrapper, compatibility, selected worker/operator agent state, and OpenClaw-managed AutoClaw MCP server state.

It does not prove session-effective worker-session MCP mounting by itself.

## Supported shapes

The shipped v1 support check allows:

- loopback Gateway with token auth
- loopback Gateway with password auth
- explicit loopback no-auth Gateway

The shipped v1 support check blocks:

- missing OpenClaw binary
- non-loopback Gateway
- trusted-proxy auth
- ambiguous auth mode
- unresolved token or password references
- missing required auth material

## Setup or repair is blocked

Check:

```bash
autoclaw openclaw check --json
autoclaw config path
```

Fix:

- make the OpenClaw Gateway reachable on loopback
- provide the Gateway token or password through supported config or flags
- run `autoclaw openclaw setup` after the support check is healthy
- run `autoclaw openclaw doctor --fix` when the integration slice drifted

Do not expect AutoClaw to rewrite unsupported OpenClaw Gateway policy into a supported shape.

## Onboard, doctor fix, or service startup fails on OpenClaw preflight

These commands intentionally fail fast before mutating important state:

- `autoclaw serve`
- `autoclaw onboard`
- `autoclaw configure --section all|openclaw|service`
- `autoclaw doctor --fix`
- `autoclaw openclaw setup`
- `autoclaw openclaw doctor --fix`
- `autoclaw service install|start|restart`

Use `autoclaw openclaw check --json` first. Fix the support shape, then rerun the original command.

## Integration drift

Use:

```bash
autoclaw openclaw doctor --json
```

If it reports drift and the support preflight is healthy, repair only the AutoClaw-owned OpenClaw slice:

```bash
autoclaw openclaw doctor --fix
```

## Related pages

- [Operator model](../concepts/operator-model.md)
- [CLI support checks and self-contained setup](../reference/cli/cli-fast-fail-and-self-contained-report.md)
- [OpenClaw integration boundary](../reference/operator/openclaw-integration-boundary.md)
