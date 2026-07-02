# AutoClaw

Local-first orchestration for delegated AI work.

> ⚠️ **Early Development Notice:** This project is in early development and is not yet ready for production use. Features may change, break, or be incomplete. Use at your own risk.

AutoClaw turns agent work into auditable workflow runs. Define reusable roles, policies, and workflows; launch one task-compose file; then let the controller dispatch bounded assignments, collect checkpoints and artifacts, handle waits, and keep the run inspectable and recoverable.

[Get started](docs/start/getting-started.md) · [Prepare OpenClaw](docs/start/prepare-openclaw.md) · [Concepts](docs/concepts/README.md) · [Guides](docs/guides/README.md) · [Reference](docs/reference/README.md)

## Why AutoClaw?

**Use AutoClaw when a task needs more than a chat transcript.**

- Assign work to root, parent, and worker nodes with explicit authority.
- Preserve durable evidence through assignments, checkpoints, and artifacts.
- Route long tasks through retry, replan, human waits, and command runs.
- Inspect and recover work from controller state instead of hidden provider memory.
- Keep the agent loop replaceable while AutoClaw owns workflow truth.

AutoClaw is not for every prompt. If the work is one short answer, one direct command, or one ad hoc assistant session, OpenClaw by itself is usually the better surface.

## AutoClaw and OpenClaw

**OpenClaw is the harness. AutoClaw is the orchestration tool.**

| Dimension                 | OpenClaw                                                | AutoClaw                                               |
| ------------------------- | ------------------------------------------------------- | ------------------------------------------------------ |
| Primary role              | Agent harness and assistant runtime                     | Workflow orchestration for delegated work              |
| User motion               | Ask an assistant                                        | Launch and supervise a structured task                 |
| Core loop                 | Context -> model -> tools -> stream -> transcript       | Assign -> execute -> checkpoint -> boundary -> advance |
| State owner               | Conversation, tools, skills, sessions, channels         | Task, flow, assignment, attempt, checkpoint, artifact  |
| Best fit                  | Personal assistance, local tool use, ad hoc coding/help | Long work with evidence, review, retry, replan, waits  |
| Failure mode if stretched | Long work becomes transcript-heavy                      | Small work becomes over-structured                     |

AutoClaw owns the orchestration layer above agent systems: workflow state, assignment authority, evidence, recovery, and release.

OpenClaw is the only provider that have been integrated. The same pattern can integrate with other capable agent products like codex.

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

## Current supported path

**Use the supported path before debugging custom adapters or service managers.**

AutoClaw is early local-first orchestration software. The current package is built around one narrow, supported lane:

| Layer                  | Current support                                                                  |
| ---------------------- | -------------------------------------------------------------------------------- |
| Agent adapter          | OpenClaw Gateway only                                                            |
| Model/provider routing | owned by the configured OpenClaw harness                                         |
| Gateway shape          | loopback Gateway; token auth recommended                                         |
| Other allowed auth     | loopback password auth or explicit loopback no-auth                              |
| Blocked Gateway shapes | non-loopback, trusted-proxy, ambiguous auth, unresolved secrets                  |
| Managed service        | Linux `systemd --user`                                                           |
| macOS / Windows        | foreground `autoclaw serve` proof path; native service parity is not shipped yet |
| Storage                | SQLite by default; Postgres extra for concurrent task runs                       |

The public surface will grow around workflows, operator UI, and additional adapters. Those should not change the core rule: AutoClaw owns controller truth; harnesses run agent turns.

## Quickstart

Prepare OpenClaw first:

```bash
# Run or repair OpenClaw's own first-run setup.
openclaw onboard

# Inspect the local OpenClaw installation and Gateway.
openclaw status
openclaw doctor --lint
openclaw update status
openclaw gateway status
```

Then install AutoClaw and run the first checks:

```bash
# Install the public AutoClaw package.
pipx install autoclaw

# Write local AutoClaw config and reconcile the OpenClaw integration slice.
autoclaw onboard

# Check local AutoClaw state.
autoclaw doctor

# Check OpenClaw compatibility without writing.
autoclaw openclaw check
```

If you prefer `uv`, use the same package through uv's tool-install lane:

```bash
uv tool install autoclaw
```

Use the Postgres extra when you want to run multiple tasks concurrently:

```bash
pipx install "autoclaw[postgres]"
# or
uv tool install "autoclaw[postgres]"
export AUTOCLAW_DATABASE_URL=postgresql+asyncpg://user:pass@127.0.0.1:5432/autoclaw
```

The fully supported managed-service path is Linux with `systemd --user`; this is distro-shaped rather than distro-branded, so Ubuntu, Debian, Fedora, Arch, and similar systemd user-service hosts are the intended lane. macOS and Windows can use `autoclaw serve` for foreground local proof, but their native service managers are not shipped parity yet.

