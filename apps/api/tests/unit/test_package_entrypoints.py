from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from app.cli import build_parser as legacy_build_parser
from app.cli import main as legacy_main
from app.main import app as legacy_app
from app.main import create_app as legacy_create_app
from autoclaw import app as packaged_app
from autoclaw import create_app as packaged_create_app
from autoclaw.cli import build_parser, main
from autoclaw.main import app, create_app


def test_autoclaw_cli_aliases_legacy_app_cli() -> None:
    assert main is legacy_main
    assert build_parser is legacy_build_parser


def test_autoclaw_main_aliases_legacy_app_main() -> None:
    assert app is legacy_app
    assert create_app is legacy_create_app
    assert packaged_app is legacy_app
    assert packaged_create_app is legacy_create_app


def test_python_m_autoclaw_cli_invokes_main() -> None:
    package_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(package_root)
        if not existing_pythonpath
        else os.pathsep.join((str(package_root), existing_pythonpath))
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
