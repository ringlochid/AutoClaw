# Install and setup problems

The current setup path is `autoclaw init` followed by `autoclaw setup --provider <provider>`.

## `autoclaw` is not found

Confirm the isolated tool installed and its executable directory is on `PATH`. For `uv`, run `uv tool update-shell` and restart the shell if needed.

## `init` fails

Check that:

- the config and data-directory paths are writable
- the selected port is valid
- the database URL is reachable
- the existing config is not being overwritten unintentionally

Use `autoclaw init --help` for explicit path and bind options. Do not use `--force` until you understand which existing local state it would replace.

## Provider setup fails

Read the configured state, then check the exact provider:

```bash
autoclaw providers status <provider> --json
autoclaw providers check <provider> --json
```

Authenticate through `autoclaw providers login <provider>` or the provider's native supported flow. A configured provider is not automatically reachable or logged in.

## No default provider

The first configured provider normally becomes the default. Set one explicitly when needed:

```bash
autoclaw providers set-default codex
```

AutoClaw will not fall back to another configured provider silently.
