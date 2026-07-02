# Diagnostic bundle

Use this page to collect enough local evidence to debug an AutoClaw problem without guessing.

Do not paste secrets into issues, chat, logs, or tickets. Redact API keys, Gateway tokens, passwords, private task content, and private artifact content before sharing.

## Install and setup bundle

Collect:

```bash
autoclaw --version
autoclaw config path
autoclaw doctor --json
autoclaw openclaw check --json
```

If you include `autoclaw config show --json`, redact:

- `security.api_key`
- `openclaw.gateway_token`
- `openclaw.gateway_password`
- private local paths when needed

## Service and health bundle

Collect:

```bash
autoclaw service status --json
curl -sS http://127.0.0.1:18125/healthz
curl -sS http://127.0.0.1:18125/readyz
```

If you used the foreground runner, include the recent `autoclaw serve` log instead of only the service status.

## Task bundle

For a started task, collect:

- task id
- workflow key
- task root path
- current runtime readback
- operator snapshot
- operator trace
- relevant human request or command-run readback

HTTP reads:

```bash
curl -sS -H "X-AutoClaw-API-Key: <redacted>" \
  "http://127.0.0.1:18125/runtime/tasks/<task_id>"

curl -sS -H "X-AutoClaw-API-Key: <redacted>" \
  "http://127.0.0.1:18125/operator/tasks/<task_id>/snapshot"

curl -sS -H "X-AutoClaw-API-Key: <redacted>" \
  "http://127.0.0.1:18125/operator/tasks/<task_id>/trace?scope=whole&sort=occurred_at_asc"
```

Task-root files worth checking locally:

- `_runtime/workflow-manifest.md`
- `_runtime/attempts/<attempt_id>/assignment.md`
- `_runtime/attempts/<attempt_id>/latest-checkpoint.md`
- `outputs/artifacts/`

## Support-state bundle

Use support-state files only after reading current runtime state.

Useful support refs:

- delivery state
- continuity state
- watchdog state
- provider events

HTTP reads:

```bash
curl -sS -H "X-AutoClaw-API-Key: <redacted>" \
  "http://127.0.0.1:18125/observability/tasks/<task_id>/delivery-state"

curl -sS -H "X-AutoClaw-API-Key: <redacted>" \
  "http://127.0.0.1:18125/observability/tasks/<task_id>/watchdog-state"
```

The returned paths point at local task-root files. Controller/runtime reads remain the authority when support files disagree.

## Maintainer bundle

For repo changes, include:

```bash
git status --short
git diff --check
./.venv/bin/python -m scripts.docs.format_markdown --check
./.venv/bin/python -m scripts.docs.docs_freeze.cli validate
```

Add the relevant focused tests or verification lane from [choose a verification lane](../maintainers/choose-a-verification-lane.md).
