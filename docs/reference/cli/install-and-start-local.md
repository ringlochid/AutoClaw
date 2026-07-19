# Install and start locally

AutoClaw requires Python 3.12 or newer.

## Repository development

```bash
python3.12 -m venv .venv
.venv/bin/pip install --upgrade -e ".[dev]"
.venv/bin/autoclaw init
.venv/bin/autoclaw setup --provider codex
.venv/bin/autoclaw serve
```

Choose `claude` or `openclaw` when that is the intended provider. The first configured provider becomes the default.

## Built distribution

Install a release wheel into a dedicated virtual environment. On Linux, the repository installer can create the environment and user service:

```bash
scripts/install-systemd-user.sh --wheel dist/autoclaw-*.whl
```

Use `--no-start` when installation proof must not start the service. The installer initializes config and data, installs the unit, and reports the exact paths it used.

## Verify

```bash
autoclaw status
autoclaw service status
curl --fail http://127.0.0.1:18125/healthz
curl --fail http://127.0.0.1:18125/readyz
```

The packaged console uses the same origin. Run `providers check <provider>` only when you want a live provider diagnostic.
