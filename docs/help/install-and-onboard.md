# Install and setup problems

The interactive setup path is `autoclaw init` followed by `autoclaw setup`. The first command confirms local state. The second asks for the primary/default provider, checks it, offers supported login, and asks about additional providers.

## `autoclaw` is not found

Confirm the isolated tool installed and its executable directory is on `PATH`. For `uv`, run `uv tool update-shell` and restart the shell if needed.

## `init` fails

Check that:

- the config and data-directory paths are writable
- the selected port is valid
- the database URL is reachable
- the existing config is not being overwritten unintentionally

Rerun `autoclaw init` and choose the default `keep` action to verify existing config and database state. Use `autoclaw init --help` for explicit path and bind options. Do not select replacement or use `--force` until you understand which existing config it would replace. `init` does not reset an old database schema.

## Provider setup fails

Read the configured state, then check the exact provider:

```bash
autoclaw providers status <provider> --json
autoclaw providers check <provider> --json
```

Guided setup offers native Codex login when its check says authentication is required. You can also authenticate through `autoclaw providers login <provider>` or the provider's native supported flow. A configured provider is not automatically reachable or logged in. Human checks show confirmed, failed, or not tested; use `--json` for the stable axis enum values.

## No default provider

Guided setup explicitly selects the primary/default provider and preserves it while adding providers. Set one directly when needed:

```bash
autoclaw providers set-default codex
```

AutoClaw will not fall back to another configured provider silently.

## Setup is waiting for input in a script

Add `--non-interactive` and pass required selections as options. `--json` and non-TTY invocation also do not prompt.

```bash
autoclaw init --non-interactive
autoclaw setup --provider codex --non-interactive
```
