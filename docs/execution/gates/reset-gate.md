# Reset gate

Status: Reference

Use this gate whenever a phase changes DB schema, runtime record contract, package-install path, or public CLI/API surface.

Phase 0.5 cleanup and salvage always requires this gate because it intentionally discards old schema truth and replaces the authoritative baseline.

- [ ] the phase page explicitly says why a reset or migration check is required
- [ ] the relevant work package or milestone explicitly names the reset consequence
- [ ] migration, backfill, or reset behavior is documented
- [ ] when old schema truth is intentionally discarded, the docs say so
- [ ] reseed/bootstrap procedure is documented when reset would leave the system empty
- [ ] DB/schema reset behavior was checked explicitly when runtime or persistence truth changed
- [ ] package reinstall or package reset behavior was checked explicitly when package-install truth changed
- [ ] public CLI/API reset or cleanup behavior was checked when public surfaces changed
- [ ] cleanup, drop, or deprecation timing is recorded instead of implied
- [ ] relevant repo-native quality gates were rerun after the reset or reinstall path where that reset could invalidate prior results
- [ ] reset failures are routed into triage rather than ignored as release-only work
- [ ] stop conditions are clear if reset behavior is still ambiguous
