# Cleanup and salvage checklist

Status: Reference

Use this checklist during Phase 0.5 cleanup and salvage.

## Main repo classification

- [ ] every major main-repo subsystem was classified in the salvage matrix
- [ ] each subsystem decision is exactly one of:
  - `keep`
  - `rewrite in place`
  - `delete`
  - `quarantine support-only`
  - `plugin rebuild`
- [ ] no subsystem is left in an ambiguous "decide later" state

## DB/schema baseline reset

- [ ] redesign implementation is explicitly using a fresh-baseline schema reset
- [ ] current redesign-incompatible target-facing tables/models are marked for rewrite or delete
- [ ] one new redesign baseline migration is designated as the new authoritative starting point
- [ ] current Alembic history is no longer treated as authoritative redesign history
- [ ] DB reset procedure is documented
- [ ] reseed/bootstrap procedure is documented
- [ ] rerun-validation-after-reset procedure is documented

## Test inventory

- [ ] unit and integration tests were classified into:
  - keep as-is
  - keep with small edits
  - rewrite to redesign contract
  - delete as stale-contract coverage
- [ ] stale task-start/task-upload tests were classified explicitly
- [ ] stale `/flows/*` and operator-drilldown tests were classified explicitly
- [ ] stale registry/skill/approval contract tests were classified explicitly
- [ ] plugin old-contract tests were classified explicitly

## Plugin rebuild

- [ ] plugin rebuild boundary is documented as target-only and near-greenfield
- [ ] target tool inventory is defined from canon first
- [ ] old approval/manifest-ack/skill-draft/skill-publish/raw-slice tools are marked for removal
- [ ] reusable plugin utilities are explicitly kept or discarded
- [ ] old plugin tests are marked rewrite/delete intentionally

## Cleanup sign-off

- [ ] retained infra/harness/package/config scaffolding is justified explicitly
- [ ] deleted or quarantined surfaces are named explicitly
- [ ] later owner phase is named where a kept/rewrite-in-place subsystem rolls forward
- [ ] mandatory review can verify the cleanup baseline without inferring intent
