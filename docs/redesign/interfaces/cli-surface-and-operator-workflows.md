# CLI surface and operator workflows

Status: Target

This page defines the target root CLI surface and the operator-facing OpenClaw workflow nouns.

The canonical runtime term is `tool`. `plugin` is adapter or package-wrapper terminology only and does not replace the canonical tool surfaces.

The current shipped root CLI in this repo is narrower than the full target surface below. Definition-import, task-compose, and OpenClaw wrapper nouns remain deferred Phase 5A / 5B targets until their owning work packages land in code.

## Target root command groups

- `autoclaw init`
- `autoclaw serve`
- `autoclaw up`
- `autoclaw doctor`
- `autoclaw config ...`
- `autoclaw db ...`
- `autoclaw definitions ...`
- `autoclaw task-compose ...`
- `autoclaw openclaw ...`
- `autoclaw service ...`

## Target primary user-facing commands

- `autoclaw init`
- `autoclaw doctor`
- `autoclaw serve`
- `autoclaw db upgrade`
- `autoclaw definitions import --file <definition_path> [--overwrite reject|allow_new_revision]`
- `autoclaw definitions import`
- `autoclaw task-compose start --file <task_compose_path>`
- `autoclaw openclaw onboard`
- `autoclaw openclaw check`

## Target support and admin commands

- `autoclaw config path`
- `autoclaw config show`
- `autoclaw openclaw setup`
- `autoclaw openclaw configure`
- `autoclaw openclaw doctor`
- `autoclaw service install`
- `autoclaw service start`
- `autoclaw service stop`
- `autoclaw service restart`
- `autoclaw service status`

## OpenClaw lifecycle contract

- `autoclaw doctor` remains the AutoClaw-local health and repair command for local config, DB, and service prerequisites.
- `autoclaw init` is AutoClaw-local only. It owns local AutoClaw config, directories, and runtime prerequisites. It is not the OpenClaw setup noun.
- `autoclaw openclaw check` is read-only verification. It may report warnings or missing prerequisites, but it does not write config, workspace state, or MCP definitions.
- `autoclaw openclaw setup` is the direct baseline-write path. It writes only baseline OpenClaw config, workspace material, and the two canonical MCP tool-surface definitions.
- `autoclaw openclaw onboard` is the guided first-run entrypoint. It is the primary operator-facing path for a new OpenClaw connection and may guide the operator through `check` and `setup`.
- `autoclaw openclaw configure` is subset re-entry only. It revisits one slice of an existing OpenClaw setup without becoming a full first-run flow or a repair command.
- `autoclaw openclaw doctor` is repair and remediation only. It exists for migration, repair, and cleanup of previously written OpenClaw state.
- `bootstrap` is not the primary canonical noun for install, first-run, or OpenClaw reconfiguration. Reserve it for internal runtime or materialization contracts.
- live OpenClaw dispatch, wait, abort, and callback authority validation remain runtime-owned; these commands configure or verify that runtime path, but they do not own it

## CLI output and interaction rules

- `--json` is output-shape only. It does not change command ownership, write semantics, or interactive intent by itself.
- `--non-interactive` controls automation behavior. It disables guided prompts and requires the command to operate from already-resolved inputs.
- `--plain`, `--no-color`, and `NO_COLOR` disable rich styling.
- Rich styling is TTY-only. Non-TTY output must stay stable and readable without assuming ANSI-capable consumers.
- when styling is present, mirror OpenClaw's lobster palette rather than inventing a separate AutoClaw palette. At minimum keep the heading and severity roles aligned to OpenClaw's accent, success, warn, error, and muted colors.
- the frozen palette roles are: accent `#FF5A2D`, success `#2FBF71`, warn `#FFB020`, error `#E23D2D`, and muted `#8B7F77`.
- Onboarding, setup, configure, and doctor output should mirror OpenClaw's warning-first tone rather than inventing a separate AutoClaw aesthetic.

## CLI visual style lock

When TTY-rich styling is enabled, copy OpenClaw's visual grammar closely:

- terminal-native, monospace, high-contrast presentation over decorative or app-like styling
- one prominent command header area near the top, typically combining product name, version, and the current command label
- accent-colored section titles and separators rather than mixed arbitrary accent colors
- boxed or framed warning, status, and review panels for dense structured content such as doctor findings, security disclaimers, and setup notes
- aligned key/value readouts, compact lists, and dense diagnostics when a command is primarily reporting state
- emphasis on clarity and scanability over minimalism; the visual style may be information-dense as long as section boundaries stay obvious
- if a short banner, wordmark, or tagline is present, treat it as secondary flourish only; required guidance must still live in the structured headings, panels, prompts, and command output

Do not reinterpret "copy OpenClaw style" as a license to redesign the CLI into generic pretty output, dashboard-like cards, or a new AutoClaw-specific color language.

## Rule

Guarded definition upload remains the canonical API/tool lifecycle surface. Any later root CLI import surface is a local authoring front door over that registry truth rather than a replacement for it. Runtime flow control remains API/tool-first and is not frozen as a root CLI command family on the current shipped subset. Adapter wrappers may mirror canonical routes, but they do not create a third truth surface.

Deferred task-start wrapper rule:

- any later `autoclaw task-compose start --file <task_compose_path>` wrapper reads one local YAML file
- that file must parse exactly as `TaskStartRequest`
- the wrapper then submits that exact body to the same canonical backend task-start handler as `POST /tasks/start`
- launch concurrency and root-path conflict handling are backend concerns, not separate CLI semantics

Deferred CLI import rules:

- canonical definition files carry top-level `kind`, so a later root CLI wrapper does not take `--kind`
- zero-arg `autoclaw definitions import` is a shallow current-working-directory scan only
- zero-arg import scans only top-level `*.yaml` files in the current working directory
- zero-arg import does not recurse into subdirectories
- zero-arg import does not scan a configured root or package-bundled root
- `--file` is the explicit local import path for that later wrapper
- bundle-manifest batch import, if retained in implementation, is compatibility/helper only rather than the primary frozen v1 authoring path

Removed from live canon:

- legacy directory/recursive definition-import variants
- `bootstrap` as the primary operator-facing noun for OpenClaw onboarding, setup, or reconfiguration

## Related contracts

- `cli-api-and-package-shape.md`
- `api-surface-and-trust-lane-map.md`
- `definition-ingest-and-upload-contract.md`
