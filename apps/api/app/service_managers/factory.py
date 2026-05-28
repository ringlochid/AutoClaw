from __future__ import annotations

import os
import sys

from app.service_managers.base import ManagedServiceManager
from app.service_managers.launchd import LaunchdUserServiceManager
from app.service_managers.schtasks import ScheduledTaskServiceManager
from app.service_managers.systemd import SystemdUserServiceManager


def get_managed_service_manager() -> ManagedServiceManager:
    if os.name == "nt":
        return ScheduledTaskServiceManager()
    if sys.platform == "darwin":
        return LaunchdUserServiceManager()
    return SystemdUserServiceManager()


__all__ = ["get_managed_service_manager"]