## First task: research brief

Create `task-compose.yaml` in an empty working directory:

```yaml
task:
    key: first-research-brief
    title: My first task
    summary: Find the best restaurants.
    instruction: >-
      Find best restaurants in the world.
workflow:
    key: topic-research-brief
```

Start it:

```bash
autoclaw task-compose start --file ./task-compose.yaml --json
```

##TODO inspect ui or ask operator.

Then read the generated runtime files:

```text
_runtime/workflow-manifest.md
_runtime/attempts/<attempt_id>/assignment.md
_runtime/attempts/<attempt_id>/latest-checkpoint.md
outputs/artifacts/
```

A successful first run has a workflow manifest, a controller-issued assignment, a checkpoint, and a `research_brief.md` artifact that all match the launched topic.

## How AutoClaw works

```mermaid
flowchart LR
    D[Role / policy / workflow definitions] --> R[Definition registry]
    T[Task-compose file] --> C[Compiler]
    R --> C
    C --> F[Controller-owned flow]
    F --> A[Current assignment]
    A --> M[MCP node tools]
    M --> H[Harness loop<br/>OpenClaw]
    H --> P[Checkpoint + artifacts]
    P --> F
    F --> O[Operator read/control surfaces]
```

AutoClaw's controller owns runtime truth. Prompts and generated files are interfaces over that truth; they are not the authority.

MCP runtime tools are the control boundary between the harness loop and the controller. Tool calls such as `record_checkpoint`, `return_boundary`, `assign_child`, `open_human_request`, `start_command_run`, and release/replan are validated state transitions against the current task, dispatch, assignment, attempt, and flow revision.

More details are in [Orchestration model](docs/concepts/orchestration-model.md).

## Core concepts

| Concept      | Definition                                                                  |
| ------------ | --------------------------------------------------------------------------- |
| Workflow     | Reusable node tree, routing rules, criteria, and evidence contract          |
| Task-compose | One launch request with task metadata, instruction, workflow key, and roots |
| Assignment   | Controller-owned scope, instructions, and evidence requirements for a node  |
| Checkpoint   | Controller-recorded progress or handoff record for one assignment attempt   |
| Artifact     | Durable output published into a workflow-declared slot                      |

More concepts are in [Core concepts](docs/concepts/core-concepts.md).

## Compared with other agent systems

AutoClaw is an orchestration layer for local-first delegated work with controller-owned evidence.

| System                         | Strong at                                                         | AutoClaw contrast                                                                                                                                                                     |
| ------------------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| LangGraph                      | Low-level durable graph runtime for stateful agents               | AutoClaw decouples orchestration from the harness loop; materializes task evidence outside the graph; replan is a controller-approved change, so graph can change after a task starts |
| CrewAI                         | Role-based crews and approachable flow abstractions               | AutoClaw makes roles subordinate to controller-minted assignments, checkpoints, artifacts, budgets, waits, and release decisions                                                      |
| AutoGen / AG2                  | Multi-agent conversation and group-chat patterns                  | AutoClaw is workflow/tree/evidence centered: handoff happens through controller-validated assignments, checkpoints, and artifacts                                                     |
| OpenAI Agents SDK              | Lightweight agents, handoffs, guardrails, tracing, sandbox agents | AutoClaw keeps orchestration state, evidence, replan, and recovery outside one provider SDK or agent loop                                                                             |
| oh-my-claudecode / oh-my-codex | Harness-side workflow layers, team modes, tmux/worktree workers   | AutoClaw makes orchestration controller-owned: assignments, checkpoints, artifacts, waits, replan, and release are legal state transitions                                            |
| A2A                            | Interop between independent opaque agents                         | AutoClaw can use A2A at external agent boundaries later; internally, handoff records are checked and minted by the controller                                                         |
| OpenClaw                       | Local agent harness, tools, skills, sessions, and channels        | AutoClaw adds a real orchestration layer above the harness instead of replacing the harness                                                                                           |

## Documentation

- [Getting started](docs/start/getting-started.md)
- [Prepare OpenClaw first](docs/start/prepare-openclaw.md)
- [Orchestration model](docs/concepts/orchestration-model.md)
- [Core concepts](docs/concepts/core-concepts.md)
- [Runtime model](docs/concepts/runtime-model.md)
- [Design workflows and instructions](docs/guides/design-workflows-and-instructions.md)
- [Write a policy](docs/guides/write-a-policy.md)
- [Write a workflow](docs/guides/write-a-workflow.md)
- [Inspect and control a task](docs/guides/inspect-and-control-a-task.md)
- [CLI reference](docs/reference/cli/README.md)

## License

MIT. See [LICENSE](LICENSE).
