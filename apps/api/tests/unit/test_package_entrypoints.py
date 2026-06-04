from __future__ import annotations

import importlib
import os
import subprocess
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
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


@contextmanager
def use_legacy_autoclaw_package_with_src_bridge() -> Iterator[None]:
    package_root = Path(__file__).resolve().parents[2]
    src_root = package_root / "src"
    original_path = list(sys.path)
    original_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "autoclaw" or name.startswith("autoclaw.")
    }

    try:
        sys.path = [
            str(package_root),
            str(src_root),
            *[entry for entry in sys.path if entry not in {str(package_root), str(src_root)}],
        ]
        for name in list(original_modules):
            sys.modules.pop(name, None)
        yield
    finally:
        sys.path = original_path
        for name in list(sys.modules):
            if name == "autoclaw" or name.startswith("autoclaw."):
                sys.modules.pop(name, None)
        sys.modules.update(original_modules)


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


def test_legacy_autoclaw_root_bridges_to_src_subpackages() -> None:
    package_root = Path(__file__).resolve().parents[2]
    src_root = package_root / "src"

    with use_legacy_autoclaw_package_with_src_bridge():
        autoclaw = importlib.import_module("autoclaw")
        autoclaw_db = importlib.import_module("autoclaw.db")
        autoclaw_runtime_schemas = importlib.import_module("autoclaw.schemas.runtime")
        autoclaw_runtime_contracts = importlib.import_module("autoclaw.schemas.runtime.contracts")
        app_runtime_schemas = importlib.import_module("app.schemas.runtime")
        app_runtime_contracts = importlib.import_module("app.schemas.runtime.contracts")

        assert autoclaw.__file__ is not None
        assert Path(autoclaw.__file__).resolve() == package_root / "autoclaw" / "__init__.py"
        assert list(autoclaw.__path__) == [
            str(package_root / "autoclaw"),
            str(src_root / "autoclaw"),
        ]
        assert autoclaw_db.__file__ is not None
        assert Path(autoclaw_db.__file__).resolve() == src_root / "autoclaw" / "db" / "__init__.py"
        assert autoclaw_runtime_schemas.TaskStartRequest is app_runtime_schemas.TaskStartRequest
        assert autoclaw_runtime_contracts.FlowStatus is app_runtime_contracts.FlowStatus


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
