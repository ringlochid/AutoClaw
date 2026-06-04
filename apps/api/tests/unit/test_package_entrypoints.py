from __future__ import annotations

import importlib
import os
import subprocess
import sys
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import autoclaw
from autoclaw.cli import build_parser, main
from autoclaw.main import app, create_app
from fastapi import FastAPI


def _route_paths(routes: list[Any]) -> set[str]:
    return {str(route.path) for route in routes if hasattr(route, "path")}


packaged_app = cast(FastAPI, autoclaw.app)
packaged_create_app = cast(Callable[..., FastAPI], autoclaw.create_app)


def _load_setuptools_configuration() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[4]
    with (repo_root / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)
    tool_config = cast(dict[str, Any], pyproject["tool"])
    return cast(dict[str, Any], tool_config["setuptools"])


def _load_project_configuration() -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[4]
    with (repo_root / "pyproject.toml").open("rb") as handle:
        pyproject = tomllib.load(handle)
    return cast(dict[str, Any], pyproject["project"])


def test_autoclaw_package_uses_src_modules_only() -> None:
    package_root = Path(__file__).resolve().parents[2]
    src_root = package_root / "src" / "autoclaw"
    packaged_cli = importlib.import_module("autoclaw.cli")
    packaged_main_module = importlib.import_module("autoclaw.main")
    packaged_openclaw = importlib.import_module("autoclaw.openclaw")

    assert autoclaw.__file__ is not None
    assert Path(autoclaw.__file__).resolve() == src_root / "__init__.py"
    assert list(autoclaw.__path__) == [str(src_root)]
    assert packaged_cli.__file__ is not None
    assert Path(packaged_cli.__file__).resolve() == src_root / "cli" / "__init__.py"
    assert packaged_main_module.__file__ is not None
    assert Path(packaged_main_module.__file__).resolve() == src_root / "main.py"
    assert packaged_openclaw.__file__ is not None
    assert Path(packaged_openclaw.__file__).resolve() == src_root / "openclaw" / "__init__.py"


def test_test_only_app_compat_routes_to_canonical_src_modules() -> None:
    package_root = Path(__file__).resolve().parents[2]
    src_root = package_root / "src" / "autoclaw"
    compat_root = package_root / "tests" / "compat" / "app"

    test_compat_app = importlib.import_module("app")
    compat_main_module = importlib.import_module("app.main")
    compat_cli_module = importlib.import_module("app.cli")
    compat_openclaw = importlib.import_module("app.openclaw")
    compat_runtime_contracts = importlib.import_module("app.runtime.contracts")
    canonical_runtime_contracts = importlib.import_module("autoclaw.schemas.runtime.contracts")

    assert test_compat_app.__file__ is not None
    assert Path(test_compat_app.__file__).resolve() == compat_root / "__init__.py"
    assert list(test_compat_app.__path__) == [str(compat_root), str(src_root)]
    assert compat_main_module.__file__ is not None
    assert Path(compat_main_module.__file__).resolve() == src_root / "main.py"
    assert compat_cli_module.__file__ is not None
    assert Path(compat_cli_module.__file__).resolve() == src_root / "cli" / "__init__.py"
    assert compat_openclaw.__file__ is not None
    assert Path(compat_openclaw.__file__).resolve() == src_root / "openclaw" / "__init__.py"
    assert compat_runtime_contracts.__file__ is not None
    assert Path(compat_runtime_contracts.__file__).resolve() == (
        compat_root / "runtime" / "contracts.py"
    )
    assert (
        compat_runtime_contracts.FlowStatus.__members__
        == canonical_runtime_contracts.FlowStatus.__members__
    )


def test_test_only_app_compat_matches_canonical_cli_and_main() -> None:
    compat_cli = importlib.import_module("app.cli")
    compat_main_module = importlib.import_module("app.main")

    project_config = _load_project_configuration()
    project_version = cast(str, project_config["version"])

    assert set(build_parser().commands) == set(compat_cli.build_parser().commands)
    assert main(["--help"]) == 0
    assert compat_cli.main(["--help"]) == 0
    assert app.title == compat_main_module.app.title == packaged_app.title == "AutoClaw API"
    assert app.version == compat_main_module.app.version == packaged_app.version == project_version
    assert _route_paths(create_app(enable_mcp_mounts=False).routes) == _route_paths(
        compat_main_module.create_app(enable_mcp_mounts=False).routes
    )
    assert _route_paths(packaged_create_app(enable_mcp_mounts=False).routes) == _route_paths(
        compat_main_module.create_app(enable_mcp_mounts=False).routes
    )


def test_pyproject_ships_canonical_packages_only() -> None:
    setuptools_config = _load_setuptools_configuration()
    package_dir = cast(dict[str, str], setuptools_config["package-dir"])
    packages = cast(list[str], setuptools_config["packages"])
    package_data = cast(dict[str, list[str]], setuptools_config["package-data"])

    assert package_dir == {"": "apps/api/src"}
    assert all(package != "app" and not package.startswith("app.") for package in packages)
    assert "autoclaw.openclaw" in packages
    assert "autoclaw.openclaw.node_mcp" in packages
    assert "autoclaw.openclaw.operator_mcp" in packages
    assert "autoclaw" in package_data
    assert "app" not in package_data


def test_python_m_autoclaw_invokes_main() -> None:
    package_root = Path(__file__).resolve().parents[2]
    repo_root = package_root.parent.parent
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(package_root / "src")
        if not existing_pythonpath
        else os.pathsep.join((str(package_root / "src"), existing_pythonpath))
    )
    result = subprocess.run(
        [sys.executable, "-m", "autoclaw", "--help"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Usage: autoclaw" in result.stdout


def test_python_m_autoclaw_cli_invokes_main() -> None:
    package_root = Path(__file__).resolve().parents[2]
    repo_root = package_root.parent.parent
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(package_root / "src")
        if not existing_pythonpath
        else os.pathsep.join((str(package_root / "src"), existing_pythonpath))
    )
    result = subprocess.run(
        [sys.executable, "-m", "autoclaw.cli", "--help"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Usage: autoclaw" in result.stdout


def test_fresh_interpreter_can_import_canonical_package_roots() -> None:
    package_root = Path(__file__).resolve().parents[2]
    repo_root = package_root.parent.parent
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(package_root / "src")
        if not existing_pythonpath
        else os.pathsep.join((str(package_root / "src"), existing_pythonpath))
    )
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "from importlib import resources; "
                "import autoclaw.compiler; "
                "import autoclaw.registry; "
                "import autoclaw.platform.managed_services.resources; "
                "import autoclaw.runtime.prompt.assets; "
                "seed_root = resources.files('autoclaw.registry.seed_definitions'); "
                "service_root = resources.files('autoclaw.platform.managed_services.resources'); "
                "prompt_root = resources.files('autoclaw.runtime.prompt.assets'); "
                "assert seed_root.name == 'seed_definitions'; "
                "assert service_root.name == 'resources'; "
                "assert prompt_root.name == 'assets'"
            ),
        ],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        "fresh interpreter canonical import smoke failed\n"
        f"stdout:\n{result.stdout}\n"
        f"stderr:\n{result.stderr}"
    )
