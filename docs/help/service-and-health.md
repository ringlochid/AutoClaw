# Service and health problems

`/healthz` proves the process is answering. `/readyz` also checks controller database readiness.

## Check the foreground path

```bash
autoclaw serve
```

In another shell:

```bash
curl -sS http://127.0.0.1:18125/healthz
curl -sS http://127.0.0.1:18125/readyz
```

If this works, the application and active config are usable.

## Check the managed service

```bash
autoclaw service status --json
autoclaw service render
```

The managed service lane uses a Linux user service. Confirm the unit uses the same config, data directory, database URL, and port as your shell. Use `autoclaw service install` only when the service has not been installed.

If health succeeds and readiness fails, continue with [Postgres and database problems](postgres-and-database.md).
