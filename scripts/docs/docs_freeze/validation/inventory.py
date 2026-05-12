from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..content.rules import REQUIRED_MARKERS
from ..paths import ROOT
from ..sections import (
    FormatterViolation,
    api_appendix_headings,
    compatibility_status_hits,
    deleted_filename_hits,
    legacy_heading_hits,
    markdown_formatter_violations,
    unreferenced_redesign_paths,
)


@dataclass(frozen=True)
class DocsFreezeInventory:
    legacy_hits: dict[Path, list[int]]
    compatibility_hits: dict[Path, list[int]]
    deleted_hits: dict[str, list[tuple[Path, list[int]]]]
    formatter_violations: list[FormatterViolation]
    unreferenced_paths: list[Path]


def build_inventory() -> DocsFreezeInventory:
    return DocsFreezeInventory(
        legacy_hits=legacy_heading_hits(),
        compatibility_hits=compatibility_status_hits(),
        deleted_hits=deleted_filename_hits(),
        formatter_violations=markdown_formatter_violations(),
        unreferenced_paths=unreferenced_redesign_paths(),
    )


def print_inventory(*, inventory: DocsFreezeInventory | None = None) -> None:
    inventory = build_inventory() if inventory is None else inventory

    print("API appendix headings:")
    for heading in api_appendix_headings():
        print(f"- {heading}")

    print("")
    print_required_marker_coverage()
    print("")
    print_execution_linked_redesign_coverage(inventory.unreferenced_paths)
    print("")
    print_path_hits("Legacy filename headings in live redesign docs:", inventory.legacy_hits)
    print("")
    print_path_hits("Compatibility statuses in live redesign docs:", inventory.compatibility_hits)
    print("")
    print_deleted_router_hits(inventory.deleted_hits)
    print("")
    print_formatter_violations(inventory.formatter_violations)


def print_required_marker_coverage() -> None:
    print("Required marker coverage:")
    for path, markers in REQUIRED_MARKERS.items():
        rel = path.relative_to(ROOT)
        if not path.exists():
            print(f"- {rel}: missing file")
            continue
        text = path.read_text(encoding="utf-8")
        missing = [marker for marker in markers if marker not in text]
        if missing:
            print(f"- {rel}: missing {len(missing)} marker(s)")
            for marker in missing:
                print(f"  - {marker}")
        else:
            print(f"- {rel}: ok ({len(markers)} marker(s))")


def print_execution_linked_redesign_coverage(unreferenced_paths: list[Path]) -> None:
    print("Execution-linked redesign coverage:")
    if not unreferenced_paths:
        print("- all redesign markdown/yaml files are linked from AGENTS.md or docs/execution/")
        return
    for path in unreferenced_paths:
        print(f"- missing execution link: {path.relative_to(ROOT)}")


def print_path_hits(title: str, hits: dict[Path, list[int]]) -> None:
    print(title)
    if not hits:
        print("- none")
        return
    for path, line_numbers in sorted(hits.items()):
        joined = ", ".join(str(n) for n in line_numbers)
        print(f"- {path.relative_to(ROOT)}: lines {joined}")


def print_deleted_router_hits(deleted_hits: dict[str, list[tuple[Path, list[int]]]]) -> None:
    print("Deleted router filename references in maintained docs:")
    if not deleted_hits:
        print("- none")
        return
    for deleted_name in sorted(deleted_hits):
        print(f"- {deleted_name}")
        for path, line_numbers in deleted_hits[deleted_name]:
            joined = ", ".join(str(n) for n in line_numbers)
            print(f"  - {path.relative_to(ROOT)}: lines {joined}")


def print_formatter_violations(formatter_violations: list[FormatterViolation]) -> None:
    print("Front-door markdown unwrap formatter violations:")
    if not formatter_violations:
        print("- none")
        return
    for violation in formatter_violations:
        print(f"- {violation.path.relative_to(ROOT)}:{violation.line}: {violation.reason}")
