# AutoClaw

Status: Reference

Last verified: 2026-05-07

AutoClaw is a controlled agent runtime for multi-step work that must stay auditable, replayable, and operationally recoverable.

This root README is a front-door router only. Public docs live under `docs/`. Internal canon lives under `docs-internal/`.

## Start here

- Public docs map: [Public docs home](docs/README.md)
- Product narrative: [Product docs home](docs/product/README.md)
- Public reference: [Reference docs home](docs/reference/README.md)
- Internal canon: [Internal canon home](docs-internal/README.md)
- Coding-agent policy: [Coding agent contract](AGENTS.md)
- Coding standards: [Coding standards](STYLE.md)

## Repo shape

- `apps/api/` - backend API, runtime, DB, CLI, and tests
- `apps/api/src/autoclaw/definitions/seeds/` - committed shipped definition seeds
- `docs/` - public product and reference docs
- `docs-internal/` - internal design, current-contrast, execution, ADR, and archive canon
- `scripts/` - repo tooling, including docs validation under `scripts/docs/`
- `examples/` - example workflows and supporting artifacts

## Common verification lanes

- Unit backend suite: `make test-api-unit`
- Local integration verification: `make test-api-integration`
- Docker/Postgres verification: `make test-api-db`
- Docs freeze validation: `./.venv/bin/python -m scripts.docs.docs_freeze.cli`

## License

Licensed under MIT. See [LICENSE](LICENSE).

## Surface rule

Use this page for fast routing only.

Do not treat it as the authoritative source for detailed runtime behavior, target design contracts, or phase-closeout status.
