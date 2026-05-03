# Current definition precedence and skill-version defaults

Status: Current

Last verified: 2026-04-24

This page defines the current packaged-vs-filesystem precedence rules for definition discovery and the current default version rule for unpinned external skill references.

## Source order

For each definition kind (`roles`, `policies`, `workflows`, `skills`), discovery happens in this order:

1. packaged definitions from `app.resources/definitions/<kind>`
2. filesystem overrides from an explicit definitions root

Filesystem overrides can come from:

1. explicit `definitions_root` passed to discovery/bootstrap functions
2. otherwise `AUTOCLAW_DEFINITIONS_ROOT`
3. otherwise configured `paths.definitions_root`

If a filesystem file has the same filename as a packaged file, the filesystem file wins for that filename.

## Ordering rule

- packaged-only files are included
- filesystem-only files are included
- duplicate filenames are replaced by the filesystem file
- returned ordering keeps packaged-known names first, then filesystem-only names, both alphabetically by filename

## Identity rule

- role, policy, workflow: YAML `id` must match filename stem
- skill: YAML `key` must match filename stem

Bootstrap/import should fail fast on mismatches.

## Minimal precedence example

```text
packaged workflow: app.resources/definitions/workflows/default-bugfix.yaml
filesystem override: C:/custom-defs/workflows/default-bugfix.yaml

result: the filesystem file wins for default-bugfix.yaml
```

## Override example

```text
packaged files:
  review.yaml
  bugfix.yaml

filesystem files:
  bugfix.yaml
  docs-pass.yaml

returned order:
  review.yaml
  bugfix.yaml   <- filesystem copy replaces packaged copy
  docs-pass.yaml
```

## Skill version default

When a skill seed or external skill reference does not pin a version, AutoClaw uses:

- `external-current`

This is the compatibility/default label for unpinned external skill references in the current implementation.

It is current truth only. It is not redesign guidance.

## Evidence

- inspected code in `autoclaw-main/apps/api/app/services/registry_service.py`
- inspected source-pack docs in `../../archive/source-packs/old_version_docs/registry-definition-precedence.md`
