# Set up OpenClaw agents and operator skills

AutoClaw uses two dedicated OpenClaw agents:

- **`autoclaw-worker`** executes bounded assignments. Each dispatch gives it a rendered prompt plus node MCP tools such as `record_checkpoint` and `return_boundary`.
- **`autoclaw-operator`** is the trusted operator agent. It inspects tasks, resolves human requests, controls command runs, uploads definitions, and starts tasks through operator MCP tools.

`autoclaw onboard` and `autoclaw openclaw setup` create or reconcile both agents and the AutoClaw MCP servers in the OpenClaw config. This page explains what gets written, how to verify it, and how to make the operator agent genuinely useful with workspace instructions and skills.

## What AutoClaw writes into the OpenClaw config

After onboarding, the OpenClaw config contains entries shaped like this (values come from your local install):

```jsonc
{
    "agents": {
        "list": [
            {
                // Executes AutoClaw assignments. AutoClaw dispatches sessions to this agent.
                "id": "autoclaw-worker",
                "workspace": "/home/you/.openclaw/workspaces/autoclaw-worker",
                "identity": { "name": "AutoClaw Worker", "theme": "quiet, exact, tool-first" },
                // Trusted local posture: the controller bounds the work, not the sandbox.
                "sandbox": { "mode": "off" },
                "tools": {
                    "profile": "full",
                    // A worker must never steer tasks: operator tools are denied.
                    "deny": ["autoclaw-operator__*"],
                    // Direct gateway exec without approval prompts.
                    "exec": { "host": "gateway", "security": "full", "ask": "off" }
                }
            },
            {
                // Trusted operator agent: inspects and steers tasks, never executes node work.
                "id": "autoclaw-operator",
                "workspace": "/home/you/.openclaw/workspaces/autoclaw-operator",
                "sandbox": { "mode": "off" },
                "tools": {
                    "profile": "full",
                    // An operator must never act as a node: node tools are denied.
                    "deny": ["autoclaw-node__*"],
                    "exec": { "host": "gateway", "security": "full", "ask": "off" }
                }
            }
        ]
    },
    "mcp": {
        "servers": {
            // Operator control plane. Authenticated with the AutoClaw API key
            // from the [security] section of the AutoClaw config.toml.
            "autoclaw-operator": {
                "url": "http://127.0.0.1:18125/operator/mcp",
                "transport": "streamable-http",
                "headers": { "Authorization": "Bearer <autoclaw api_key>" }
            },
            // Node runtime tools. No static header: every call must carry the
            // dispatch-local session_key plus task_id, which the controller
            // validates against the live session, dispatch, assignment, and attempt.
            "autoclaw-node": {
                "url": "http://127.0.0.1:18125/node/mcp",
                "transport": "streamable-http"
            }
        }
    },
    "gateway": {
        // AutoClaw talks to this Gateway. Loopback plus token auth is the
        // recommended supported shape.
        "port": 18789,
        "bind": "loopback",
        "auth": { "mode": "token", "token": "<gateway token>" }
    }
}
```

The two ports are different products:

- `18125` is the AutoClaw API and MCP bind port, from `server.port` in the AutoClaw `config.toml`.
- `18789` is the OpenClaw Gateway port, stored in AutoClaw as `openclaw.base_url`.

Do not hand-edit the AutoClaw-owned entries. When they drift, run `autoclaw openclaw doctor --fix` to repair only the AutoClaw-owned slice, or `autoclaw openclaw setup` to reconcile it from scratch.

## Verify ports, tokens, and Gateway policy

When you are unsure what your install is actually using:

```bash
# OpenClaw side: Gateway port, bind, auth mode, reachability.
openclaw gateway status

# AutoClaw side: resolved config including server.port and openclaw.base_url.
autoclaw config show

# Compatibility probe: reports the support classification, agent state,
# MCP server state, and Gateway auth shape without writing anything.
autoclaw openclaw check --json
```

AutoClaw requires a loopback Gateway. Token auth is the recommended shape; password auth and explicit no-auth loopback are supported compatibility shapes. Non-loopback, trusted-proxy, and ambiguous auth are blocked. See [Prepare OpenClaw first](../start/prepare-openclaw.md).

