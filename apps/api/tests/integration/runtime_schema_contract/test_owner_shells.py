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
        if name in {"app", "autoclaw"} or name.startswith(("app.", "autoclaw."))
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


def test_runtime_contract_and_db_landing_shells_share_owner_types() -> None:
    with use_src_autoclaw_package():
        app_db = importlib.import_module("app.db")
        legacy_runtime_contracts = importlib.import_module("app.runtime.contracts")
        legacy_primitives = importlib.import_module("app.runtime.contract_models.primitives")
        legacy_prompt_contracts = importlib.import_module("app.runtime.contract_models.prompt")
        app_runtime_schemas = importlib.import_module("app.schemas.runtime")
        app_runtime_contracts = importlib.import_module("app.schemas.runtime.contracts")
        autoclaw_db = importlib.import_module("autoclaw.db")
        autoclaw_runtime_schemas = importlib.import_module("autoclaw.schemas.runtime")
        autoclaw_runtime_contracts = importlib.import_module("autoclaw.schemas.runtime.contracts")
        autoclaw_launch_contracts = importlib.import_module(
            "autoclaw.schemas.runtime.contracts.launch"
        )
        autoclaw_primitive_contracts = importlib.import_module(
            "autoclaw.schemas.runtime.contracts.primitives"
        )
        autoclaw_projection_contracts = importlib.import_module(
            "autoclaw.schemas.runtime.contracts.projection"
        )
        autoclaw_prompt_contracts = importlib.import_module(
            "autoclaw.schemas.runtime.contracts.prompt"
        )

        assert legacy_runtime_contracts.FlowStatus is app_runtime_contracts.FlowStatus
        assert (
            legacy_runtime_contracts.RuntimeLaunchInput is app_runtime_contracts.RuntimeLaunchInput
        )
        assert legacy_primitives.FlowStatus is app_runtime_contracts.FlowStatus
        assert legacy_prompt_contracts.PromptFamily is app_runtime_contracts.PromptFamily
        assert autoclaw_db.RuntimeBase is app_db.RuntimeBase
        assert autoclaw_runtime_schemas.TaskStartRequest is app_runtime_schemas.TaskStartRequest
        assert autoclaw_runtime_contracts.FlowStatus is app_runtime_contracts.FlowStatus
        assert (
            autoclaw_launch_contracts.RuntimeLaunchInput is app_runtime_contracts.RuntimeLaunchInput
        )
        assert autoclaw_primitive_contracts.FlowStatus is app_runtime_contracts.FlowStatus
        assert (
            autoclaw_projection_contracts.ManifestProjection
            is app_runtime_contracts.ManifestProjection
        )
        assert autoclaw_runtime_contracts.PromptFamily is app_runtime_contracts.PromptFamily
        assert autoclaw_prompt_contracts.PromptFamily is app_runtime_contracts.PromptFamily


