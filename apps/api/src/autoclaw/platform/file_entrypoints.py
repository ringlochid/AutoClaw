"""Temporary Phase 6 shim for the legacy platform file-entrypoint owner."""

from __future__ import annotations

from app.file_entrypoints import load_yaml_mapping, resolved_input_path

__all__ = ["load_yaml_mapping", "resolved_input_path"]
