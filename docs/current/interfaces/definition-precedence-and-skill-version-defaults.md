# Current definition precedence and skill-version defaults

Status: Current

Last verified: 2026-05-05

Legacy filename retained for searchability.

This page now defines the current seed-source precedence used by `seed_definition_registry()` and records that the older `skill_refs` defaulting story no longer ships in the current tree.

## Current seed-source order

For roles, policies, and workflows, current seeding happens in this order:

1. if `seed_definition_registry()` is called with an explicit `definitions_root`, use that override tree
2. otherwise use packaged seed files from `app.resources/definitions/**`

Current seeding does not do filename-overlay merging between packaged and filesystem trees. It chooses one root tree and seeds from that tree.

On shipped paths the repo-root mirror is not part of the shipped default seed path.
There is no automatic fallback from packaged seeds to the repo-root mirror. If
the packaged tree is missing required seed files, seeding fails with
`FileNotFoundError`.

After seeding, later compiler and runtime resolution read registry current revisions only. The chosen seed tree does not remain live authority.

## Current ordering rule

Within the chosen seed root:

- roles are seeded first
- policies are seeded second
- workflows are seeded third
- files are processed alphabetically within each kind

## Current identity rule

Current identity comes from the parsed YAML payload:

- role id -> `role_key`
- policy id -> `policy_key`
- workflow id -> `workflow_key`

The current seeding code also records `source_path` on each created revision.

For shipped packaged seeds, `source_path` is now a stable seed identity of the
form `seed://packaged/<relative-seed-path>`.

For explicit override seeding, `source_path` is recorded as
`seed://override/<root-fingerprint>/<relative-seed-path>`.

## Skill-version defaults

Current shipped definition schemas reject `skill_refs`.

That means the older default-version rule for unpinned external skill refs does not apply to the current tree. There is no live `external-current` behavior in the shipped definition models.

## Minimal precedence example

```text
explicit definitions_root passed
  -> seed from that override root only

no explicit definitions_root
  -> seed from the packaged app.resources/definitions mirror
  -> if packaged seeds are unavailable, fail
```

## Evidence

- inspected code in `apps/api/app/registry/seeds.py`
- inspected code in `apps/api/app/cli.py`
- inspected tests in `apps/api/tests/unit/test_definition_schemas.py`
- inspected tests in `apps/api/tests/unit/test_cli.py`
- inspected tests in `apps/api/tests/integration/test_registry_seed_authority.py`
