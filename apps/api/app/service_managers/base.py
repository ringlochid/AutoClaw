from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ManagedServiceStatus:
    manager: str
    service_name: str
    installed: bool
    enabled: bool
    running: bool
    healthy: bool | None
    fragment_path: str | None
    active_state: str | None
    sub_state: str | None

    def to_payload(self) -> dict[str, object]:
        return {
            "ok": True,
            "manager": self.manager,
            "service_name": self.service_name,
            "installed": self.installed,
            "enabled": self.enabled,
            "running": self.running,
            "healthy": self.healthy,
            "fragment_path": self.fragment_path,
            "active_state": self.active_state,
            "sub_state": self.sub_state,
        }


@dataclass(frozen=True)
class ServiceInstallRequest:
    config_path: Path
    data_dir: Path
    env_file: Path
    service_name: str
    unit_dir: Path | None
    force: bool
    no_start: bool


@dataclass(frozen=True)
class ServiceUninstallRequest:
    config_path: Path
    env_file: Path
    service_name: str
    unit_dir: Path | None
    remove_env_file: bool


class ManagedServiceManager(Protocol):
    def install(self, request: ServiceInstallRequest) -> None: ...

    def uninstall(self, request: ServiceUninstallRequest) -> None: ...

    def start(self, service_name: str) -> ManagedServiceStatus: ...

    def stop(self, service_name: str) -> ManagedServiceStatus: ...

    def restart(self, service_name: str) -> ManagedServiceStatus: ...

    def status(self, service_name: str) -> ManagedServiceStatus: ...


__all__ = [
    "ManagedServiceManager",
    "ManagedServiceStatus",
    "ServiceInstallRequest",
    "ServiceUninstallRequest",
]
