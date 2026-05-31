from __future__ import annotations

import json
from collections.abc import Sequence
from typing import NoReturn

import pytest
from app import cli


def test_main_renders_friendly_unknown_command(capsys: pytest.CaptureFixture[str]) -> None:
    result = cli.main(["definitely-not-a-command"])

    output = capsys.readouterr().out
    assert result == 2
    assert 'AutoClaw does not know the command "definitely-not-a-command".' in output
    assert "Try: autoclaw --help" in output
    assert "Traceback" not in output


def test_main_renders_json_parse_errors(capsys: pytest.CaptureFixture[str]) -> None:
    result = cli.main(["onboard", "--json", "--definitely-not-an-option"])

    payload = json.loads(capsys.readouterr().out)
    assert result == 2
    assert payload["ok"] is False
    assert payload["error"]["kind"] == "unknown_option"
    assert "--definitely-not-an-option" in payload["error"]["message"]


def test_main_hides_traceback_without_debug(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _boom(_args: Sequence[str]) -> NoReturn:
        raise RuntimeError("boom")

    monkeypatch.setattr("app.cli.root.cmd_init", _boom)
    result = cli.main(["init", "--force"])

    output = capsys.readouterr().out
    assert result == 1
    assert "AutoClaw command failed" in output
    assert "Reason: boom" in output
    assert "Traceback" not in output


def test_main_shows_traceback_with_debug(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def _boom(_args: Sequence[str]) -> NoReturn:
        raise RuntimeError("boom")

    monkeypatch.setattr("app.cli.root.cmd_init", _boom)
    result = cli.main(["--debug", "init", "--force"])

    output = capsys.readouterr().out
    assert result == 1
    assert "AutoClaw command failed" in output
    assert "Traceback" in output
