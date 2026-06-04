from __future__ import annotations

import importlib


def test_runtime_materialization_owner_shells_share_app_runtime_exports() -> None:
    legacy_runtime = importlib.import_module("autoclaw.runtime")
    legacy_runtime_contracts = importlib.import_module("autoclaw.runtime.contracts")
    legacy_prompt = importlib.import_module("autoclaw.runtime.prompt")
    legacy_task_root = importlib.import_module("autoclaw.runtime.task_root")
    legacy_projection = importlib.import_module("autoclaw.runtime.projection")
    legacy_manifest = importlib.import_module("autoclaw.runtime.projection.manifest")
    legacy_launch = importlib.import_module("autoclaw.runtime.launch")
    legacy_bootstrap = importlib.import_module("autoclaw.runtime.launch.bootstrap")
    autoclaw_runtime = importlib.import_module("autoclaw.runtime")
    autoclaw_prompt = importlib.import_module("autoclaw.runtime.prompt")
    autoclaw_task_root = importlib.import_module("autoclaw.runtime.task_root")
    autoclaw_projection = importlib.import_module("autoclaw.runtime.projection")
    autoclaw_manifest = importlib.import_module("autoclaw.runtime.projection.manifest")
    autoclaw_launch = importlib.import_module("autoclaw.runtime.launch")
    autoclaw_bootstrap = importlib.import_module("autoclaw.runtime.launch.bootstrap")

    for export_name in legacy_runtime.__all__:
        assert hasattr(autoclaw_runtime, export_name)
        assert getattr(autoclaw_runtime, export_name) is getattr(legacy_runtime, export_name)

    assert autoclaw_runtime.PromptSendMode is legacy_runtime_contracts.PromptSendMode
    assert (
        autoclaw_runtime.RuntimeBootstrapResult is legacy_runtime_contracts.RuntimeBootstrapResult
    )
    assert autoclaw_prompt.render_prompt_bundle is legacy_prompt.render_prompt_bundle
    assert autoclaw_task_root.resolve_task_root_paths is legacy_task_root.resolve_task_root_paths
    assert (
        autoclaw_projection.materialize_attempt_files is legacy_projection.materialize_attempt_files
    )
    assert (
        autoclaw_manifest.build_current_structural_edit_palette
        is legacy_manifest.build_current_structural_edit_palette
    )
    assert (
        autoclaw_launch.persist_bootstrap_runtime_from_precomputed
        is legacy_launch.persist_bootstrap_runtime_from_precomputed
    )
    assert autoclaw_launch.launch_task_runtime is legacy_launch.launch_task_runtime
    assert (
        autoclaw_bootstrap.build_bootstrap_runtime_projection_result
        is legacy_bootstrap.build_bootstrap_runtime_projection_result
    )
