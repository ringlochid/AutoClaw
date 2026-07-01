# Distribution and database support matrix

This page defines the supported v1 distribution and database matrix.

## Shipped package paths

- PyPI wheel/sdist
- `pipx install autoclaw`
- `uv tool install autoclaw`

## Shipped DB lanes

- SQLite local-first smoke lane
- Postgres lane via `pipx install "autoclaw[postgres]"` plus a real `AUTOCLAW_DATABASE_URL`
- Postgres lane via `uv tool install "autoclaw[postgres]"` plus a real `AUTOCLAW_DATABASE_URL`

## Service-manager support

- Linux with `systemd --user`: shipped v1 managed-service path
- intended Linux distros: Ubuntu, Debian, Fedora, Arch, and similar systemd user-service hosts with Python 3.12
- macOS `launchd`: not yet shipped as v1 parity
- Windows Scheduled Task: not yet shipped as v1 parity
- macOS and Windows foreground path: `autoclaw serve`

Repo-native editable checkout is a contributor/dev path, not part of the public distribution matrix.

## Required strong verification lane

- `make test-api-db`

Optional manual development stack commands remain available when you want a long-lived local Postgres container:

- `make docker-up`
- `make docker-down`

## Not currently supported

- standalone binaries
- npm shim package
- Homebrew or other convenience installer
- native macOS or Windows managed-service parity
