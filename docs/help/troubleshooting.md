# Troubleshooting

Use this page to route a failure to the right help topic.

Start with the visible symptom. Do not jump straight to reset or reinstall; most AutoClaw failures are clearer after `doctor`, `openclaw check`, runtime readbacks, or service health reads.

## First checks

Run these local reads before changing state:

- `autoclaw doctor`
- `autoclaw openclaw check`
- `autoclaw service status` when you use the managed Linux service
- `curl http://127.0.0.1:18125/healthz` when the API should be running
- `curl http://127.0.0.1:18125/readyz` when database readiness matters

Use `--json` when you need machine-readable output.

## Symptom map

| If you see                                                                       | Start with                                                 |
| -------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| `autoclaw` is not found, `onboard` fails, or `doctor` is unhealthy after install | [Install and onboard problems](install-and-onboard.md)     |
| `openclaw check` blocks setup, wrapper repair, or service startup                | [OpenClaw integration problems](openclaw-integration.md)   |
| `service start` fails, `/healthz` fails, or `/readyz` fails                      | [Service and health problems](service-and-health.md)       |
| `task-compose start` fails before a useful task exists                           | [Task start failures](task-start-failures.md)              |
| a task is waiting, paused, stale, or unclear after launch                        | [Task stuck or waiting](task-stuck-or-waiting.md)          |
| Postgres, migration, reset, or DB-backed verification fails                      | [Postgres and database problems](postgres-and-database.md) |

## Collect evidence

When the symptom is not obvious, collect the smallest useful diagnostic bundle:

- current command and exact error
- `autoclaw doctor --json`
- `autoclaw openclaw check --json`
- service status or foreground `serve` log when the API should be running
- task id, runtime readback, operator snapshot, and operator trace when a task already exists

Use [diagnostic bundle](diagnostic-bundle.md) for the exact command set and redaction notes.

## Avoid these shortcuts

- do not delete the data directory before reading the failing state
- do not use `continue` as a polling command
- do not treat observability support files as controller truth
- do not assume macOS or Windows managed-service parity in v1
- do not paste API keys, Gateway tokens, passwords, or private task artifacts into a report
