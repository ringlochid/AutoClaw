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

The managed service lane uses a Linux user service. Confirm the unit uses the same config, data directory, database URL, and port as your shell. Rerun `autoclaw service install` to reconcile an older generated unit after upgrading AutoClaw; it preserves an existing environment file unless `--force` is passed.

If start or restart fails, AutoClaw prints bounded `systemctl` output and the exact inspection commands. You can also run them directly:

```bash
systemctl --user status autoclaw.service --no-pager
journalctl --user -u autoclaw.service -n 50 --no-pager
```

Remove obsolete settings named by validation errors from the selected config or service environment file, then rerun `autoclaw service install`. Validation output names the field without echoing its rejected value. Do not use `--force` merely to reconcile the unit because it also replaces the managed environment file. `--debug` works before or after the leaf command, for example `autoclaw service start --debug`; parse mistakes remain concise.

If health succeeds and readiness fails, continue with [Postgres and database problems](postgres-and-database.md).
