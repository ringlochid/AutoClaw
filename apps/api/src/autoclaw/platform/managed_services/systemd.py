from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from autoclaw.platform.managed_services.resources import get_systemd_service_template

from .contracts import (
    ManagedServiceStatus,
    ServiceInstallRequest,
    ServiceUninstallRequest,
)

DEFAULT_SERVICE_ENV_TEXT = """# Optional overrides for the AutoClaw user service.
# Add environment-only overrides here if you need them.
"""
SYSTEMD_TEMPLATE_RESOURCE = ("systemd", "autoclaw.service")


class SystemdUserServiceManager:
    def render_systemd_service_unit(
        self,
        *,
        python_bin: Path,
        config_path: Path,
        data_dir: Path,
        env_file: Path,
    ) -> str:
        return render_systemd_service_unit(
            python_bin=python_bin,
            config_path=config_path,
            data_dir=data_dir,
            env_file=env_file,
        )

    def install(self, request: ServiceInstallRequest) -> None:
        require_supported_systemd()
        unit_dir = request.unit_dir or get_linux_user_unit_dir()
        unit_path = unit_dir / build_service_unit_name(request.service_name)
        unit_dir.mkdir(parents=True, exist_ok=True)
        request.env_file.parent.mkdir(parents=True, exist_ok=True)
        if request.should_force or not request.env_file.exists():
            request.env_file.write_text(DEFAULT_SERVICE_ENV_TEXT, encoding="utf-8")
        unit_path.write_text(
            render_systemd_service_unit(
                python_bin=Path(sys.executable),
                config_path=request.config_path,
                data_dir=request.data_dir,
                env_file=request.env_file,
            ),
            encoding="utf-8",
        )
        execute_systemctl("daemon-reload")
        execute_systemctl("enable", build_service_unit_name(request.service_name))
        if not request.should_skip_start:
            execute_systemctl("restart", build_service_unit_name(request.service_name))

    def uninstall(self, request: ServiceUninstallRequest) -> None:
        require_supported_systemd()
        unit_dir = request.unit_dir or get_linux_user_unit_dir()
        unit_path = unit_dir / build_service_unit_name(request.service_name)
        execute_systemctl(
            "disable",
            "--now",
            build_service_unit_name(request.service_name),
            should_check=False,
        )
        unit_path.unlink(missing_ok=True)
        if request.should_remove_env_file:
            request.env_file.unlink(missing_ok=True)
        execute_systemctl("daemon-reload")

    def start(self, service_name: str) -> ManagedServiceStatus:
        require_supported_systemd()
        execute_systemctl("start", build_service_unit_name(service_name))
        return read_systemd_status(service_name)

    def stop(self, service_name: str) -> ManagedServiceStatus:
        require_supported_systemd()
        execute_systemctl("stop", build_service_unit_name(service_name))
        return read_systemd_status(service_name)

    def restart(self, service_name: str) -> ManagedServiceStatus:
        require_supported_systemd()
        execute_systemctl("restart", build_service_unit_name(service_name))
        return read_systemd_status(service_name)

    def status(self, service_name: str) -> ManagedServiceStatus:
        require_supported_systemd()
        return read_systemd_status(service_name)


def render_systemd_service_unit(
    *,
    python_bin: Path,
    config_path: Path,
    data_dir: Path,
    env_file: Path,
) -> str:
    template_path = get_systemd_service_template()
    rendered = template_path.read_text(encoding="utf-8")
    replacements = {
        "@AUTOCLAW_PYTHON@": str(python_bin),
        "@AUTOCLAW_CONFIG@": str(config_path),
        "@AUTOCLAW_DATA_DIR@": str(data_dir),
        "@AUTOCLAW_ENV_FILE@": str(env_file),
    }
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


def read_systemd_status(service_name: str) -> ManagedServiceStatus:
    unit_name = build_service_unit_name(service_name)
    result = execute_systemctl(
        "show",
        unit_name,
        "--property=LoadState,UnitFileState,ActiveState,SubState,FragmentPath",
        should_check=False,
    )
    values: dict[str, str] = {}
    for line in result.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    load_state = values.get("LoadState")
    unit_file_state = values.get("UnitFileState")
    active_state = values.get("ActiveState")
    sub_state = values.get("SubState")
    fragment_path = values.get("FragmentPath") or None
    installed = load_state not in {None, "", "not-found"}
    enabled = unit_file_state in {"enabled", "linked", "static", "generated"}
    running = active_state == "active"
    return ManagedServiceStatus(
        manager="systemd-user",
        service_name=unit_name,
        is_installed=installed,
        is_enabled=enabled,
        is_running=running,
        is_healthy=running,
        fragment_path=fragment_path,
        active_state=active_state,
        sub_state=sub_state,
    )


def require_supported_systemd() -> None:
    if not is_systemd_supported():
        raise RuntimeError(
            "AutoClaw managed service commands currently support Linux systemd --user only"
        )


def execute_systemctl(
    *args: str,
    should_check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [resolve_systemctl_bin(), "--user", *args],
        check=should_check,
        capture_output=True,
        text=True,
    )


def get_linux_user_unit_dir() -> Path:
    return Path.home() / ".config" / "systemd" / "user"


def build_service_unit_name(name: str) -> str:
    return name if name.endswith(".service") else f"{name}.service"


def resolve_systemctl_bin() -> str:
    return os.environ.get("AUTOCLAW_SYSTEMCTL_BIN", "systemctl")


def is_systemd_supported() -> bool:
    return os.name != "nt" and sys.platform.startswith("linux")


__all__ = [
    "DEFAULT_SERVICE_ENV_TEXT",
    "SystemdUserServiceManager",
    "build_service_unit_name",
    "execute_systemctl",
    "get_linux_user_unit_dir",
    "is_systemd_supported",
    "read_systemd_status",
    "render_systemd_service_unit",
    "require_supported_systemd",
    "resolve_systemctl_bin",
]
