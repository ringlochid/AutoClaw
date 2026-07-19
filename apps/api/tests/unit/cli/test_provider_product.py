from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import tomllib
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from autoclaw.config import Settings
from autoclaw.definitions.contracts.workflow import ProviderKind
from autoclaw.interfaces.cli.commands import providers as provider_commands
from autoclaw.interfaces.cli.main import build_parser
from autoclaw.interfaces.cli.providers import inspection as provider_inspection
from autoclaw.interfaces.cli.providers.configuration import (
    ProviderConfigurationRequest,
    configure_provider,
    set_default_provider,
)
from autoclaw.interfaces.cli.providers.contracts import (
    ProviderConfigurationSnapshot,
    ProviderIdentityOutcome,
)
from autoclaw.interfaces.cli.providers.inspection import invoke_provider_identity_action
from autoclaw.runtime.providers import (
    ProviderCheckAxisStatus,
    ProviderCheckResult,
    ProviderCheckStatus,
)
from click.testing import CliRunner


def test_first_configuration_sets_default_and_later_configuration_preserves_it(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"

    first = configure_provider(
        config_path,
        ProviderConfigurationRequest(provider=ProviderKind.CODEX, model="gpt-5"),
    )
    second = configure_provider(
        config_path,
        ProviderConfigurationRequest(provider=ProviderKind.CLAUDE, effort="high"),
    )

    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert first.default_provider == ProviderKind.CODEX
    assert first.is_default_changed is True
    assert first.model_dump(mode="json")["default_changed"] is True
    assert second.default_provider == ProviderKind.CODEX
    assert second.is_default_changed is False
    assert payload["codex"] == {"enabled": True, "model": "gpt-5"}
    assert payload["claude"] == {"enabled": True, "effort": "high"}
    assert payload["runtime"]["default_provider"] == "codex"


def test_openclaw_is_configurable_and_default_eligible(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    configure_provider(
        config_path,
        ProviderConfigurationRequest(provider=ProviderKind.CODEX),
    )
    configured = configure_provider(
        config_path,
        ProviderConfigurationRequest(
            provider=ProviderKind.OPENCLAW,
            gateway_url="ws://127.0.0.1:18789",
            gateway_profile="user-maintained",
        ),
    )

    changed = set_default_provider(config_path, ProviderKind.OPENCLAW)

    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    assert configured.product_status.value == "experimental"
    assert configured.default_provider == ProviderKind.CODEX
    assert changed.default_provider == ProviderKind.OPENCLAW
    assert changed.is_default_changed is True
    assert payload["runtime"]["default_provider"] == "openclaw"
    assert payload["openclaw"] == {
        "enabled": True,
        "gateway_url": "ws://127.0.0.1:18789",
        "gateway_profile": "user-maintained",
    }


def test_failed_configuration_preserves_previous_bytes_and_default(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    configure_provider(
        config_path,
        ProviderConfigurationRequest(provider=ProviderKind.CODEX),
    )
    previous_bytes = config_path.read_bytes()

    with pytest.raises(ValueError, match="gateway_url"):
        configure_provider(
            config_path,
            ProviderConfigurationRequest(
                provider=ProviderKind.OPENCLAW,
                gateway_url="ws://user:secret@127.0.0.1:18789",
            ),
        )

    assert config_path.read_bytes() == previous_bytes
    assert tomllib.loads(previous_bytes.decode())["runtime"]["default_provider"] == "codex"


def test_concurrent_first_configuration_has_one_stable_default(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    barrier_calls = (
        ProviderConfigurationRequest(provider=ProviderKind.CODEX),
        ProviderConfigurationRequest(provider=ProviderKind.CLAUDE),
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(lambda request: configure_provider(config_path, request), barrier_calls)
        )

    payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    defaults = {result.default_provider for result in results}
    assert len(defaults) == 1
    assert sum(result.is_default_changed for result in results) == 1
    assert payload["runtime"]["default_provider"] in {"codex", "claude"}
    assert payload["codex"]["enabled"] is True
    assert payload["claude"]["enabled"] is True


def test_bare_and_status_are_passive_with_zero_providers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.toml"
    monkeypatch.setenv("AUTOCLAW_CONFIG", str(config_path))
    monkeypatch.setattr(
        "autoclaw.interfaces.cli.providers.inspection.subprocess.run",
        lambda *_args, **_kwargs: pytest.fail("passive status invoked a provider command"),
    )
    runner = CliRunner()
    parser = build_parser()

    bare = runner.invoke(parser, [])
    status = runner.invoke(parser, ["status", "--config", str(config_path), "--json"])

    assert bare.exit_code == 0
    assert status.exit_code == 0
    assert "default provider: not configured" in bare.output
    payload = json.loads(status.output)
    assert payload["default_provider"] is None
    assert all(not provider["configured"] for provider in payload["providers"])
    assert payload["database"]["schema"] == "not_checked"
    assert payload["service"]["status"] == "not_checked"
    assert not config_path.exists()


def test_status_redacts_database_password(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        '[database]\nurl = "postgresql+asyncpg://operator:secret@localhost/autoclaw"\n',
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        build_parser(),
        ["status", "--config", str(config_path), "--json"],
    )

    assert result.exit_code == 0
    assert "secret" not in result.output
    assert json.loads(result.output)["database"]["configured_url"] == (
        "postgresql+asyncpg://operator:***@localhost/autoclaw"
    )


def test_provider_list_and_status_are_passive_and_mark_openclaw_experimental(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[openclaw]
enabled = true
gateway_url = "ws://user:secret@127.0.0.1:18789"
gateway_profile = "external"

[runtime]
default_provider = "openclaw"
""".strip()
        + "\n",
        encoding="utf-8",
    )
    previous_bytes = config_path.read_bytes()
    runner = CliRunner()
    parser = build_parser()

    listed = runner.invoke(parser, ["providers", "list", "--json"])
    status = runner.invoke(
        parser,
        ["providers", "status", "openclaw", "--config", str(config_path), "--json"],
    )

    assert listed.exit_code == 0
    assert status.exit_code == 0
    list_payload = json.loads(listed.output)
    status_payload = json.loads(status.output)
    openclaw_definition = next(
        provider for provider in list_payload["providers"] if provider["kind"] == "openclaw"
    )
    assert openclaw_definition["product_status"] == "experimental"
    assert openclaw_definition["setup_owner"] == "user"
    assert status_payload["providers"][0]["authentication"] == "not_checked"
    assert status_payload["providers"][0]["reachability"] == "not_checked"
    assert "user:secret" not in status.output
    assert config_path.read_bytes() == previous_bytes


def test_provider_check_runs_bounded_diagnostic_without_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.toml"
    configure_provider(
        config_path,
        ProviderConfigurationRequest(provider=ProviderKind.CODEX),
    )
    previous_bytes = config_path.read_bytes()
    monkeypatch.setattr(
        "autoclaw.interfaces.cli.providers.inspection.module_is_available",
        lambda _module: True,
    )
    monkeypatch.setattr(
        "autoclaw.interfaces.cli.providers.inspection.execute_provider_diagnostic",
        lambda _settings, provider: ProviderCheckResult(
            kind=provider,
            status=ProviderCheckStatus.AVAILABLE,
            code="codex_available",
        ),
    )

    result = CliRunner().invoke(
        build_parser(),
        ["providers", "check", "codex", "--config", str(config_path), "--json"],
    )
    human_result = CliRunner().invoke(
        build_parser(),
        ["providers", "check", "codex", "--config", str(config_path)],
    )

    assert result.exit_code == 0
    assert human_result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["outcome"] == "ready"
    assert payload["is_ready"] is True
    assert payload["authentication"] == "not_checked"
    assert payload["reachability"] == "not_checked"
    assert "Authentication: not tested" in human_result.output
    assert "Reachability: not tested" in human_result.output
    assert "not_checked" not in human_result.output
    assert config_path.read_bytes() == previous_bytes


def test_provider_status_keeps_passive_diagnostics_out_of_human_output(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"
    configure_provider(
        config_path,
        ProviderConfigurationRequest(provider=ProviderKind.CODEX),
    )

    result = CliRunner().invoke(
        build_parser(),
        ["providers", "status", "--config", str(config_path)],
    )

    assert result.exit_code == 0
    assert "Provider status" in result.output
    assert "Codex" in result.output
    assert "Local configuration only" in result.output
    assert "autoclaw providers check codex" in result.output
    assert "not_checked" not in result.output


def test_provider_check_maps_authentication_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.toml"
    configure_provider(
        config_path,
        ProviderConfigurationRequest(provider=ProviderKind.CODEX),
    )
    monkeypatch.setattr(
        "autoclaw.interfaces.cli.providers.inspection.module_is_available",
        lambda _module: True,
    )
    monkeypatch.setattr(
        "autoclaw.interfaces.cli.providers.inspection.execute_provider_diagnostic",
        lambda _settings, provider: ProviderCheckResult(
            kind=provider,
            status=ProviderCheckStatus.UNAVAILABLE,
            code="codex_authentication_required",
            authentication=ProviderCheckAxisStatus.FAILED,
        ),
    )

    result = CliRunner().invoke(
        build_parser(),
        ["providers", "check", "codex", "--config", str(config_path), "--json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["outcome"] == "authentication_failed"
    assert payload["authentication"] == "failed"
    assert payload["reachability"] == "not_checked"


def test_provider_diagnostic_timeout_includes_adapter_cleanup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class SlowCleanupAdapter:
        @asynccontextmanager
        async def lifespan(self) -> AsyncIterator[None]:
            try:
                yield
            finally:
                await asyncio.Event().wait()

        async def read_availability(self) -> ProviderCheckResult:
            return ProviderCheckResult(
                kind=ProviderKind.CODEX,
                status=ProviderCheckStatus.AVAILABLE,
                code="codex_available",
            )

    monkeypatch.setattr(
        "autoclaw.integrations.provider_registry.build_provider_adapter",
        lambda _provider, _settings: SlowCleanupAdapter(),
    )
    monkeypatch.setattr(provider_inspection, "PROVIDER_CHECK_TIMEOUT_SECONDS", 0.01)

    with pytest.raises(TimeoutError):
        provider_inspection.execute_provider_diagnostic(
            Settings(),
            ProviderKind.CODEX,
        )


def test_setup_uses_the_shared_configuration_operation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_path = tmp_path / "config.toml"
    calls: list[ProviderConfigurationRequest] = []
    original = provider_commands.configure_provider

    def recording_configure(
        path: Path,
        request: ProviderConfigurationRequest,
    ) -> ProviderConfigurationSnapshot:
        calls.append(request)
        return original(path, request)

    monkeypatch.setattr(provider_commands, "configure_provider", recording_configure)

    result = provider_commands.cmd_setup(
        argparse.Namespace(
            config=str(config_path),
            provider="claude",
            model="sonnet",
            effort=None,
            gateway_url=None,
            gateway_profile=None,
            json=True,
        )
    )

    assert result == 0
    assert calls == [ProviderConfigurationRequest(provider=ProviderKind.CLAUDE, model="sonnet")]
    assert tomllib.loads(config_path.read_text())["runtime"]["default_provider"] == "claude"


def test_json_setup_without_provider_is_a_zero_write_guide(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"

    result = CliRunner().invoke(
        build_parser(),
        ["setup", "--config", str(config_path), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload == {
        "ok": True,
        "configured_provider": None,
        "configured_providers": [],
        "default_provider": None,
        "default_provider_configured": False,
        "next_actions": [
            "autoclaw init",
            "autoclaw providers configure <provider>",
        ],
    }
    assert not config_path.exists()


@pytest.mark.parametrize(
    ("config_text", "configured", "default_provider", "next_actions"),
    (
        (
            "[codex]\nenabled = true\n",
            ["codex"],
            None,
            ["autoclaw providers set-default codex"],
        ),
        (
            '[codex]\nenabled = true\n[runtime]\ndefault_provider = "codex"\n',
            ["codex"],
            "codex",
            ["autoclaw providers check codex", "autoclaw serve"],
        ),
        (
            "[codex]\nenabled = true\n[claude]\nenabled = true\n",
            ["codex", "claude"],
            None,
            ["autoclaw providers set-default <provider>"],
        ),
    ),
)
def test_json_setup_guide_uses_selected_provider_state_without_writes(
    tmp_path: Path,
    config_text: str,
    configured: list[str],
    default_provider: str | None,
    next_actions: list[str],
) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(config_text, encoding="utf-8")
    previous_bytes = config_path.read_bytes()

    result = CliRunner().invoke(
        build_parser(),
        ["setup", "--config", str(config_path), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["configured_providers"] == configured
    assert payload["configured_provider"] == (configured[0] if len(configured) == 1 else None)
    assert payload["default_provider"] == default_provider
    assert payload["default_provider_configured"] is (default_provider is not None)
    assert payload["next_actions"] == next_actions
    assert config_path.read_bytes() == previous_bytes


def test_json_setup_guide_configures_environment_only_provider_before_default(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "config.toml"

    result = CliRunner().invoke(
        build_parser(),
        ["setup", "--config", str(config_path), "--json"],
        env={"AUTOCLAW_CODEX__ENABLED": "true"},
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["configured_providers"] == ["codex"]
    assert payload["default_provider"] is None
    assert payload["next_actions"] == ["autoclaw providers configure codex"]
    assert not config_path.exists()


def test_codex_identity_delegates_without_reading_or_storing_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    native_calls: list[tuple[list[str], dict[str, object]]] = []

    def native_runner(
        command: list[str],
        **options: object,
    ) -> subprocess.CompletedProcess[str]:
        native_calls.append((command, options))
        return subprocess.CompletedProcess(command, 0)

    bundled_binary = tmp_path / "codex"
    monkeypatch.setattr(
        "autoclaw.interfaces.cli.providers.inspection.bundled_codex_path",
        lambda: bundled_binary,
    )

    snapshot = invoke_provider_identity_action(
        ProviderKind.CODEX,
        "login",
        is_json_output=True,
        command_runner=native_runner,
    )

    assert snapshot.outcome == ProviderIdentityOutcome.SUCCEEDED
    assert native_calls[0][0] == [str(bundled_binary), "login"]
    assert native_calls[0][1]["stdout"] == subprocess.DEVNULL
    assert native_calls[0][1]["stderr"] == subprocess.DEVNULL


@pytest.mark.parametrize("provider", [ProviderKind.CLAUDE, ProviderKind.OPENCLAW])
def test_non_codex_identity_remains_user_managed(provider: ProviderKind) -> None:
    snapshot = invoke_provider_identity_action(
        provider,
        "logout",
        is_json_output=True,
    )

    assert snapshot.outcome == ProviderIdentityOutcome.USER_MANAGED
    assert "user-managed" in snapshot.detail
