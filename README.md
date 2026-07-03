<p align="center"> <img src="docs/assets/autoclaw-mark.png" alt="AutoClaw" width="140"> </p>

<h1 align="center">AutoClaw</h1>

<p align="center"><strong>Local-first orchestration for delegated AI work.</strong></p>

<p align="center"> <a href="docs/start/getting-started.md">Get started</a> · <a href="docs/start/configuration-and-settings.md">Config</a> · <a href="docs/start/prepare-openclaw.md">Prepare OpenClaw</a> · <a href="docs/concepts/README.md">Concepts</a> · <a href="docs/guides/README.md">Guides</a> · <a href="docs/reference/README.md">Reference</a> </p>

---

**AutoClaw turns agent work into auditable workflow runs.** Define reusable roles, policies, and workflows; launch one task-compose file; then let the controller dispatch bounded assignments, collect checkpoints and artifacts, handle human waits and long commands, and keep the whole run inspectable and recoverable.

> ⚠️ **Early development.** AutoClaw is not production-ready yet. Interfaces, schemas, and workflows may change or break.

## Why AutoClaw?

**AutoClaw gives delegated agent work durable state, reviewable evidence, and runtime control.**

- **Reusable definitions.** Roles, policies, workflows, and task-compose files make repeated work launchable instead of reprompted.
- **Controller-owned state.** Tasks, flow revisions, assignments, attempts, checkpoints, and artifacts live in AutoClaw state.
- **Evidence-first handoff.** Nodes receive explicit criteria and publish checkpoints or artifacts for later nodes, operators, and humans.
- **Runtime control.** Retry, replan, pause, continue, human requests, and command runs are modeled as task state.
- **Local console.** Start tasks, inspect the workflow graph, follow events, and open artifacts from `http://127.0.0.1:<server.port>/`.
- **Local-first storage.** Per-task directories and the default SQLite database stay in your data directory; Postgres is available for concurrent runs.
- **Harness boundary.** OpenClaw Gateway is the shipped adapter today; AutoClaw keeps orchestration above the agent loop.

## What AutoClaw is for

Use AutoClaw for:

- feature delivery with implementation, verification, review, and closure
- bugfix pipelines with triage, patch, tests, and release evidence
- research briefs where sources, synthesis, and review must be inspectable
- delivery batches where a parent assigns one bounded scope at a time
- long-running verification where logs, cancellation, and continuation matter

Use OpenClaw directly for:

- "What does this error mean?"
- "Run this one command."
- "Summarize this page."
- unbounded background autonomy with no evidence contract

## Supported today

The current shipped support is intentionally narrow:

| Layer                  | Current support                                                                  |
| ---------------------- | -------------------------------------------------------------------------------- |
| Agent adapter          | OpenClaw Gateway only                                                            |
| OpenClaw version       | 2026.6.10 or newer                                                               |
| Model/provider routing | owned by the configured OpenClaw harness                                         |
| Gateway shape          | loopback Gateway; token auth recommended                                         |
| Other allowed auth     | loopback password auth or explicit loopback no-auth                              |
| Blocked Gateway shapes | non-loopback, trusted-proxy, ambiguous auth, unresolved secrets                  |
| Managed service        | Linux `systemd --user`                                                           |
| macOS / Windows        | foreground `autoclaw serve` proof path; native service parity is not shipped yet |
| Storage                | SQLite by default; Postgres extra for concurrent task runs                       |
| Shipped definitions    | 14 workflow fixtures, 26 roles, and 7 standard policies                          |

## Quickstart

Prepare OpenClaw first. AutoClaw fails fast when the OpenClaw shape is unsupported, so inspect it before onboarding:

If you already have a trusted OpenClaw agent with shell access, you can ask it to do the setup:

```text
Go to https://github.com/ringlochid/AutoClaw. Read the README and docs/start/getting-started.md, then set up AutoClaw on this machine. Use the documented published-package path unless the repo says otherwise. Run the setup and health checks. Install or copy every operator skill from examples/openclaw/skills into the AutoClaw operator agent's skills directory, and copy examples/openclaw/worker-workspace/AGENTS.md into the AutoClaw worker workspace. Do not print secrets. Report the config path, console URL, data directory, installed skills, and any blocked step.
```

Manual setup:

```bash
# Run or repair OpenClaw's own first-run setup (Gateway, auth, workspace).
openclaw onboard

# Inspect the install, Gateway state, and update channel AutoClaw will rely on.
openclaw status
openclaw gateway status
openclaw update status
openclaw doctor --lint
```

`openclaw gateway status` shows the Gateway port, bind, and auth mode. Keep the Gateway on loopback with token auth for the clearest path; see [Prepare OpenClaw first](docs/start/prepare-openclaw.md).

