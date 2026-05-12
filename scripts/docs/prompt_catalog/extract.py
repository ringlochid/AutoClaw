from __future__ import annotations

import re
from pathlib import Path


def extract_markdown_section(text: str, heading: str) -> str | None:
    lines = text.splitlines()
    capture = False
    in_code_block = False
    collected: list[str] = []
    for line in lines:
        if line.strip() == heading:
            capture = True
            continue
        if capture and line.strip().startswith("```"):
            in_code_block = not in_code_block
        if capture and line.startswith("## ") and not in_code_block:
            break
        if capture:
            collected.append(line)
    if not capture:
        return None
    return "\n".join(collected)


def extract_first_text_code_block(section: str) -> str | None:
    lines = section.splitlines()
    in_code_block = False
    collected: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not in_code_block:
            if stripped == "```text":
                in_code_block = True
            continue
        if stripped == "```":
            return "\n".join(collected).strip("\n")
        collected.append(line)
    return None


def extract_exact_block_text_from_mirror_doc(path: Path, block_id: str) -> str:
    heading = f"## `{block_id}`"
    mirror_text = path.read_bytes().decode("utf-8")
    if heading not in mirror_text:
        raise ValueError(f"missing exact block heading {block_id} in {path}")
    code_block_match = re.search(
        r"```text\r?\n(.*?)^```",
        mirror_text.split(heading, maxsplit=1)[1],
        re.MULTILINE | re.DOTALL,
    )
    if code_block_match is None:
        raise ValueError(f"missing exact block code fence {block_id} in {path}")
    return code_block_match.group(1)


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())
