"""Compatibility shell for the src autoclaw owner."""

from __future__ import annotations

import sys
from importlib import import_module

sys.modules[__name__] = import_module("autoclaw.cli.commands.openclaw.gateway_bootstrap")
