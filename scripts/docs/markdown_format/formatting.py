from __future__ import annotations

import re
from collections.abc import Sequence

LIST_RE = re.compile(r"^(\s*)([-*+]|\d+[.)])\s+(.*)$")
FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
HR_RE = re.compile(r"^\s{0,3}([-*_])(?:\s*\1){2,}\s*$")
REFERENCE_DEF_RE = re.compile(r"^\[[^\]]+\]:\s+\S+")
SETEXT_RE = re.compile(r"^\s*(?:=+|-{2,})\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?(?:\s*:?-{3,}:?\s*\|)+\s*(?:\s*:?-{3,}:?\s*)?$")


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _leading_spaces(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _is_blank(line: str) -> bool:
    return line.strip() == ""


def _is_heading(line: str) -> bool:
    return line.lstrip().startswith("#")


def _is_blockquote(line: str) -> bool:
    return line.lstrip().startswith(">")


def _is_horizontal_rule(line: str) -> bool:
    return bool(HR_RE.match(line))


def _is_reference_definition(line: str) -> bool:
    return bool(REFERENCE_DEF_RE.match(line.strip()))


def _is_html_blockish(line: str) -> bool:
    stripped = line.lstrip()
    return (
        stripped.startswith("<!--")
        or stripped.startswith("<details")
        or stripped.startswith("</details")
        or stripped.startswith("<summary")
        or stripped.startswith("</summary")
    )


def _is_front_matter_start(lines: Sequence[str], index: int) -> bool:
    return index == 0 and lines[index].strip() == "---"


def _is_setext_underline(line: str) -> bool:
    return bool(SETEXT_RE.match(line.strip()))


def _is_setext_heading(lines: Sequence[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    line = lines[index]
    if _is_blank(line):
        return False
    if _is_heading(line) or _is_blockquote(line) or _is_horizontal_rule(line):
        return False
    return _is_setext_underline(lines[index + 1])


def _is_table_line(lines: Sequence[str], index: int) -> bool:
    line = lines[index]
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("|"):
        return True
    if "|" not in stripped:
        return False
    prev_line = lines[index - 1].strip() if index > 0 else ""
    next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
    return bool(
        TABLE_SEPARATOR_RE.match(stripped)
        or TABLE_SEPARATOR_RE.match(prev_line)
        or TABLE_SEPARATOR_RE.match(next_line)
    )


def _list_match(line: str) -> re.Match[str] | None:
    return LIST_RE.match(line)


def _is_fence_start(line: str) -> re.Match[str] | None:
    return FENCE_RE.match(line)


def _is_indented_code(line: str) -> bool:
    return line.startswith("\t") or _leading_spaces(line) >= 4


def _has_explicit_linebreak(line: str) -> bool:
    return line.endswith("  ") or line.endswith("\\")


def _is_block_start(lines: Sequence[str], index: int) -> bool:
    line = lines[index]
    if _is_blank(line):
        return True
    if _is_setext_heading(lines, index):
        return True
    if _is_heading(line) or _is_blockquote(line) or _is_horizontal_rule(line):
        return True
    if _is_reference_definition(line) or _is_html_blockish(line):
        return True
    if _is_fence_start(line):
        return True
    if _is_table_line(lines, index):
        return True
    if _list_match(line):
        return True
    if _is_indented_code(line):
        return True
    return False


def _consume_table(lines: Sequence[str], index: int) -> tuple[list[str], int]:
    block: list[str] = []
    cursor = index
    while cursor < len(lines) and _is_table_line(lines, cursor):
        block.append(lines[cursor])
        cursor += 1
    return block, cursor


def _consume_front_matter(lines: Sequence[str], index: int) -> tuple[list[str], int]:
    block = [lines[index]]
    cursor = index + 1
    while cursor < len(lines):
        block.append(lines[cursor])
        if lines[cursor].strip() == "---":
            return block, cursor + 1
        cursor += 1
    return block, cursor


def _consume_fenced_block(
    lines: Sequence[str],
    index: int,
    fence_match: re.Match[str],
) -> tuple[list[str], int]:
    block = [lines[index]]
    cursor = index + 1
    marker = fence_match.group(2)
    fence_char = marker[0]
    fence_len = len(marker)
    close_re = re.compile(rf"^\s*{re.escape(fence_char)}{{{fence_len},}}(?:\s.*)?$")
    while cursor < len(lines):
        block.append(lines[cursor])
        if close_re.match(lines[cursor]):
            return block, cursor + 1
        cursor += 1
    return block, cursor


def _consume_list_item(lines: Sequence[str], index: int, match: re.Match[str]) -> tuple[str, int]:
    indent = match.group(1)
    marker = match.group(2)
    first_text = match.group(3).strip()
    content_indent = len(indent) + len(marker) + 1
    parts: list[str] = [first_text] if first_text else []
    cursor = index + 1

    if _has_explicit_linebreak(lines[index]):
        return lines[index], cursor

    while cursor < len(lines):
        line = lines[cursor]
        if _is_blank(line):
            break
        if _is_setext_heading(lines, cursor):
            break
        if _is_heading(line) or _is_blockquote(line) or _is_horizontal_rule(line):
            break
        if _is_reference_definition(line) or _is_html_blockish(line):
            break
        if _is_fence_start(line) or _is_table_line(lines, cursor):
            break

        nested_match = _list_match(line)
        if nested_match:
            nested_indent = len(nested_match.group(1))
            if nested_indent > len(indent):
                break
            if nested_indent <= len(indent):
                break

        leading_spaces = _leading_spaces(line)
        if line.startswith("\t") or leading_spaces >= content_indent + 4:
            break
        if leading_spaces < len(indent):
            break

        parts.append(line.strip())
        if _has_explicit_linebreak(line):
            cursor += 1
            break
        cursor += 1

    joined = " ".join(part for part in parts if part)
    if joined:
        return f"{indent}{marker} {joined}", cursor
    return lines[index], cursor


def _consume_paragraph(lines: Sequence[str], index: int) -> tuple[str, int]:
    if _has_explicit_linebreak(lines[index]):
        return lines[index], index + 1

    parts: list[str] = [lines[index].strip()]
    cursor = index + 1
    while cursor < len(lines):
        if _is_block_start(lines, cursor):
            break
        line = lines[cursor]
        parts.append(line.strip())
        if _has_explicit_linebreak(line):
            cursor += 1
            break
        cursor += 1

    return " ".join(part for part in parts if part), cursor


def format_markdown_text(text: str) -> str:
    normalized = normalize_text(text)
    had_trailing_newline = normalized.endswith("\n")
    lines = normalized.split("\n")
    if had_trailing_newline and lines and lines[-1] == "":
        lines = lines[:-1]

    output: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if _is_front_matter_start(lines, index):
            block, index = _consume_front_matter(lines, index)
            output.extend(block)
            continue
        if _is_blank(line):
            output.append("")
            index += 1
            continue
        fence_match = _is_fence_start(line)
        if fence_match:
            block, index = _consume_fenced_block(lines, index, fence_match)
            output.extend(block)
            continue
        if _is_setext_heading(lines, index):
            output.append(line)
            output.append(lines[index + 1])
            index += 2
            continue
        if _is_table_line(lines, index):
            block, index = _consume_table(lines, index)
            output.extend(block)
            continue
        if _is_heading(line) or _is_blockquote(line) or _is_horizontal_rule(line):
            output.append(line)
            index += 1
            continue
        if _is_reference_definition(line) or _is_html_blockish(line) or _is_indented_code(line):
            output.append(line)
            index += 1
            continue

        list_match = _list_match(line)
        if list_match:
            formatted_line, index = _consume_list_item(lines, index, list_match)
            output.append(formatted_line)
            continue

        formatted_paragraph, index = _consume_paragraph(lines, index)
        output.append(formatted_paragraph)

    formatted = "\n".join(output)
    if formatted:
        formatted += "\n"
    return formatted
