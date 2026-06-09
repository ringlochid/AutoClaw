# Distribution and database support matrix

Status: Reference

This page defines the supported v1 distribution and database matrix.

## Shipped install path

- PyPI wheel/sdist
- `pipx install autoclaw`

## Shipped DB lanes

- SQLite local-first smoke lane
- Postgres package extra via `pipx install "autoclaw[postgres]"`

## Required strong verification lane

- Postgres + Docker
- `make docker-up`
- `make test-api-db`
- `make docker-down`

## Not currently supported

- standalone binaries
- npm shim package
- Homebrew or other convenience installer
