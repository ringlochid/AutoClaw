# FAQ

## Should I use `pipx` or `uv`?

Use `pipx` for the default public v1 path. Use `uv` if you prefer its tool-install workflow and want the same published package artifacts.

## Is repo checkout the normal install story?

No. Editable checkout is the contributor/dev lane. The public v1 install story is the published package.

## Is managed-service support cross-platform in v1?

No. The fully supported v1 managed-service path is Linux with `systemd --user`. Ubuntu, Debian, Fedora, Arch, and similar systemd user-service hosts are the intended lane when Python 3.12 is available. macOS and Windows can use the foreground `autoclaw serve` path, but native service-manager parity is later work.

## Why does AutoClaw require a supported OpenClaw shape before setup?

Setup and service commands need a reliable local OpenClaw integration. AutoClaw supports loopback Gateway shapes with token auth, password auth, or explicit no-auth loopback. It blocks non-loopback, trusted-proxy, ambiguous, or unresolved-secret shapes instead of writing partial local state.

## What is the difference between `doctor` and `openclaw check`?

`autoclaw doctor` checks local AutoClaw config, database, packaged resources, managed-service visibility, and the AutoClaw-owned OpenClaw integration slice.

`autoclaw openclaw check` is the read-only OpenClaw compatibility and integration-material probe. Use it first when setup or service startup is blocked by OpenClaw support.

## Where do definitions live after import?

Repo files are authoring inputs. After successful import, the controller-owned registry becomes authoritative for those definitions.

## Should I choose a shipped workflow or write my own?

Write your own workflow when the automation has its own purpose, evidence path, and completion criteria. Shipped definitions are examples and first-run material, not a menu that limits what AutoClaw can orchestrate.

## What is the difference between workflow and task-compose?

A workflow is reusable definition truth. It owns the node tree, durable inputs, outputs, and criteria.

Task-compose is one launch input. It names one task, selects a workflow, provides task-specific instruction, and can bind roots such as `workspace` and `context`. If roots are omitted, AutoClaw uses task-owned defaults.

## Why does task start use `POST /tasks/start` instead of a separate task-compose route?

Current shipped task-compose launch is a launch-body contract, not a separate public route family. The CLI wrapper reads one local file and submits the same task-start body as the canonical backend task-start handler.

## When should a node use a human request?

Use a human request when the node needs typed human judgment: direction, approval, input, or review. Do not use it as a generic status update.

## When should a node use a command run?

Use a command run for controller-managed long-running command work that needs progress, logs, terminal state, or cancellation. for example tests or model training. Ordinary commands should run inline and finish comfortably under about two minutes.

## Is an operator always a human?

No. AutoClaw's intended operator shape is a trusted OpenClaw operator agent profile using operator tools. A human can also act as an operator through UI surfaces, but that is a different surface from an agent using tools.

## When should I use Postgres?

Use SQLite for the default local-first lane. Use Postgres when you need to run multiple tasks concurrently. Install `autoclaw[postgres]` and set `AUTOCLAW_DATABASE_URL` before onboarding.