Then install AutoClaw:

```bash
# Install the published package (or: uv tool install autoclaw).
pipx install autoclaw

# Guided first-run setup: writes local config, seeds packaged definitions,
# reconciles the OpenClaw worker/operator agents and MCP servers, and can
# install the managed service. Prompts for the AutoClaw API/MCP port
# (default 18125) and the OpenClaw Gateway port (default 18789).
autoclaw onboard

# Check local config, database, packaged resources, service, and integration health.
autoclaw doctor

# Read-only OpenClaw compatibility probe; run it first whenever setup is blocked.
autoclaw openclaw check
```

Find your local console port and data directory with:

```bash
autoclaw config path
autoclaw config show --json
```

Open the console at `http://127.0.0.1:<server.port>/`. The default AutoClaw port is `18125`.

For concurrent task runs, use the Postgres extra:

```bash
pipx install "autoclaw[postgres]"
export AUTOCLAW_DATABASE_URL=postgresql+asyncpg://user:pass@127.0.0.1:5432/autoclaw
```

The fully supported managed-service path is Linux with `systemd --user` (Ubuntu, Debian, Fedora, Arch, and similar hosts). On macOS and Windows, run `autoclaw serve` in the foreground.

## Let an operator agent drive it

Onboarding creates two dedicated OpenClaw agents:

- **`autoclaw-worker`** executes bounded assignments through node MCP tools.
- **`autoclaw-operator`** is a trusted agent that inspects tasks, resolves human requests, launches work, and authors definitions through operator MCP tools.

Install the operator skills so you can drive AutoClaw from an OpenClaw chat — "start a research task", "why is task X waiting?", "write me a bugfix workflow":

- [`autoclaw-work-orchestrator`](examples/openclaw/skills/autoclaw-work-orchestrator/SKILL.md) — decide whether AutoClaw fits, pick a workflow, draft task-compose, launch
- [`autoclaw-runtime-operator`](examples/openclaw/skills/autoclaw-runtime-operator/SKILL.md) — inspect, resolve waits, control, and recover running tasks
- [`autoclaw-definition-author`](examples/openclaw/skills/autoclaw-definition-author/SKILL.md) — write roles, policies, workflows, and task-compose files

Setup, the annotated OpenClaw config block, and the worker workspace `AGENTS.md` are in [Set up OpenClaw agents and operator skills](docs/guides/set-up-openclaw-agents-and-skills.md).

## First task: research brief

Use either the local console or a task-compose YAML file. **The fastest first run is through the local console.**

Use `autoclaw config show --json` when you need the port. The same output includes `paths.data_dir`; per-task directories live under `<data_dir>/tasks/<task_id>/`.

### Start from the console

Open `http://127.0.0.1:<server.port>/task-start`, select `topic-research-brief`, fill the task fields, and start the task.

![Start the topic-research-brief workflow from the local console](docs/assets/first-task-console.gif)

### Start from a task-compose file

Create `task-compose.yaml` in an empty working directory:

```yaml
task:
    key: first-research-brief
    title: My first task
    summary: Produce one concise restaurant research brief.
    instruction: >-
      Research notable restaurants and write one brief.
workflow:
    key: topic-research-brief
```

Start it:

```bash
autoclaw task-compose start --file ./task-compose.yaml --json
```

After either method, open the task in the console:

```text
http://127.0.0.1:<server.port>/tasks/<task_id>
```

For diagnostics, read the generated files in the task directory:

```text
_runtime/workflow-manifest.md                       # current workflow shape
_runtime/attempts/<attempt_id>/assignment.md        # the active node's mission
_runtime/attempts/<attempt_id>/latest-checkpoint.md # durable progress or handoff
outputs/artifacts/                                  # published outputs
```

A successful first run produces `workspace/research_brief.md` and publishes it as the `research_brief` artifact. The task-owned workspace file is:

```text
<data_dir>/tasks/<task_id>/workspace/research_brief.md
```

On Linux with defaults, that is:

```text
~/.local/share/autoclaw/tasks/<task_id>/workspace/research_brief.md
```

![Example first-task research brief result](docs/assets/first-task-result.png)

See [Inspect a task](docs/start/inspect-a-task.md).

## How AutoClaw works

```mermaid
flowchart LR
    D[Role / policy / workflow definitions] --> R[Definition registry]
    T[task-compose.yaml] --> C[Compiler]
    R --> C
    C --> F[Controller-owned flow]
    F --> A[Current assignment]
    A --> H[Harness loop<br/>OpenClaw today]
    H --> N[MCP node tools<br/>checkpoint / artifacts / assign child / boundary]
    N --> F
    F --> O[Operator read and control surfaces]
```

