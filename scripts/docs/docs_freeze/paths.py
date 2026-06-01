from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCS_PUBLIC_ROOT = ROOT / "docs"
DOCS_INTERNAL_ROOT = ROOT / "docs-internal"
DESIGN_ROOT = DOCS_INTERNAL_ROOT / "design" / "v1"
CURRENT_ROOT = DOCS_INTERNAL_ROOT / "current" / "v1"
EXECUTION_ROOT = DOCS_INTERNAL_ROOT / "execution" / "v1"
ARCHIVE_ROOT = DOCS_INTERNAL_ROOT / "archive"
