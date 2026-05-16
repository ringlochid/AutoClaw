# Superseded execution-phase compatibility pointer

Status: Reference

This compatibility pointer is retained only so legacy links do not break.

Use these canonical phase pages instead:

- [Phase 5A](phase-5a-definition-ingest-api-and-cli.md)
- [Phase 5B](phase-5b-packaging-release-and-docs-cutover.md)

Required marker carry-forward for compatibility:

- canonical API detail now lives in [API schema appendix](../../redesign/interfaces/api-schema-appendix.md)
- deferred Phase 5A CLI target includes `autoclaw definitions import --file <definition_path> [--overwrite reject|allow_new_revision]`
- deferred Phase 5A CLI target includes zero-arg `autoclaw definitions import [--overwrite reject|allow_new_revision]` for shallow current-working-directory scan only

This file is not an authoritative phase contract.
