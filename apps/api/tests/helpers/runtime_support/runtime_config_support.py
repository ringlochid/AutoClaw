from __future__ import annotations

from pathlib import Path


def _set_runtime_setting(
    config_path: Path,
    *,
    setting_name: str,
    setting_literal: str,
) -> None:
    config_text = config_path.read_text(encoding="utf-8")
    lines = config_text.splitlines()
    runtime_index = next(
        (index for index, line in enumerate(lines) if line.strip() == "[runtime]"),
        None,
    )
    if runtime_index is None:
        lines.extend(["", "[runtime]", f"{setting_name} = {setting_literal}"])
    else:
        inserted = False
        for index in range(runtime_index + 1, len(lines)):
            line = lines[index].strip()
            if not line:
                break
            if line.startswith("[") and line.endswith("]"):
                break
            if line.startswith(setting_name):
                lines[index] = f"{setting_name} = {setting_literal}"
                inserted = True
                break
        if not inserted:
            lines.insert(runtime_index + 1, f"{setting_name} = {setting_literal}")
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_dispatch_drain_timeout(config_path: Path, *, timeout_seconds: int) -> None:
    _set_runtime_setting(
        config_path,
        setting_name="dispatch_drain_timeout_seconds",
        setting_literal=str(timeout_seconds),
    )


def set_runtime_watchdog_enabled(config_path: Path, *, enabled: bool) -> None:
    _set_runtime_setting(
        config_path,
        setting_name="watchdog_enabled",
        setting_literal="true" if enabled else "false",
    )
