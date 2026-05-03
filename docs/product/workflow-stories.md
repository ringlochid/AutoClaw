# Workflow stories: minimal, normal, maximal

Status: Reference

This page describes the three canonical workflow shapes in product language.

## Minimal

One parent plus one executable child.

Use it for the smallest controller-owned task where local review and sync staging are unnecessary.

## Normal

One parent-owned execution subtree plus one internal review child and one final sync leaf.

Use it for standard delivery work where the parent verifies child outputs and findings before final closure.

## Maximal

Multiple parent-owned subtrees, local review children on major parents, direct root review children for cross-cutting release concerns, and one final sync leaf.

Use it for demanding workflow shapes where multiple execution lanes, release findings, optional root-owned `sync_prepare`, and subtree-local replans all matter.
