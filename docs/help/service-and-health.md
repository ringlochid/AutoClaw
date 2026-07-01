# Service and health problems

Use this page when the API process, managed service, `/healthz`, or `/readyz` fails.

## Supported service lane

The shipped v1 managed-service path is Linux `systemd --user`.

macOS `launchd` and Windows Scheduled Task parity are not shipped v1 support. Use `autoclaw serve` as the foreground fallback for local host proof and debugging.

## `autoclaw service install` fails

Check:

```bash
autoclaw openclaw check --json
autoclaw service render
```

Likely causes:

- OpenClaw support preflight is blocked
- the selected API port is already in use
- Linux `systemd --user` is not available
- the user service unit or env-file path is not writable

Fix:

- fix the OpenClaw support check first
- choose a free API port with `--port`
- use `autoclaw serve` on hosts without shipped service-manager support

## `autoclaw service start` or `restart` fails

Check:

```bash
autoclaw service status --json
autoclaw openclaw check --json
```

If the service was never installed, run:

```bash
autoclaw service install
```

If the foreground path works but the service path fails, inspect the managed service unit and environment:

```bash
autoclaw service render
```

## `/healthz` fails

`/healthz` proves the API process is answering.

Check:

```bash
autoclaw service status
curl http://127.0.0.1:18125/healthz
```

If no managed service is running, prove the foreground path:

```bash
autoclaw serve
```

## `/readyz` fails

`/readyz` performs a database readiness check.

Check:

```bash
curl http://127.0.0.1:18125/readyz
autoclaw doctor --json
autoclaw db upgrade
```

Likely causes:

- database URL is wrong
- database server is unavailable
- schema has not been created or upgraded
- Postgres driver is missing because the package was installed without `autoclaw[postgres]`

Continue with [Postgres and database problems](postgres-and-database.md) when the failure is DB-backed.

## Related pages

- [Verify an install and runtime](../reference/cli/verify-current-install-and-runtime.md)
- [Install and start AutoClaw locally](../reference/cli/install-and-start-local.md)
- [Distribution and database support matrix](../reference/maintainers/distribution-and-database-support-matrix.md)
