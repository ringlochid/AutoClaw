# Prepare OpenClaw first

AutoClaw currently runs delegated agent work through OpenClaw Gateway. Prepare and inspect OpenClaw before asking AutoClaw to write integration state.

## What AutoClaw expects

Current AutoClaw packages support the OpenClaw Gateway adapter.

| Requirement                | Supported path                                                               |
| -------------------------- | ---------------------------------------------------------------------------- |
| OpenClaw binary            | installed and discoverable from AutoClaw config, env, or `PATH`              |
| OpenClaw version           | 2026.6.10 or newer                                                           |
| Gateway bind               | loopback Gateway                                                             |
| Recommended auth           | token auth                                                                   |
| Other supported auth       | password auth, or explicit no-auth loopback                                  |
| Blocked auth/connect modes | non-loopback, trusted-proxy, ambiguous auth, unresolved token/password refs  |
| Worker/operator profiles   | separate OpenClaw agents managed or reconciled by AutoClaw                   |
| Execution posture          | trusted local profile with full tool access for the selected AutoClaw agents |

Token auth is the default documentation path because it is explicit and easy to diagnose. Password auth and explicit no-auth loopback are supported compatibility shapes, but they are not the clearest first-run story.

## Install or update OpenClaw

Install OpenClaw through a supported OpenClaw release channel before installing AutoClaw. For npm-managed installs, the package is:

```bash
# Install or update the OpenClaw CLI when npm owns the install.
npm install -g openclaw

# Confirm the OpenClaw binary that AutoClaw will later discover.
# AutoClaw supports OpenClaw 2026.6.10 or newer; update older installs first.
openclaw --version
```

If OpenClaw is already installed, inspect or update it first:

```bash
# Show the current update channel and version status.
openclaw update status

# Preview an update without changing the install.
openclaw update --dry-run

# Run OpenClaw's own repair checks after an update or config change.
openclaw doctor --lint
```

Use OpenClaw's own update channel and package-manager guidance when your install is not npm-managed.

## Configure the local Gateway

Run OpenClaw first-run setup if this host is new:

```bash
# Set up OpenClaw workspace, Gateway, auth, and local defaults.
openclaw onboard

# Inspect the configured OpenClaw runtime.
openclaw status

# Inspect Gateway service state and live reachability.
openclaw gateway status

# Probe Gateway reachability and auth capability.
openclaw gateway probe
```

For a foreground local proof run, prefer loopback token auth:

```bash
# Example foreground Gateway shape for local proof.
openclaw gateway run --bind loopback --auth token --token "$OPENCLAW_GATEWAY_TOKEN"
```

Keep the Gateway on loopback for the shipped AutoClaw path. AutoClaw blocks non-loopback and trusted-proxy Gateway shapes because it does not implement that trust boundary yet.

## Use a trusted AutoClaw profile

AutoClaw's OpenClaw setup creates or reconciles dedicated worker and operator agent profiles. Keep them separate:

- the worker profile receives bounded assignments and node tools
- the operator profile inspects and steers tasks through operator tools

After onboarding, see [set up OpenClaw agents and operator skills](../guides/set-up-openclaw-agents-and-skills.md) for the annotated config shape, the worker workspace `AGENTS.md`, and the operator skills that let you drive AutoClaw from chat.

For the early local lane, the intended OpenClaw posture is trusted and direct: full tools, gateway exec, no approval prompts, and sandbox off for the AutoClaw-managed worker/operator profiles. In OpenClaw terms, this is the practical "YOLO" direction; in docs and config, prefer the real fields: full tool profile, `exec` ask off, full security, and sandbox off.

Use that posture only on a trusted local machine and a workspace you are willing to let an agent edit. AutoClaw controls workflow authority; it does not turn unsafe operating-system permissions into safe ones.

## Check AutoClaw compatibility

After installing AutoClaw, run the read-only compatibility check:

```bash
# Install the AutoClaw package after OpenClaw is healthy.
pipx install autoclaw

# Check the OpenClaw host shape and AutoClaw-owned integration material.
autoclaw openclaw check --json
```

If the check is healthy, run onboarding:

```bash
# Write local AutoClaw config, seed packaged definitions, and reconcile OpenClaw integration.
autoclaw onboard

# Check local AutoClaw state and the OpenClaw integration slice.
autoclaw doctor
```

If the check is blocked, fix OpenClaw first. `autoclaw onboard`, `autoclaw serve`, service startup, and repair commands intentionally fail fast when the OpenClaw support shape is unsupported.

## What AutoClaw does not support yet

- direct Codex or Claude adapter launch from the current package
- non-loopback Gateway trust boundaries
- trusted-proxy Gateway auth
- native macOS `launchd` or Windows Scheduled Task service parity
- treating provider/model success as task success

Codex, Claude, and other harnesses are adapter directions, not current shipped support. Model/provider routing for today's path belongs to OpenClaw.

## Next steps

- [Get started](getting-started.md)
- [Start a task](start-a-task.md)
- [Set up OpenClaw agents and operator skills](../guides/set-up-openclaw-agents-and-skills.md)
- [OpenClaw integration problems](../help/openclaw-integration.md)
- [Install and start AutoClaw locally](../reference/cli/install-and-start-local.md)
