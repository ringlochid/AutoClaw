# Hard-reset checklist

Status: Reference

Use this checklist during Phase 0.5 total code hard reset.

## Main repo classification

- [ ] every major main-repo subsystem was classified in the reset matrix
- [ ] each subsystem decision is exactly one of:
  - `delete now`
  - `retain infra shell only`
  - `plugin rebuild`
- [ ] no subsystem is left in an ambiguous "decide later" state

## DB/schema baseline reset

- [ ] redesign implementation is explicitly using a fresh-baseline schema reset
- [ ] current redesign-incompatible target-facing tables/models are marked for deletion
- [ ] DB reset procedure is implemented and evidenced
- [ ] no carried migration history or packaged migration mirror remains in the baseline
- [ ] the reset leaves no seed content or reset-only schema by convenience
- [ ] rerun-validation-after-reset procedure is implemented and evidenced

## Test inventory

- [ ] unit and integration tests were classified into:
  - retain infra shell only
  - delete as stale-contract coverage
- [ ] stale task-start/task-upload tests were classified explicitly
- [ ] stale `/flows/*` and operator-drilldown tests were classified explicitly
- [ ] stale registry/skill/approval contract tests were classified explicitly
- [ ] stale callback-binding lineage and `/tasks/composes/start` contract tests were classified explicitly
- [ ] plugin old-contract tests were classified explicitly

## Plugin rebuild

- [ ] plugin rebuild boundary is documented as target-only and near-greenfield
- [ ] target tool inventory is defined from canon first
- [ ] old approval/manifest-ack/skill-draft/skill-publish/raw-slice tools are marked for removal
- [ ] no current plugin utility survives on trust
- [ ] if no local plugin source tree exists in the checkout, that absence is recorded explicitly and Phase 4B is named as the rebuild entry point
- [ ] old plugin tests are marked for deletion intentionally

## Cleanup sign-off

- [ ] retained infra/harness/package/config scaffolding is justified explicitly
- [ ] deleted surfaces are named explicitly
- [ ] later owner phase is named where a retained infra shell rolls forward
- [ ] phase closeout is based on code reset and executed evidence, not docs alignment
- [ ] mandatory review can verify the cleanup baseline without inferring intent
