from __future__ import annotations

import os
import subprocess
import sys
from importlib import resources
from pathlib import Path

from app.service_managers.base import (
    ManagedServiceStatus,
    ServiceInstallRequest,
    ServiceUninstallRequest,
)

DEFAULT_SERVICE_ENV_TEXT = """# Optional overrides for the AutoClaw user service.
# Add environment-only overrides here if you need them.
"""
SYSTEMD_TEMPLATE_RESOURCE = ("systemd", "autoclaw.service")


def systemd_supported() -> bool:
    return os.name != "nt" and sys.platform.startswith("linux")


def require_systemd_supported() -> None:
    if not systemd_supported():
        raise RuntimeError(
            "AutoClaw managed service commands currently support Linux systemd --user only"
        )


def systemctl_bin() -> str:
    return os.environ.get("AUTOCLAW_SYSTEMCTL_BIN", "systemctl")


def linux_user_unit_dir() -> Path:
    return Path.home() / ".config" / "systemd" / "user"


def service_unit_name(name: str) -> str:
    return name if name.endswith(".service") else f"{name}.service"


def run_systemctl(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [systemctl_bin(), "--user", *args],
        check=check,
        capture_output=True,
        text=True,
    )


def render_systemd_service_unit(
    *,
    python_bin: Path,
    config_path: Path,
    data_dir: Path,
    env_file: Path,
) -> str:
    template_path = resources.files("app.resources").joinpath(*SYSTEMD_TEMPLATE_RESOURCE)
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
    unit_name = service_unit_name(service_name)
    result = run_systemctl(
        "show",
        unit_name,
        "--property=LoadState,UnitFileState,ActiveState,SubState,FragmentPath",
        check=False,
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
        installed=installed,
        enabled=enabled,
        running=running,
        healthy=running,
        fragment_path=fragment_path,
        active_state=active_state,
        sub_state=sub_state,
    )


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
        require_systemd_supported()
        unit_dir = request.unit_dir or linux_user_unit_dir()
        unit_path = unit_dir / service_unit_name(request.service_name)
        unit_dir.mkdir(parents=True, exist_ok=True)
        request.env_file.parent.mkdir(parents=True, exist_ok=True)
        if request.force or not request.env_file.exists():
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
        run_systemctl("daemon-reload")
        run_systemctl("enable", service_unit_name(request.service_name))
        if not request.no_start:
            run_systemctl("restart", service_unit_name(request.service_name))

    def uninstall(self, request: ServiceUninstallRequest) -> None:
        require_systemd_supported()
        unit_dir = request.unit_dir or linux_user_unit_dir()
        unit_path = unit_dir / service_unit_name(request.service_name)
        run_systemctl("disable", "--now", service_unit_name(request.service_name), check=False)
        unit_path.unlink(missing_ok=True)
        if request.remove_env_file:
            request.env_file.unlink(missing_ok=True)
        run_systemctl("daemon-reload")

    def start(self, service_name: str) -> ManagedServiceStatus:
        require_systemd_supported()
        run_systemctl("start", service_unit_name(service_name))
        return read_systemd_status(service_name)

    def stop(self, service_name: str) -> ManagedServiceStatus:
        require_systemd_supported()
        run_systemctl("stop", service_unit_name(service_name))
        return read_systemd_status(service_name)

    def restart(self, service_name: str) -> ManagedServiceStatus:
        require_systemd_supported()
        run_systemctl("restart", service_unit_name(service_name))
        return read_systemd_status(service_name)

    def status(self, service_name: str) -> ManagedServiceStatus:
        require_systemd_supported()
        return read_systemd_status(service_name)


__all__ = [
    "DEFAULT_SERVICE_ENV_TEXT",
    "SystemdUserServiceManager",
    "linux_user_unit_dir",
    "read_systemd_status",
    "render_systemd_service_unit",
    "require_systemd_supported",
    "run_systemctl",
    "service_unit_name",
    "systemctl_bin",
    "systemd_supported",
]
