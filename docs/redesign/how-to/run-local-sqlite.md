# Run the redesign target on local SQLite

Status: Target

This page defines the frozen local SQLite lane.

## Procedure

1. Install or update the package: `pipx install autoclaw`
2. Run onboarding: `autoclaw init`
3. Keep SQLite as the default local DB, or set `AUTOCLAW_DATABASE_URL=sqlite+aiosqlite:///...`
4. Run migrations through the package surface: `autoclaw db upgrade`
5. Confirm health: `autoclaw doctor`
6. Start the product: `autoclaw serve`
7. Optional durable local-service path without systemd: `autoclaw service start`

## Lane rule

SQLite is the local-first smoke lane. It is not the strong concurrency or release-proof lane.