The exec/sandbox posture above is deliberately trusted and direct — full tools, gateway exec, no approval prompts, sandbox off. This is the practical "YOLO" direction for the dedicated AutoClaw agents. Use it only on a trusted local machine with a workspace you are willing to let an agent edit. AutoClaw bounds workflow authority; it does not make unsafe operating-system access safe.

## Source the example files

The canonical public source for the examples is `https://github.com/ringlochid/AutoClaw`.

If you are inside a checkout, use the local `examples/openclaw/` files. Without a checkout, clone the public repo:

```bash
git clone https://github.com/ringlochid/AutoClaw.git
cd AutoClaw
```

The copy commands below assume you are in a checkout.

## Give the worker workspace an AGENTS.md

Worker sessions start fresh each dispatch. A short `AGENTS.md` in the worker agent's workspace keeps every session in the worker lane before the first tool call.

Copy the [worker workspace agent instructions](../../examples/openclaw/worker-workspace/AGENTS.md) into the worker workspace:

```bash
cp examples/openclaw/worker-workspace/AGENTS.md \
   ~/.openclaw/workspaces/autoclaw-worker/AGENTS.md
```

The example makes three rules explicit: read the AutoClaw assignment surfaces first, stay inside the current assignment, and report through checkpoints and artifacts instead of chat prose.

## Install the operator skills

The operator skills teach an OpenClaw agent how to drive AutoClaw well: when to use it, which tools to call in which order, and what not to improvise.

| Skill | Job |
| --- | --- |
| [`autoclaw-task-interview`](../../examples/openclaw/skills/autoclaw-task-interview/SKILL.md) | intake interview for new work: confirm intent, scope, workflow shape, and `roots` workspace/context paths before anything is drafted or launched |
| [`autoclaw-work-orchestrator`](../../examples/openclaw/skills/autoclaw-work-orchestrator/SKILL.md) | decide whether AutoClaw fits, choose or adapt a workflow, draft task-compose, launch |
| [`autoclaw-runtime-operator`](../../examples/openclaw/skills/autoclaw-runtime-operator/SKILL.md) | inspect running tasks, resolve human requests, handle command runs, control and recover |
| [`autoclaw-definition-author`](../../examples/openclaw/skills/autoclaw-definition-author/SKILL.md) | write roles, policies, workflows, and task-compose YAML |

The interview skill is the intake gate: "use AutoClaw to build me an MVP" means launching AutoClaw work, and the skill makes the operator confirm scope, workflow shape, and real `roots` directories instead of guessing — or misreading the request as integrating AutoClaw into an app.

Copy them into the operator agent's workspace skills directory:

```bash
mkdir -p ~/.openclaw/workspaces/autoclaw-operator/skills
cp -r examples/openclaw/skills/* ~/.openclaw/workspaces/autoclaw-operator/skills/
```

Then confirm OpenClaw sees them through its skills listing for that agent. Use OpenClaw's own skills documentation if your install resolves skills from a different directory.

With the skills installed, you can drive AutoClaw conversationally: "start a research task on X", "why is task Y waiting?", "write me a bugfix workflow and launch it against this repo."

## Optional: give your main assistant operator access

You can also let an existing personal OpenClaw agent act as the AutoClaw operator instead of chatting with `autoclaw-operator` directly. Give that agent the same two guardrails:

- deny `autoclaw-node__*` so it can never act as a node
- install the four operator skills in its workspace

The operator MCP server entry is global in the OpenClaw config, so any agent whose tool policy allows `autoclaw-operator__*` can operate tasks. Keep that set small: an operator is a trusted lane, and its Authorization header is the AutoClaw API key.

Never give one agent both node and operator tools. The worker/operator separation is what keeps execution authority and steering authority distinct.

## Related pages

- [Operator model](../concepts/operator-model.md)
- [Prepare OpenClaw first](../start/prepare-openclaw.md)
- [OpenClaw integration problems](../help/openclaw-integration.md)
- [Use the OpenClaw integration](../reference/operator/use-openclaw-integration.md)
