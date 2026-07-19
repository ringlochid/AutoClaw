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

`init` creates the local configuration, prepares the controller database, and installs the packaged definitions. It binds the server to `127.0.0.1:18125` by default.

Use `--data-dir`, `--database-url`, `--host`, or `--port` when the defaults do not fit your machine. Keep the server on loopback for the supported local lane.

## Configure a provider

Choose one provider:

```bash
autoclaw setup --provider codex
autoclaw providers check codex
```

Replace `codex` with `claude` or `openclaw`. The first provider you configure becomes the default. To change it later, run:

```bash
autoclaw providers set-default claude
```

`setup` without `--provider` only prints guidance; it does not change configuration. See [configuration and settings](configuration-and-settings.md) for provider behavior and authentication.

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

These commands read local state. Provider reachability is checked only by `autoclaw providers check <provider>`.

Next, [start a task](start-a-task.md).
