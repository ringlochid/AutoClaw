# Troubleshooting

Status: Reference

Use this page for the most common install, onboarding, and first-run failures.

## `autoclaw onboard` fails before writing

Cause:
- OpenClaw support preflight blocked the host shape

Check:
- run `autoclaw openclaw check --json`

Likely fixes:
- confirm the OpenClaw gateway is loopback, not remote
- confirm auth mode is supported and the required secret is available
- avoid assuming AutoClaw will rewrite OpenClaw gateway policy for you

## `autoclaw service start` fails

Cause:
- Linux `systemd --user` support is the only fully shipped v1 managed-service lane

Check:
- run `autoclaw service status`
- if needed, use `autoclaw serve` to prove the foreground runtime path

## `autoclaw doctor` is healthy but task start fails

Cause:
- definition import or task-compose launch input is invalid

Check:
- verify the workflow key exists
- verify the task-compose file matches the current launch contract
- use [definition and task-compose YAML contract](../reference/api/definition-and-task-compose-yaml-contract.md)

## Postgres lane fails

Cause:
- the stronger DB-backed lane depends on the package extra plus Docker/Postgres setup

Check:
- confirm you installed `autoclaw[postgres]`
- confirm `AUTOCLAW_DATABASE_URL` is set
- use [Use Postgres](../reference/maintainers/use-postgres.md)
- run [Run Docker Postgres verification](../reference/maintainers/run-docker-postgres-verification.md)
