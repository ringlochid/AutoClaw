# Install and set up AutoClaw

This is the shortest local path from installation to a running controller.

## Install

Use an isolated tool environment:

```bash
pipx install autoclaw
```

You can use `uv tool install autoclaw` instead. Install `autoclaw[postgres]` only when you plan to use Postgres.

## Create local state

```bash
autoclaw init
```

On a terminal, `init` shows the recommended local paths, database, and loopback API address before it writes. It creates the local configuration, prepares the controller database, and installs the packaged definitions. It binds the server to `127.0.0.1:18125` by default.

Rerunning `init` keeps and verifies an existing config by default. Replacing config requires an explicit selection and confirmation. It never resets a mismatched database; use `autoclaw db reset` only when destructive replacement is intended.

Use `--data-dir`, `--database-url`, `--host`, or `--port` when the defaults do not fit your machine. Keep the server on loopback for the supported local lane.

## Configure a provider

Start the provider guide:

```bash
autoclaw setup
```

The guide asks for the primary/default provider, checks it, offers supported provider-native login when needed, and asks whether to add providers. Codex and Claude are managed integrations. OpenClaw is selectable and may be the default, but its experimental compatibility setup remains user-managed.

To change the default directly later, run:

```bash
autoclaw providers set-default claude
```

For scripts, use `--non-interactive`. Non-interactive setup configures one selected route; login and checking remain explicit:

```bash
autoclaw init --non-interactive
autoclaw setup --provider codex --non-interactive
autoclaw providers login codex
autoclaw providers check codex
```

See [configuration and settings](configuration-and-settings.md) for provider behavior and authentication.

## Run AutoClaw

Start the foreground server:

```bash
autoclaw serve
```

Or install the Linux user service:

```bash
autoclaw service install
autoclaw service status
```

Open `http://127.0.0.1:18125/`. The packaged console, HTTP API, and MCP surfaces share this local server.

## Check local state

```bash
autoclaw status
autoclaw config show --json
autoclaw providers status
```

These commands read local state. Use `autoclaw providers check <provider>` for a fresh bounded diagnostic. A `not tested` axis was not directly verified; the check never starts an agent and does not treat an unknown fact as success or failure.

Next, [start a task](start-a-task.md).
