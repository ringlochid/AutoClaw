# Packaging guide

Status: Reference

Use this page as the maintainer front door for the public package and install story.

## Key rules

- the root Python package is the release artifact
- `pipx` is the primary public install lane
- `uv` is the supported secondary tool-install lane
- repo-native editable install is a contributor/dev path, not the public onboarding story

## Exact references

- [Release and install strategy](../reference/maintainers/release-and-install-strategy.md)
- [Distribution and database support matrix](../reference/maintainers/distribution-and-database-support-matrix.md)
- [Install and start locally](../reference/cli/install-and-start-local.md)
