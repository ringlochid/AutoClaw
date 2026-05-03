# Docs answer-sourcing checklist

Status: Reference

Use this checklist whenever Codex needs an answer during redesign implementation. For the canonical hierarchy, use [AGENTS.md](../../../AGENTS.md).

- [ ] I checked `docs/redesign/` first for the target answer
- [ ] I checked the named appendix owner when exact API/schema/prompt detail mattered
- [ ] I checked the named appendix owner when exact API/schema/prompt/payload detail mattered
- [ ] I checked `docs/current/` second if migration truth or current behavior mattered
- [ ] I inspected code/tests only after the canonical docs pass
- [ ] I checked the implementation file lock map before widening scope or touching adjacent surfaces
- [ ] I used `docs/archive/` or older source packs only because canonical docs were still silent
- [ ] I can point to the exact canonical page that answers the question
- [ ] if the canonical docs were silent, I recorded the gap explicitly
- [ ] I did not ask the user a question already answered by canonical docs
- [ ] I did not invent a new contract from repo shape alone
- [ ] I treated the current phase page as the sole phase-local execution contract
- [ ] I treated the current phase page as the sole phase-local delivery contract
