from __future__ import annotations

import asyncio
import tomllib
from pathlib import Path

import pytest
from autoclaw.definitions.contracts.workflow import ProviderKind
from autoclaw.interfaces.cli import root as cli_root
from autoclaw.interfaces.cli.bootstrap.config import settings_to_config_text
from autoclaw.interfaces.cli.commands import guided_setup
from autoclaw.interfaces.cli.main import build_parser
from autoclaw.interfaces.cli.providers.contracts import (
    ProviderCheckOutcome,
    ProviderCheckSnapshot,
    ProviderIdentityOutcome,
    ProviderIdentitySnapshot,
)
from autoclaw.persistence.session import dispose_db_engine
from autoclaw.runtime.providers import ProviderCheckAxisStatus
from click.testing import CliRunner


def test_guided_flow_requires_tty_and_explicit_human_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class TerminalStream:
        def isatty(self) -> bool:
            return True

    terminal = TerminalStream()
    monkeypatch.setattr(guided_setup.sys, "stdin", terminal)
    monkeypatch.setattr(guided_setup.sys, "stdout", terminal)

    assert guided_setup.should_run_guided_flow(
        is_non_interactive=False,
        is_json_output=False,
    )
    assert not guided_setup.should_run_guided_flow(
        is_non_interactive=True,
        is_json_output=False,
    )
    assert not guided_setup.should_run_guided_flow(
        is_non_interactive=False,
        is_json_output=True,
    )


def test_guided_init_confirms_recommended_local_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.toml"
    data_dir = tmp_path / "data"
    monkeypatch.setattr(cli_root, "should_run_guided_flow", lambda **_kwargs: True)

    result = CliRunner().invoke(
        build_parser(),
        [
            "init",
            "--config",
            str(config_path),
            "--data-dir",
            str(data_dir),
        ],
        input="y\n",
    )

    assert result.exit_code == 0, result.output
    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert payload["paths"]["data_dir"] == str(data_dir)
    assert data_dir.joinpath("autoclaw.persistence").is_file()
    assert "Use these recommended local settings?" in result.output
    assert "Next: autoclaw setup" in result.output


def test_guided_init_rerun_keeps_config_and_verifies_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.toml"
    data_dir = tmp_path / "data"
    config_path.write_text(
        settings_to_config_text(
            data_dir=data_dir,
            database_url=f"sqlite+aiosqlite:///{data_dir / 'autoclaw.persistence'}",
            host="127.0.0.1",
            port=18125,
            log_level="WARNING",
        )
        + '\n[codex]\nenabled = true\n\n[runtime]\ndefault_provider = "codex"\n',
        encoding="utf-8",
    )
    previous_config = config_path.read_bytes()
    monkeypatch.setattr(cli_root, "should_run_guided_flow", lambda **_kwargs: True)

    try:
        result = CliRunner().invoke(
            build_parser(),
            ["init", "--config", str(config_path)],
            input="\n",
        )
    finally:
        asyncio.run(dispose_db_engine())

    assert result.exit_code == 0, result.output
    assert config_path.read_bytes() == previous_config
    assert data_dir.joinpath("autoclaw.persistence").is_file()
    assert "Keep and verify" in result.output


def test_guided_init_replacement_requires_final_confirmation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = write_local_config(tmp_path)
    with config_path.open("a", encoding="utf-8") as stream:
        stream.write("\n[codex]\nenabled = true\n")
    previous_config = config_path.read_bytes()
    monkeypatch.setattr(cli_root, "should_run_guided_flow", lambda **_kwargs: True)

    result = CliRunner().invoke(
        build_parser(),
        ["init", "--config", str(config_path)],
        input="replace\ny\nn\n",
    )

    assert result.exit_code == 0, result.output
    assert config_path.read_bytes() == previous_config
    assert "Replace the existing local config" in result.output
    assert "Cancelled" in result.output


