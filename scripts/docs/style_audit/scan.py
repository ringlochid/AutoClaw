from __future__ import annotations

import ast
from pathlib import Path

from .models import (
    AuditResults,
    AuditSettings,
    FunctionSizeViolation,
    HelperDefinition,
    ModuleRecord,
    ReferenceLocation,
)


def run_style_audit(settings: AuditSettings) -> AuditResults:
    modules = _load_modules(settings)
    module_name_to_path = {
        module.module_name: module.path for module in modules if module.module_name is not None
    }
    helpers, helpers_by_path = _collect_private_helpers(modules)
    references = _collect_same_module_references(helpers, helpers_by_path, modules)
    cross_module_findings = _collect_cross_module_references(
        helpers_by_path,
        module_name_to_path,
        modules,
        references,
    )
    zero_reference_helpers = tuple(
        sorted(
            (helper for helper_key, helper in helpers.items() if not references[helper_key]),
            key=lambda helper: (helper.path.as_posix(), helper.line, helper.name),
        )
    )
    file_line_violations = tuple(_collect_file_line_violations(modules, settings))
    function_size_violations = tuple(
        _collect_function_size_violations(modules, settings.function_size_threshold)
    )
    return AuditResults(
        modules=tuple(modules),
        cross_module_findings=tuple(cross_module_findings),
        zero_reference_helpers=zero_reference_helpers,
        file_line_violations=file_line_violations,
        function_size_violations=function_size_violations,
    )


def _iter_python_files(settings: AuditSettings) -> list[Path]:
    paths: list[Path] = []
    for root in settings.scan_roots:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if "__pycache__" in path.parts or path in settings.excluded_paths:
                continue
            paths.append(path)
    return sorted(paths)


def _module_name_for_path(path: Path, settings: AuditSettings) -> str | None:
    if path.is_relative_to(settings.apps_api_root):
        return _dotted_module_name(path.relative_to(settings.apps_api_root))

    scripts_docs_root = settings.root / "scripts" / "docs"
    if path.is_relative_to(scripts_docs_root):
        return _dotted_module_name(path.relative_to(scripts_docs_root))
    return None


def _dotted_module_name(relative_path: Path) -> str | None:
    parts = list(relative_path.with_suffix("").parts)
    if not parts:
        return None
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return None
    return ".".join(parts)


def _resolve_module_name(current_module: str | None, module: str | None, level: int) -> str | None:
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


def _count_non_comment_lines(lines: tuple[str, ...], start_line: int, end_line: int) -> int:
    return sum(
        1
        for line in lines[start_line - 1 : end_line]
        if line.strip() and not line.strip().startswith("#")
    )


def _load_modules(settings: AuditSettings) -> list[ModuleRecord]:
    modules: list[ModuleRecord] = []
    for path in _iter_python_files(settings):
        source = path.read_text(encoding="utf-8")
        modules.append(
            ModuleRecord(
                path=path,
                module_name=_module_name_for_path(path, settings),
                tree=ast.parse(source, filename=str(path)),
                lines=tuple(source.splitlines()),
            )
        )
    return modules


def _collect_private_helpers(
    modules: list[ModuleRecord],
) -> tuple[dict[tuple[Path, str], HelperDefinition], dict[Path, dict[str, HelperDefinition]]]:
    helpers: dict[tuple[Path, str], HelperDefinition] = {}
    helpers_by_path: dict[Path, dict[str, HelperDefinition]] = {}
    for module in modules:
        module_helpers: dict[str, HelperDefinition] = {}
        for node in module.tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not node.name.startswith("_") or node.name.startswith("__"):
                continue
            end_line = node.end_lineno or node.lineno
            definition = HelperDefinition(
                path=module.path,
                name=node.name,
                line=node.lineno,
                end_line=end_line,
                non_comment_lines=_count_non_comment_lines(module.lines, node.lineno, end_line),
            )
            helpers[(module.path, node.name)] = definition
            module_helpers[node.name] = definition
        helpers_by_path[module.path] = module_helpers
    return helpers, helpers_by_path


