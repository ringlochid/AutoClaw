NOTE: don't trust this plan, this is just a suggestions which is not detail enough, have gpas and may be wrong! research for best practices.

1. **Clean the scaffold**
   Remove stale empty feature folders, keep only real page-owned folders, and add `AppShell`, layout primitives, UI primitives, and a small fixture/gallery route. This prevents page work from growing around messy foundations.

2. **Harden the API layer**
   Add typed endpoint helpers, structured error normalization, and production-safe runtime config. The current client sends the API key, but it does not yet parse `OperationFailure` or validation errors cleanly.

3. **Build `Tasks` first**
   Implement `GET /runtime/tasks` with view-model mappers, filters/sort/paging, empty/error/loading states, and MSW tests. This is the real runtime entrypoint.

4. **Build `Task Detail` bootstrap**
   Add task read, snapshot, trace, event backfill, SSE cursor resume, dedupe, and reset handling. This is the highest contract-risk slice, so do it before fancy UI.

5. **Add task-scoped action pages**
   Implement `Human Requests` and `Command Runs` as siblings under one task. Keep request resolution and command-run cancel/log handling separate from generic task continue/cancel.

6. **Add authoring browse/start**
   Build `Definitions` browse and `Task Start` from stored controller truth. This gives the authoring lane useful value before the editor becomes large.

7. **Build `Definition Editor` last**
   The draft-set API exists, so don’t defer because of backend absence. Defer because editor validation, preview, diff, apply, reset, and rematerialize need strong primitives and tests first.

8. **Lock proof gates**
   Keep `make check-console`, OpenAPI drift check, MSW integration tests, Playwright e2e, visual parity screenshots, and axe/focus checks as required gates for each page slice.
