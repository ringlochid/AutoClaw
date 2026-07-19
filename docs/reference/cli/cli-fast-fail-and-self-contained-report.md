# CLI failure and output contract

CLI commands validate local inputs before starting their owned mutation. A failed provider configuration does not replace the current default, and a failed service render does not become an installed unit.

## Output

Commands with `--json` print one machine-readable result and no human progress text. Human output stays short and names the next useful command. `--debug` on the root command adds a traceback; normal failures return a concise error without one.

Passive commands do not turn missing checks into success. Provider authentication and reachability remain `not_checked` until `autoclaw providers check <provider>` runs.

## Safe boundaries

- `setup` and `providers configure` change AutoClaw config only.
- `providers check` is a bounded diagnostic, not a model turn.
- `task-compose start` returns after bootstrap commit, before provider start.
- `service install --no-start` writes and enables the unit without starting it.
- `db upgrade` never repairs or migrates a legacy runtime schema.
- `db reset` is destructive and must not be used as a generic health check.

Provider configuration is CLI-owned. Browser and HTTP surfaces do not expose it.
