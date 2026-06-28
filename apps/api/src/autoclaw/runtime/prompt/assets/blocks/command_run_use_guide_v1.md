### Command Run Use Guide

Use `start_command_run` only for controller-managed long command work.

Open a command run when the command is expected to exceed about two minutes, needs async waiting, or needs controller-owned cancellation/terminal-result tracking.

Run ordinary short commands inline in the current dispatch. A normal inline command should stay comfortably under about two minutes; if it cannot, use `start_command_run` when capability allows it, or checkpoint the blocker.

Rules:

- Command run is only for command execution, not a generic external wait, workflow boundary, task continue action, local process runner, or raw stdout/stderr capture surface.
- Fill `command`, `description`, optional `workdir`, and optional `timeout_seconds`.
- The `description` should explain why this command belongs in the controller-managed long-run lane and what terminal result will decide next.
- Do not start a command run just to avoid writing a checkpoint or choosing a boundary.
- Treat returned command-run summaries and log refs as controller-owned command-run truth; do not invent progress from stale logs or provider traces.
- After `start_command_run` succeeds, stop this dispatch turn and wait for controller redispatch with command-run continuation context.
