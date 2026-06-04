from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class ManagedServiceStatus:
    manager: str
    service_name: str
    is_installed: bool
    is_enabled: bool
    is_running: bool
    is_healthy: bool | None
    fragment_path: str | None
    active_state: str | None
    sub_state: str | None

    @property
    def installed(self) -> bool:
        return self.is_installed

    @property
    def enabled(self) -> bool:
        return self.is_enabled

    @property
    def running(self) -> bool:
        return self.is_running

    @property
    def healthy(self) -> bool | None:
        return self.is_healthy

    def to_payload(self) -> dict[str, object]:
        return {
            "ok": True,
            "manager": self.manager,
            "service_name": self.service_name,
            "installed": self.is_installed,
            "enabled": self.is_enabled,
            "running": self.is_running,
            "healthy": self.is_healthy,
            "fragment_path": self.fragment_path,
            "active_state": self.active_state,
            "sub_state": self.sub_state,
        }


@dataclass(frozen=True, init=False)
class ServiceInstallRequest:
    config_path: Path
    data_dir: Path
    env_file: Path
    service_name: str
    unit_dir: Path | None
    should_force: bool
    should_skip_start: bool

    def __init__(
        self,
        *,
        config_path: Path,
        data_dir: Path,
        env_file: Path,
        service_name: str,
        unit_dir: Path | None,
        **legacy_options: object,
    ) -> None:
        should_force = _pop_required_boolean_option(legacy_options, "force")
        should_skip_start = _pop_required_boolean_option(legacy_options, "no_start")
        _raise_for_unexpected_options(legacy_options)
        object.__setattr__(self, "config_path", config_path)
        object.__setattr__(self, "data_dir", data_dir)
        object.__setattr__(self, "env_file", env_file)
        object.__setattr__(self, "service_name", service_name)
        object.__setattr__(self, "unit_dir", unit_dir)
        object.__setattr__(self, "should_force", should_force)
        object.__setattr__(self, "should_skip_start", should_skip_start)

    @property
    def force(self) -> bool:
        return self.should_force

    @property
    def no_start(self) -> bool:
        return self.should_skip_start


@dataclass(frozen=True, init=False)
class ServiceUninstallRequest:
    config_path: Path
    env_file: Path
    service_name: str
    unit_dir: Path | None
    should_remove_env_file: bool

    def __init__(
        self,
        *,
        config_path: Path,
        env_file: Path,
        service_name: str,
        unit_dir: Path | None,
        **legacy_options: object,
    ) -> None:
        should_remove_env_file = _pop_required_boolean_option(
            legacy_options,
            "remove_env_file",
        )
        _raise_for_unexpected_options(legacy_options)
        object.__setattr__(self, "config_path", config_path)
        object.__setattr__(self, "env_file", env_file)
        object.__setattr__(self, "service_name", service_name)
        object.__setattr__(self, "unit_dir", unit_dir)
        object.__setattr__(self, "should_remove_env_file", should_remove_env_file)

    @property
    def remove_env_file(self) -> bool:
        return self.should_remove_env_file


class ManagedServiceManager(Protocol):
    def install(self, request: ServiceInstallRequest) -> None: ...

    def uninstall(self, request: ServiceUninstallRequest) -> None: ...

    def start(self, service_name: str) -> ManagedServiceStatus: ...

    def stop(self, service_name: str) -> ManagedServiceStatus: ...

    def restart(self, service_name: str) -> ManagedServiceStatus: ...

    def status(self, service_name: str) -> ManagedServiceStatus: ...


def _pop_required_boolean_option(
    legacy_options: dict[str, object],
    option_name: str,
) -> bool:
    if option_name not in legacy_options:
        raise TypeError(f"missing required keyword argument: {option_name}")

    option_value = legacy_options.pop(option_name)
    if not isinstance(option_value, bool):
        raise TypeError(f"{option_name} must be a bool")
    return option_value


def _raise_for_unexpected_options(legacy_options: dict[str, object]) -> None:
    if not legacy_options:
        return

    unexpected_keys = ", ".join(sorted(legacy_options))
    raise TypeError(f"unexpected keyword arguments: {unexpected_keys}")


__all__ = [
    "ManagedServiceManager",
    "ManagedServiceStatus",
    "ServiceInstallRequest",
    "ServiceUninstallRequest",
]
