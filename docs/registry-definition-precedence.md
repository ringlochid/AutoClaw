# Registry definition precedence

This is the phase-7 canonical note for how AutoClaw discovers file-backed definitions before they are bootstrapped into the DB registry.

## Source order

For each definition kind (`roles`, `policies`, `workflows`, `skills`), discovery happens in this order:

1. **packaged definitions** from `app.resources/definitions/<kind>`
2. **filesystem overrides** from an explicit definitions root

Filesystem overrides can come from:

1. the explicit `definitions_root` argument passed into `iter_definition_files(...)` / `bootstrap_registry(...)`
2. otherwise `AUTOCLAW_DEFINITIONS_ROOT`
3. otherwise configured `paths.definitions_root`

If a filesystem file has the same filename as a packaged file, the filesystem file wins for that filename.

## Ordering rule

`iter_definition_files(...)` returns one file per filename.

- packaged-only files are included
- filesystem-only files are included
- for duplicate filenames, the filesystem file replaces the packaged one
- returned ordering keeps packaged-known names first, then filesystem-only names, both alphabetically by filename

That means the list is deterministic, while still making override replacement explicit.

## Identity rule

Definition identity is strict:

- role/policy/workflow: `yaml id == filename stem`
- skill: `yaml key == filename stem`

Bootstrap/import should fail fast on mismatches instead of silently inventing a new key.

## Bootstrap/publish rule

`bootstrap_registry(...)` imports the discovered files into the DB registry.

- files are bootstrap/import inputs
- the DB registry is the live runtime truth after import
- packaged definitions are the default source for installed/package-first usage
- filesystem definitions are the explicit override path for local development or operator-managed overrides

## Skill version default

When a skill seed or external skill reference does not pin a version, AutoClaw uses the synthetic version label:

- `external-current`

This is the compatibility/default label for unpinned external skill references.
