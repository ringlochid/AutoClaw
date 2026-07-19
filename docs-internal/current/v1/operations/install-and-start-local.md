# Install and start AutoClaw locally

Status: Current

Last verified: 2026-07-19

AutoClaw needs Python 3.12 or newer.

## Install

For repository development:

```bash
python3.12 -m venv .venv
.venv/bin/pip install --upgrade -e ".[dev]"
```

For a built release, install the wheel into a dedicated virtual environment instead.

## Initialize

```bash
.venv/bin/autoclaw init
.venv/bin/autoclaw setup --provider codex
.venv/bin/autoclaw providers status
```

Choose `claude` or `openclaw` when that is the intended provider. The first configured provider becomes the default. Run `providers check <provider>` only when you want an explicit diagnostic.

## Start

Run in the foreground:

```bash
.venv/bin/autoclaw serve
```

Or install the Linux user service:

```bash
.venv/bin/autoclaw service install
.venv/bin/autoclaw service status
```

The default API is `http://127.0.0.1:18125`. The packaged console is on the same origin.

## Verification

```bash
curl --fail http://127.0.0.1:18125/healthz
curl --fail http://127.0.0.1:18125/readyz
```

`readyz` must succeed before starting tasks.

Do not run `autoclaw db reset` as a routine startup command. It destroys controller runtime data and controller-owned task roots.