def _collect_function_size_violations(
    modules: list[ModuleRecord],
    function_size_threshold: int,
) -> list[FunctionSizeViolation]:
    violations: list[FunctionSizeViolation] = []
    for module in modules:
        for node in ast.walk(module.tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            end_line = node.end_lineno or node.lineno
            non_comment_lines = _count_non_comment_lines(module.lines, node.lineno, end_line)
            if non_comment_lines <= function_size_threshold:
                continue
            violations.append(
                FunctionSizeViolation(
                    path=module.path,
                    name=node.name,
                    line=node.lineno,
                    non_comment_lines=non_comment_lines,
                )
            )
    return sorted(
        violations,
        key=lambda violation: (
            -violation.non_comment_lines,
            violation.path.as_posix(),
            violation.line,
            violation.name,
        ),
    )


def _collect_same_module_references(
    helpers: dict[tuple[Path, str], HelperDefinition],
    helpers_by_path: dict[Path, dict[str, HelperDefinition]],
    modules: list[ModuleRecord],
) -> dict[tuple[Path, str], list[ReferenceLocation]]:
    references: dict[tuple[Path, str], list[ReferenceLocation]] = {key: [] for key in helpers}
    for module in modules:
        module_helpers = helpers_by_path[module.path]
        if not module_helpers:
            continue
        for node in ast.walk(module.tree):
            if not isinstance(node, ast.Name) or not isinstance(node.ctx, ast.Load):
                continue
            helper = module_helpers.get(node.id)
            if helper is None:
                continue
            references[(module.path, helper.name)].append(
                ReferenceLocation(path=module.path, line=node.lineno, kind="same-module")
            )
    return references


def _collect_cross_module_references(
    helpers_by_path: dict[Path, dict[str, HelperDefinition]],
    module_name_to_path: dict[str, Path],
    modules: list[ModuleRecord],
    references: dict[tuple[Path, str], list[ReferenceLocation]],
) -> list[tuple[HelperDefinition, ReferenceLocation]]:
    findings: list[tuple[HelperDefinition, ReferenceLocation]] = []
    for module in modules:
        module_aliases: dict[str, Path] = {}
        for node in ast.walk(module.tree):
            if isinstance(node, ast.Import):
                _record_import_aliases(node, module.path, module_name_to_path, module_aliases)
                continue
            if isinstance(node, ast.ImportFrom):
                _record_import_from_aliases(
                    node,
                    module,
                    helpers_by_path,
                    module_name_to_path,
                    module_aliases,
                    references,
                    findings,
                )
                continue
            if isinstance(node, ast.Attribute):
                _record_module_attribute_reference(
                    node,
                    module.path,
                    helpers_by_path,
                    module_aliases,
                    references,
                    findings,
                )
    return sorted(
        findings,
        key=lambda finding: (
            finding[0].path.as_posix(),
            finding[0].name,
            finding[1].path.as_posix(),
            finding[1].line,
        ),
    )


def _record_import_aliases(
    node: ast.Import,
    module_path: Path,
    module_name_to_path: dict[str, Path],
    module_aliases: dict[str, Path],
) -> None:
    for alias in node.names:
        target_path = module_name_to_path.get(alias.name)
        if target_path is None or target_path == module_path:
            continue
        alias_name = alias.asname or alias.name.rsplit(".", maxsplit=1)[-1]
        module_aliases[alias_name] = target_path


def _record_import_from_aliases(
    node: ast.ImportFrom,
    module: ModuleRecord,
    helpers_by_path: dict[Path, dict[str, HelperDefinition]],
    module_name_to_path: dict[str, Path],
    module_aliases: dict[str, Path],
    references: dict[tuple[Path, str], list[ReferenceLocation]],
    findings: list[tuple[HelperDefinition, ReferenceLocation]],
) -> None:
    resolved_module = _resolve_module_name(module.module_name, node.module, node.level)
    target_module_path = module_name_to_path.get(resolved_module) if resolved_module else None
    for alias in node.names:
        if alias.name == "*":
            continue
        if alias.name.startswith("_") and not alias.name.startswith("__"):
            _record_direct_private_import(
                alias.name,
                module.path,
                node.lineno,
                target_module_path,
                helpers_by_path,
                references,
                findings,
            )
        if resolved_module is None:
            continue
        submodule_path = module_name_to_path.get(f"{resolved_module}.{alias.name}")
        if submodule_path is None or submodule_path == module.path:
            continue
        module_aliases[alias.asname or alias.name] = submodule_path


def _record_direct_private_import(
    helper_name: str,
    module_path: Path,
    line: int,
    target_module_path: Path | None,
    helpers_by_path: dict[Path, dict[str, HelperDefinition]],
    references: dict[tuple[Path, str], list[ReferenceLocation]],
    findings: list[tuple[HelperDefinition, ReferenceLocation]],
) -> None:
    if target_module_path is None or target_module_path == module_path:
        return
    helper = helpers_by_path.get(target_module_path, {}).get(helper_name)
    if helper is None:
        return
    location = ReferenceLocation(path=module_path, line=line, kind="direct-import")
    references[(helper.path, helper.name)].append(location)
    findings.append((helper, location))


def _record_module_attribute_reference(
    node: ast.Attribute,
    module_path: Path,
    helpers_by_path: dict[Path, dict[str, HelperDefinition]],
    module_aliases: dict[str, Path],
    references: dict[tuple[Path, str], list[ReferenceLocation]],
    findings: list[tuple[HelperDefinition, ReferenceLocation]],
) -> None:
    if not node.attr.startswith("_") or node.attr.startswith("__"):
        return
    if not isinstance(node.value, ast.Name):
        return
    target_module_path = module_aliases.get(node.value.id)
    if target_module_path is None or target_module_path == module_path:
        return
    helper = helpers_by_path.get(target_module_path, {}).get(node.attr)
    if helper is None:
        return
    location = ReferenceLocation(path=module_path, line=node.lineno, kind="module-attribute")
    references[(helper.path, helper.name)].append(location)
    findings.append((helper, location))


def _collect_file_line_violations(
    modules: list[ModuleRecord],
    settings: AuditSettings,
) -> list[tuple[Path, int]]:
    return sorted(
        (
            (module.path, len(module.lines))
            for module in modules
            if len(module.lines) > settings.file_split_review_threshold
        ),
        key=lambda item: (-item[1], item[0].as_posix()),
    )