def test_runtime_dispatch_watchdog_replan_and_openclaw_shells_share_legacy_exports() -> None:
    with use_src_autoclaw_package():
        autoclaw_control = importlib.import_module("autoclaw.runtime.control")
        autoclaw_dispatch = importlib.import_module("autoclaw.runtime.control.dispatch")
        autoclaw_observability = importlib.import_module("autoclaw.runtime.control.observability")
        autoclaw_parent_tools = importlib.import_module("autoclaw.runtime.control.parent_tools")
        autoclaw_dispatch_authority = importlib.import_module(
            "autoclaw.runtime.control.dispatch.authority"
        )
        autoclaw_dispatch_gateway = importlib.import_module(
            "autoclaw.runtime.control.dispatch.gateway"
        )
        autoclaw_dispatch_openclaw_runtime = importlib.import_module(
            "autoclaw.runtime.control.dispatch.openclaw_runtime"
        )
        autoclaw_replan = importlib.import_module("autoclaw.runtime.replan")
        autoclaw_runtime_openclaw = importlib.import_module("autoclaw.runtime.openclaw")
        autoclaw_watchdog = importlib.import_module("autoclaw.runtime.watchdog")
        autoclaw_integrations_openclaw = importlib.import_module("autoclaw.integrations.openclaw")
        autoclaw_integrations_bindings = importlib.import_module(
            "autoclaw.integrations.openclaw.bindings"
        )
        autoclaw_integrations_common = importlib.import_module(
            "autoclaw.integrations.openclaw.common"
        )
        autoclaw_legacy_openclaw = importlib.import_module("autoclaw.openclaw")
        autoclaw_legacy_bindings = importlib.import_module("autoclaw.openclaw.bindings")
        autoclaw_legacy_common = importlib.import_module("autoclaw.openclaw.common")
        autoclaw_legacy_node_contracts = importlib.import_module(
            "autoclaw.openclaw.node_mcp.contracts"
        )
        app_observability = importlib.import_module("app.runtime.control.observability")
        app_parent_tools = importlib.import_module("app.runtime.control.parent_tools")
        app_dispatch_authority = importlib.import_module("app.runtime.control.dispatch.authority")
        app_dispatch_gateway = importlib.import_module("app.runtime.control.dispatch.gateway")
        app_dispatch_openclaw_runtime = importlib.import_module(
            "app.runtime.control.dispatch.openclaw_runtime"
        )
        app_replan = importlib.import_module("app.runtime.replan")
        app_runtime_openclaw = importlib.import_module("app.runtime.openclaw")
        app_watchdog = importlib.import_module("app.runtime.watchdog")

        assert autoclaw_control.dispatch is autoclaw_dispatch
        assert autoclaw_control.observability is autoclaw_observability
        assert autoclaw_control.parent_tools is autoclaw_parent_tools
        assert autoclaw_dispatch.authority is autoclaw_dispatch_authority
        assert autoclaw_dispatch.gateway is autoclaw_dispatch_gateway
        assert autoclaw_dispatch.openclaw_runtime is autoclaw_dispatch_openclaw_runtime
        assert autoclaw_dispatch_authority.validate_node_session_key is (
            app_dispatch_authority.validate_node_session_key
        )
        assert autoclaw_dispatch_gateway.resolve_gateway_session_key is (
            app_dispatch_gateway.resolve_gateway_session_key
        )
        assert autoclaw_dispatch_openclaw_runtime.close_all_dispatch_runtimes is (
            app_dispatch_openclaw_runtime.close_all_dispatch_runtimes
        )
        assert autoclaw_observability.observability_ref is app_observability.observability_ref
        assert autoclaw_observability.operator_snapshot is app_observability.operator_snapshot
        assert autoclaw_observability.operator_trace is app_observability.operator_trace
        assert autoclaw_parent_tools.call_parent_tool is app_parent_tools.call_parent_tool

        assert autoclaw_replan.add_child_to_current_flow is app_replan.add_child_to_current_flow
        assert (
            autoclaw_replan.remove_child_from_current_flow
            is app_replan.remove_child_from_current_flow
        )
        assert (
            autoclaw_replan.update_child_in_current_flow is app_replan.update_child_in_current_flow
        )

        assert autoclaw_watchdog.drive_watchdog_once is app_watchdog.drive_watchdog_once
        assert autoclaw_watchdog.notify_runtime_watchdog is app_watchdog.notify_runtime_watchdog
        assert autoclaw_watchdog.stop_runtime_watchdog is app_watchdog.stop_runtime_watchdog

        assert (
            autoclaw_runtime_openclaw.OpenClawGatewayAdapter
            is app_runtime_openclaw.OpenClawGatewayAdapter
        )
        assert (
            autoclaw_runtime_openclaw.build_openclaw_gateway_adapter
            is app_runtime_openclaw.build_openclaw_gateway_adapter
        )
        assert (
            autoclaw_runtime_openclaw.OPENCLAW_PROTOCOL_VERSION
            == app_runtime_openclaw.OPENCLAW_PROTOCOL_VERSION
        )

        assert (
            autoclaw_legacy_openclaw.create_node_mcp_app
            is autoclaw_integrations_openclaw.create_node_mcp_app
        )
        assert (
            autoclaw_legacy_openclaw.create_operator_mcp_server
            is autoclaw_integrations_openclaw.create_operator_mcp_server
        )
        assert (
            autoclaw_legacy_bindings.NodeToolContext
            is autoclaw_integrations_bindings.NodeToolContext
        )
        assert (
            autoclaw_legacy_bindings.load_current_node_tool_context
            is autoclaw_integrations_bindings.load_current_node_tool_context
        )
        assert (
            autoclaw_legacy_common.default_transport_security
            is autoclaw_integrations_common.default_transport_security
        )
        assert (
            autoclaw_legacy_common.run_read_operation
            is autoclaw_runtime_openclaw.read_openclaw_operation
        )
        assert autoclaw_legacy_common.run_session_write_operation is (
            autoclaw_runtime_openclaw.write_openclaw_operation
        )
        assert autoclaw_legacy_common.run_runtime_write_operation is (
            autoclaw_runtime_openclaw.write_openclaw_runtime_operation
        )
        assert autoclaw_legacy_common.run_runtime_write_operation_and_wait is (
            autoclaw_runtime_openclaw.write_openclaw_runtime_operation_and_wait
        )
        assert (
            autoclaw_legacy_node_contracts.NODE_TOOL_NAMES
            == autoclaw_integrations_openclaw.NODE_TOOL_NAMES
        )
        assert autoclaw_legacy_node_contracts.NODE_STRUCTURAL_MUTATION_TOOL_NAMES == (
            "assign_child",
            "add_child",
            "update_child",
            "remove_child",
            "release_green",
            "release_blocked",
        )
