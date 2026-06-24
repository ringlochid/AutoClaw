from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

APPS_API_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = APPS_API_ROOT / "src"


@contextmanager
def use_src_autoclaw_package() -> Iterator[None]:
    original_path = list(sys.path)
    original_modules = {
        name: module
        for name, module in sys.modules.items()
        if name == "autoclaw" or name.startswith("autoclaw.")
    }

    try:
        sys.path = [str(SRC_ROOT), *[entry for entry in sys.path if entry != str(SRC_ROOT)]]
        for name in list(original_modules):
            sys.modules.pop(name, None)
        yield
    finally:
        sys.path = original_path
        for name in list(sys.modules):
            if name == "autoclaw" or name.startswith("autoclaw."):
                sys.modules.pop(name, None)
        sys.modules.update(original_modules)


def test_runtime_contract_and_persistence_landing_shells_share_owner_types() -> None:
    with use_src_autoclaw_package():
        persistence = importlib.import_module("autoclaw.persistence")
        runtime = importlib.import_module("autoclaw.runtime")
        runtime_contracts = importlib.import_module("autoclaw.runtime.contracts")
        capability_contracts = importlib.import_module("autoclaw.runtime.contracts.capabilities")
        command_run_contracts = importlib.import_module("autoclaw.runtime.contracts.command_runs")
        human_request_contracts = importlib.import_module(
            "autoclaw.runtime.contracts.human_requests"
        )
        launch_contracts = importlib.import_module("autoclaw.runtime.contracts.launch")
        primitive_contracts = importlib.import_module("autoclaw.runtime.contracts.primitives")
        projection_contracts = importlib.import_module("autoclaw.runtime.contracts.projection")
        prompt_contracts = importlib.import_module("autoclaw.runtime.contracts.prompt")
        provider_contracts = importlib.import_module(
            "autoclaw.runtime.contracts.provider_resolution"
        )
        task_event_contracts = importlib.import_module("autoclaw.runtime.contracts.task_events")

        assert runtime.FlowStatus is runtime_contracts.FlowStatus
        assert runtime.RuntimeLaunchInput is runtime_contracts.RuntimeLaunchInput
        assert runtime.TaskStartRequest is runtime_contracts.TaskStartRequest
        assert (
            persistence.RuntimeBase is importlib.import_module("autoclaw.persistence").RuntimeBase
        )
        assert launch_contracts.RuntimeLaunchInput is runtime_contracts.RuntimeLaunchInput
        assert primitive_contracts.FlowStatus is runtime_contracts.FlowStatus
        assert primitive_contracts.ProviderName is runtime_contracts.ProviderName
        assert provider_contracts.ProviderResolution is runtime_contracts.ProviderResolution
        assert (
            capability_contracts.EffectiveCapabilitySet is runtime_contracts.EffectiveCapabilitySet
        )
        assert human_request_contracts.PendingHumanRequest is runtime_contracts.PendingHumanRequest
        assert command_run_contracts.CommandRunRecord is runtime_contracts.CommandRunRecord
        assert task_event_contracts.TaskEventRecord is runtime_contracts.TaskEventRecord
        assert projection_contracts.ManifestProjection is runtime_contracts.ManifestProjection
        assert prompt_contracts.PromptFamily is runtime_contracts.PromptFamily
