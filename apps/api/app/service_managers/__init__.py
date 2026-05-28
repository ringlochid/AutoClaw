from __future__ import annotations

from app.service_managers.base import (
    ManagedServiceStatus,
    ServiceInstallRequest,
    ServiceUninstallRequest,
)
from app.service_managers.factory import get_managed_service_manager
from app.service_managers.launchd import LaunchdUserServiceManager
from app.service_managers.schtasks import ScheduledTaskServiceManager
from app.service_managers.systemd import SystemdUserServiceManager

__all__ = [
    "LaunchdUserServiceManager",
    "ManagedServiceStatus",
    "ScheduledTaskServiceManager",
    "ServiceInstallRequest",
    "ServiceUninstallRequest",
    "SystemdUserServiceManager",
    "get_managed_service_manager",
]
