from __future__ import annotations

import ast
from pathlib import Path

from .models import AuditSettings, ModuleRecord


def load_modules(settings: AuditSettings) -> list[ModuleRecord]:
    modules: list[ModuleRecord] = []
    for path in iter_python_files(settings):
        source = path.read_text(encoding="utf-8")
        modules.append(
            ModuleRecord(
                path=path,
                module_name=module_name_for_path(path, settings),
                tree=ast.parse(source, filename=str(path)),
                lines=tuple(source.splitlines()),
            )
        )
    return modules


def iter_python_files(settings: AuditSettings) -> list[Path]:
    paths: list[Path] = []
    for root in settings.scan_roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts or path in settings.excluded_paths:
                continue
            paths.append(path)
    return sorted(paths)


def module_name_for_path(path: Path, settings: AuditSettings) -> str | None:
    if path.is_relative_to(settings.apps_api_root):
        return dotted_module_name(path.relative_to(settings.apps_api_root))

    scripts_docs_root = settings.root / "scripts" / "docs"
    if path.is_relative_to(scripts_docs_root):
        return dotted_module_name(path.relative_to(scripts_docs_root))
    return None


def dotted_module_name(relative_path: Path) -> str | None:
    parts = list(relative_path.with_suffix("").parts)
    if not parts:
        return None
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return None
    return ".".join(parts)


def resolve_module_name(current_module: str | None, module: str | None, level: int) -> str | None:
    if level == 0:
        return module
    if current_module is None:
        return None
    parts = current_module.split(".")
    if len(parts) < level:
        return None
    anchor = parts[: len(parts) - level]
    if module:
        return ".".join(anchor + module.split("."))
    return ".".join(anchor)


def count_non_comment_lines(lines: tuple[str, ...], start_line: int, end_line: int) -> int:
    return sum(
        1
        for line in lines[start_line - 1 : end_line]
        if line.strip() and not line.strip().startswith("#")
    )
