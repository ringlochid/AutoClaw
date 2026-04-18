from __future__ import annotations

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