To the harness, `record_checkpoint` or `return_boundary` are ordinary tool calls. To AutoClaw, they are validated state transitions against the current task, dispatch, assignment, attempt, and flow revision. That boundary is what makes the harness replaceable while AutoClaw keeps workflow truth.

More detail: [Orchestration model](docs/concepts/orchestration-model.md).

## Core concepts

| Concept      | Definition                                                                                          |
| ------------ | --------------------------------------------------------------------------------------------------- |
| Workflow     | Reusable node tree, routing rules, criteria, and evidence contract                                  |
| Task-compose | One launch request with task metadata, instruction, workflow key, and optional `roots` path mapping |
| Assignment   | Controller-owned scope, instructions, and evidence requirements for a node                          |
| Checkpoint   | Controller-recorded progress or handoff record for one assignment attempt                           |
| Artifact     | Durable output published into a workflow-declared slot                                              |

More concepts: [Core concepts](docs/concepts/core-concepts.md).

## AutoClaw and OpenClaw

**OpenClaw is the harness. AutoClaw is the orchestration layer above it.**

| Dimension                 | OpenClaw                                                | AutoClaw                                               |
| ------------------------- | ------------------------------------------------------- | ------------------------------------------------------ |
| Primary role              | Agent harness and assistant runtime                     | Workflow orchestration for delegated work              |
| User motion               | Ask an assistant                                        | Launch and supervise a structured task                 |
| Core loop                 | Context -> model -> tools -> stream -> transcript       | Assign -> execute -> checkpoint -> boundary -> advance |
| State owner               | Conversation, tools, skills, sessions, channels         | Task, flow, assignment, attempt, checkpoint, artifact  |
| Best fit                  | Personal assistance, local tool use, ad hoc coding/help | Long work with evidence, review, retry, replan, waits  |
| Failure mode if stretched | Long work becomes transcript-heavy                      | Small work becomes over-structured                     |

OpenClaw executes agent turns. AutoClaw decides which bounded assignment runs next and whether the evidence is good enough to advance.

OpenClaw Gateway is the shipped adapter today. The same MCP-tool boundary can host other capable harnesses, such as Codex or Claude Code, as future adapters.

## Compared with other agent systems

AutoClaw is an orchestration layer for local-first delegated work with controller-owned evidence.

| System                         | Strong at                                                         | AutoClaw contrast                                                                                                                                                    |
| ------------------------------ | ----------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LangGraph                      | Low-level durable graph runtime for stateful agents               | AutoClaw decouples orchestration from the harness loop, materializes task evidence outside the graph, and treats replan as a controller-approved change after launch |
| CrewAI                         | Role-based crews and approachable flow abstractions               | AutoClaw makes roles subordinate to controller-minted assignments, checkpoints, artifacts, budgets, waits, and release decisions                                     |
| AutoGen / AG2                  | Multi-agent conversation and group-chat patterns                  | AutoClaw is workflow/tree/evidence centered: handoff happens through controller-validated assignments, checkpoints, and artifacts                                    |
| OpenAI Agents SDK              | Lightweight agents, handoffs, guardrails, tracing, sandbox agents | AutoClaw keeps orchestration state, evidence, replan, and recovery outside one provider SDK or agent loop                                                            |
| oh-my-claudecode / oh-my-codex | Harness-side workflow layers, team modes, tmux/worktree workers   | AutoClaw makes orchestration controller-owned: assignments, checkpoints, artifacts, waits, replan, and release are legal state transitions                           |
| A2A                            | Interop between independent opaque agents                         | AutoClaw can use A2A at external agent boundaries later; internally, handoff records are checked and minted by the controller                                        |
| OpenClaw                       | Local agent harness, tools, skills, sessions, and channels        | AutoClaw adds a real orchestration layer above the harness instead of replacing the harness                                                                          |

## Documentation

- [Getting started](docs/start/getting-started.md)
- [Configuration and settings](docs/start/configuration-and-settings.md)
- [Prepare OpenClaw first](docs/start/prepare-openclaw.md)
- [Set up OpenClaw agents and operator skills](docs/guides/set-up-openclaw-agents-and-skills.md)
- [Orchestration model](docs/concepts/orchestration-model.md)
- [Core concepts](docs/concepts/core-concepts.md)
- [Runtime model](docs/concepts/runtime-model.md)
- [Design workflows and instructions](docs/guides/design-workflows-and-instructions.md)
- [Write a workflow](docs/guides/write-a-workflow.md)
- [Write a policy](docs/guides/write-a-policy.md)
- [Inspect and control a task](docs/guides/inspect-and-control-a-task.md)
- [CLI reference](docs/reference/cli/README.md)

## License

MIT. See [LICENSE](LICENSE).
