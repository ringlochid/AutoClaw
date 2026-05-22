from __future__ import annotations

from pathlib import Path


def set_dispatch_drain_timeout(config_path: Path, *, timeout_seconds: int) -> None:
    config_text = config_path.read_text(encoding="utf-8")
    lines = config_text.splitlines()
    runtime_index = next(
        (index for index, line in enumerate(lines) if line.strip() == "[runtime]"),
        None,
    )
    if runtime_index is None:
        lines.extend(["", "[runtime]", f"dispatch_drain_timeout_seconds = {timeout_seconds}"])
    else:
        inserted = False
        for index in range(runtime_index + 1, len(lines)):
            line = lines[index].strip()
            if not line:
                break
            if line.startswith("[") and line.endswith("]"):
                break
            if line.startswith("dispatch_drain_timeout_seconds"):
                lines[index] = f"dispatch_drain_timeout_seconds = {timeout_seconds}"
                inserted = True
                break
        if not inserted:
            lines.insert(runtime_index + 1, f"dispatch_drain_timeout_seconds = {timeout_seconds}")
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
