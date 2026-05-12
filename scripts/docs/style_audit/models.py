from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AuditSettings:
    root: Path
    apps_api_root: Path
    scan_roots: tuple[Path, ...]
    excluded_paths: frozenset[Path]
    file_split_review_threshold: int
    file_no_growth_threshold: int
    function_size_threshold: int


@dataclass(frozen=True)
class HelperDefinition:
    path: Path
    name: str
    line: int
    end_line: int
    non_comment_lines: int


@dataclass(frozen=True)
class FunctionSizeViolation:
    path: Path
    name: str
    line: int
    non_comment_lines: int


@dataclass(frozen=True)
class ReferenceLocation:
    path: Path
    line: int
    kind: str


@dataclass(frozen=True)
class ModuleRecord:
    path: Path
    module_name: str | None
    tree: ast.Module
    lines: tuple[str, ...]


@dataclass(frozen=True)
class AuditResults:
    modules: tuple[ModuleRecord, ...]
    cross_module_findings: tuple[tuple[HelperDefinition, ReferenceLocation], ...]
    zero_reference_helpers: tuple[HelperDefinition, ...]
    file_line_violations: tuple[tuple[Path, int], ...]
    function_size_violations: tuple[FunctionSizeViolation, ...]

    @property
    def has_findings(self) -> bool:
        return any(
            (
                self.cross_module_findings,
                self.zero_reference_helpers,
                self.file_line_violations,
                self.function_size_violations,
            )
        )
