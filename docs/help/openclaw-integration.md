# OpenClaw integration problems

Use this page when `openclaw check`, OpenClaw setup, wrapper repair, or OpenClaw-gated service startup fails.

The current shipped AutoClaw adapter is OpenClaw Gateway. Model/provider routing belongs to OpenClaw; AutoClaw owns the orchestration state and runtime transitions above that harness.

## What the check means

`autoclaw openclaw check` is the read-only compatibility probe. It checks direct config, wrapper, compatibility, selected worker/operator agent state, and OpenClaw-managed AutoClaw MCP server state.

It does not prove session-effective worker-session MCP mounting by itself.

## Supported shapes

The shipped v1 support check allows:

- loopback Gateway with token auth, which is the recommended first-run path
- loopback Gateway with password auth
- explicit loopback no-auth Gateway

AutoClaw supports OpenClaw 2026.6.10 or newer. Run `openclaw --version` and `openclaw update status` when integration behavior looks stale.

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
- provide the Gateway token or password through supported config or flags, preferably token auth for a first run
- run `autoclaw openclaw setup` after the support check is healthy
- run `autoclaw openclaw doctor --fix` when the integration slice drifted

Do not expect AutoClaw to rewrite unsupported OpenClaw Gateway policy into a supported shape.

## Recommended OpenClaw posture

For the early local lane, use dedicated OpenClaw worker and operator agents for AutoClaw. The practical profile is trusted local execution: full tools, Gateway exec, no approval prompts, and sandbox off for those dedicated agents.

That posture is sometimes described as "YOLO mode", but the important rule is narrower: use it only on a trusted local host and a workspace where agent edits are acceptable. AutoClaw constrains workflow authority; it does not sandbox arbitrary operating-system access.

Do not use the same OpenClaw agent for worker execution and operator control. The worker receives bounded assignments. The operator inspects, resolves waits, and steers the task through operator-authorized surfaces.

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
- [Set up OpenClaw agents and operator skills](../guides/set-up-openclaw-agents-and-skills.md)
- [Prepare OpenClaw first](../start/prepare-openclaw.md)
- [CLI support checks and self-contained setup](../reference/cli/cli-fast-fail-and-self-contained-report.md)
- [OpenClaw integration boundary](../reference/operator/openclaw-integration-boundary.md)