def test_guided_setup_selects_default_and_offers_codex_login(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = write_local_config(tmp_path)
    checks = iter(
        (
            provider_check(
                ProviderKind.CODEX,
                outcome=ProviderCheckOutcome.AUTHENTICATION_FAILED,
                is_ready=False,
                detail="codex_authentication_required",
                authentication=ProviderCheckAxisStatus.FAILED,
            ),
            provider_check(
                ProviderKind.CODEX,
                outcome=ProviderCheckOutcome.READY,
                is_ready=True,
                detail="codex_available",
            ),
        )
    )
    identity_calls: list[ProviderKind] = []
    monkeypatch.setattr(cli_root, "should_run_guided_flow", lambda **_kwargs: True)
    monkeypatch.setattr(guided_setup, "collect_provider_check", lambda *_args: next(checks))

    def login(
        provider: ProviderKind, *_args: object, **_kwargs: object
    ) -> ProviderIdentitySnapshot:
        identity_calls.append(provider)
        return ProviderIdentitySnapshot(
            provider=provider,
            action="login",
            outcome=ProviderIdentityOutcome.SUCCEEDED,
            service_identity="tester",
            native_home="/tmp/codex-home",
            detail="native Codex login completed",
        )

    monkeypatch.setattr(guided_setup, "invoke_provider_identity_action", login)

    result = CliRunner().invoke(
        build_parser(),
        ["setup", "--config", str(config_path)],
        input="\n\n\n",
    )

    assert result.exit_code == 0, result.output
    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert payload["codex"]["enabled"] is True
    assert payload["runtime"]["default_provider"] == "codex"
    assert identity_calls == [ProviderKind.CODEX]
    assert "Sign in to Codex now?" in result.output
    assert "codex: ready" in result.output


def test_guided_setup_adds_provider_without_replacing_primary_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = write_local_config(tmp_path)
    checked: list[ProviderKind] = []
    monkeypatch.setattr(cli_root, "should_run_guided_flow", lambda **_kwargs: True)

    def ready_check(_settings: object, provider: ProviderKind) -> ProviderCheckSnapshot:
        checked.append(provider)
        return provider_check(
            provider,
            outcome=ProviderCheckOutcome.READY,
            is_ready=True,
            detail=f"{provider.value}_available",
        )

    monkeypatch.setattr(guided_setup, "collect_provider_check", ready_check)

    result = CliRunner().invoke(
        build_parser(),
        ["setup", "--config", str(config_path), "--provider", "claude"],
        input="y\nopenclaw\nn\n",
    )

    assert result.exit_code == 0, result.output
    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert payload["runtime"]["default_provider"] == "claude"
    assert payload["claude"]["enabled"] is True
    assert payload["openclaw"]["enabled"] is True
    assert checked == [ProviderKind.CLAUDE, ProviderKind.OPENCLAW]
    assert "OpenClaw is experimental" in result.output


def test_guided_setup_explicit_primary_choice_replaces_existing_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = write_local_config(tmp_path)
    with config_path.open("a", encoding="utf-8") as stream:
        stream.write('\n[codex]\nenabled = true\n\n[runtime]\ndefault_provider = "codex"\n')
    monkeypatch.setattr(cli_root, "should_run_guided_flow", lambda **_kwargs: True)
    monkeypatch.setattr(
        guided_setup,
        "collect_provider_check",
        lambda _settings, provider: provider_check(
            provider,
            outcome=ProviderCheckOutcome.READY,
            is_ready=True,
            detail=f"{provider.value}_available",
        ),
    )

    result = CliRunner().invoke(
        build_parser(),
        ["setup", "--config", str(config_path)],
        input="claude\nn\n",
    )

    assert result.exit_code == 0, result.output
    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert payload["codex"]["enabled"] is True
    assert payload["claude"]["enabled"] is True
    assert payload["runtime"]["default_provider"] == "claude"


def test_guided_setup_discloses_environment_default_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = write_local_config(tmp_path)
    with config_path.open("a", encoding="utf-8") as stream:
        stream.write('\n[codex]\nenabled = true\n\n[runtime]\ndefault_provider = "codex"\n')
    monkeypatch.setattr(cli_root, "should_run_guided_flow", lambda **_kwargs: True)
    monkeypatch.setattr(
        guided_setup,
        "collect_provider_check",
        lambda _settings, provider: provider_check(
            provider,
            outcome=ProviderCheckOutcome.READY,
            is_ready=True,
            detail=f"{provider.value}_available",
        ),
    )

    result = CliRunner().invoke(
        build_parser(),
        ["setup", "--config", str(config_path), "--provider", "codex"],
        input="n\n",
        env={
            "AUTOCLAW_CLAUDE__ENABLED": "true",
            "AUTOCLAW_RUNTIME__DEFAULT_PROVIDER": "claude",
        },
    )

    assert result.exit_code == 0, result.output
    assert "Current default: codex" in result.output
    assert "Effective default: claude (environment override)" in result.output
    assert "Effective environment-overridden default: claude" in result.output


def test_setup_non_interactive_keeps_the_deterministic_command_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = write_local_config(tmp_path)
    monkeypatch.setattr(
        cli_root,
        "guide_provider_setup",
        lambda _args: pytest.fail("non-interactive setup entered the guided flow"),
    )

    result = CliRunner().invoke(
        build_parser(),
        [
            "setup",
            "--config",
            str(config_path),
            "--provider",
            "codex",
            "--non-interactive",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert payload["runtime"]["default_provider"] == "codex"


def write_local_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "config.toml"
    data_dir = tmp_path / "data"
    config_path.write_text(
        settings_to_config_text(
            data_dir=data_dir,
            database_url=f"sqlite+aiosqlite:///{data_dir / 'autoclaw.persistence'}",
            host="127.0.0.1",
            port=18125,
            log_level="WARNING",
        ),
        encoding="utf-8",
    )
    return config_path


def provider_check(
    provider: ProviderKind,
    *,
    outcome: ProviderCheckOutcome,
    is_ready: bool,
    detail: str,
    authentication: ProviderCheckAxisStatus = ProviderCheckAxisStatus.NOT_CHECKED,
) -> ProviderCheckSnapshot:
    return ProviderCheckSnapshot(
        kind=provider,
        outcome=outcome,
        is_ready=is_ready,
        service_identity="tester",
        native_home=f"/tmp/{provider.value}-home",
        authentication=authentication,
        reachability=ProviderCheckAxisStatus.NOT_CHECKED,
        detail=detail,
    )
