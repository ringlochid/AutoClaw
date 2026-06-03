from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import autoclaw as packaged_root
from app.cli import build_parser as legacy_build_parser
from app.cli import main as legacy_main
from app.main import app as legacy_app
from app.main import create_app as legacy_create_app
from autoclaw.cli import build_parser, main
from autoclaw.main import app, create_app
from fastapi import FastAPI


def _route_paths(routes: list[Any]) -> set[str]:
    return {str(route.path) for route in routes if hasattr(route, "path")}


packaged_app = cast(FastAPI, packaged_root.app)
packaged_create_app = cast(Callable[..., FastAPI], packaged_root.create_app)


def test_autoclaw_cli_aliases_legacy_app_cli() -> None:
    assert set(build_parser().commands) == set(legacy_build_parser().commands)
    assert main(["--help"]) == 0
    assert legacy_main(["--help"]) == 0


def test_autoclaw_main_aliases_legacy_app_main() -> None:
    assert app.title == legacy_app.title == packaged_app.title == "AutoClaw API"
    assert _route_paths(app.routes) == _route_paths(legacy_app.routes)
    assert _route_paths(packaged_app.routes) == _route_paths(legacy_app.routes)
    assert _route_paths(create_app(enable_mcp_mounts=False).routes) == _route_paths(
        legacy_create_app(enable_mcp_mounts=False).routes
    )
    assert _route_paths(packaged_create_app(enable_mcp_mounts=False).routes) == _route_paths(
        legacy_create_app(enable_mcp_mounts=False).routes
    )


def test_python_m_autoclaw_cli_invokes_main() -> None:
    package_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        os.pathsep.join((str(package_root / "src"), str(package_root)))
        if not existing_pythonpath
        else os.pathsep.join((str(package_root / "src"), str(package_root), existing_pythonpath))
    )
    result = subprocess.run(
        [sys.executable, "-m", "autoclaw.cli", "--help"],
        cwd=package_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Usage: autoclaw" in result.stdout
