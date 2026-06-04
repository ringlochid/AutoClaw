from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from autoclaw.config import OpenClawSettings, RuntimeSettings
from autoclaw.runtime.openclaw.host_setup import (
    AUTOCLAW_OPERATOR_AGENT_ID,
    AUTOCLAW_WORKER_AGENT_ID,
)


def settings_to_config_text(
    *,
    data_dir: Path,
    database_url: str,
    host: str,
    port: int,
    log_level: str,
    api_key: str,
    internal_api_key: str,
) -> str:
    payload: dict[str, dict[str, Any]] = {
        "paths": {
            "data_dir": data_dir,
        },
        "database": {
            "url": database_url,
            "echo": False,
        },
        "server": {
            "host": host,
            "port": port,
            "console_origins": [
                "http://127.0.0.1:5173",
                "http://localhost:5173",
                "http://127.0.0.1:4173",
                "http://localhost:4173",
            ],
        },
        "logging": {
            "level": log_level,
        },
        "security": {
            "api_key": api_key,
            "internal_api_key": internal_api_key,
        },
        "openclaw": {
            "base_url": OpenClawSettings().base_url,
            "agent_id": AUTOCLAW_WORKER_AGENT_ID,
            "operator_agent_id": AUTOCLAW_OPERATOR_AGENT_ID,
            "timeout_ms": OpenClawSettings().timeout_ms,
        },
        "runtime": RuntimeSettings().model_dump(mode="json"),
    }
    return _config_sections_to_text(payload)


def update_config_sections(
    config_path: Path,
    *,
    section_updates: dict[str, dict[str, Any]],
) -> None:
    import tomllib

    if config_path.is_file():
        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    else:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    for section, values in section_updates.items():
        existing = payload.get(section)
        next_values = dict(existing) if isinstance(existing, dict) else {}
        for key, value in values.items():
            if value is None or value == "":
                next_values.pop(key, None)
            else:
                next_values[key] = value
        if next_values:
            payload[section] = next_values
        else:
            payload.pop(section, None)
    config_path.write_text(
        _config_sections_to_text(
            {key: value for key, value in payload.items() if isinstance(value, dict)}
        ),
        encoding="utf-8",
    )


def _config_sections_to_text(payload: dict[str, dict[str, Any]]) -> str:
    section_order = (
        "paths",
        "database",
        "server",
        "logging",
        "security",
        "openclaw",
        "runtime",
    )
    ordered_sections = [
        section for section in section_order if isinstance(payload.get(section), dict)
    ]
    ordered_sections.extend(
        section
        for section in payload
        if section not in ordered_sections and isinstance(payload[section], dict)
    )

    lines: list[str] = []
    for section in ordered_sections:
        values = payload[section]
        rendered_values = [
            (key, value) for key, value in values.items() if value is not None and value != ""
        ]
        if not rendered_values:
            continue
        lines.append(f"[{section}]")
        for key, value in rendered_values:
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, Path):
        return json.dumps(str(value))
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return json.dumps(str(value))


__all__ = [
    "settings_to_config_text",
    "update_config_sections",
]
