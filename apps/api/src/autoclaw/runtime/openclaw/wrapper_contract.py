"""Runtime-facing shell over the OpenClaw gateway substrate."""

from __future__ import annotations

import autoclaw.integrations.openclaw.gateway.wrapper_contract as _owner

WRAPPER_CLIENT_MODE = _owner.WRAPPER_CLIENT_MODE
WRAPPER_MCP_SURFACES_FILENAME = _owner.WRAPPER_MCP_SURFACES_FILENAME
WRAPPER_OPERATOR_CONTRACT_FILENAME = _owner.WRAPPER_OPERATOR_CONTRACT_FILENAME
WRAPPER_PROFILE_FILENAME = _owner.WRAPPER_PROFILE_FILENAME
WRAPPER_REQUIRED_ROLE = _owner.WRAPPER_REQUIRED_ROLE
WRAPPER_REQUIRED_SCOPES = _owner.WRAPPER_REQUIRED_SCOPES
desired_mcp_surfaces = _owner.desired_mcp_surfaces
desired_operator_contract = _owner.desired_operator_contract
desired_wrapper_profile = _owner.desired_wrapper_profile
desired_wrapper_state = _owner.desired_wrapper_state
load_wrapper_material = _owner.load_wrapper_material
load_wrapper_state = _owner.load_wrapper_state
wrapper_mcp_surfaces_path = _owner.wrapper_mcp_surfaces_path
wrapper_operator_contract_path = _owner.wrapper_operator_contract_path
wrapper_profile_path = _owner.wrapper_profile_path
wrapper_state_path = _owner.wrapper_state_path
write_wrapper_material = _owner.write_wrapper_material
write_wrapper_state = _owner.write_wrapper_state

__all__ = [
    "WRAPPER_CLIENT_MODE",
    "WRAPPER_MCP_SURFACES_FILENAME",
    "WRAPPER_OPERATOR_CONTRACT_FILENAME",
    "WRAPPER_PROFILE_FILENAME",
    "WRAPPER_REQUIRED_ROLE",
    "WRAPPER_REQUIRED_SCOPES",
    "desired_mcp_surfaces",
    "desired_operator_contract",
    "desired_wrapper_profile",
    "desired_wrapper_state",
    "load_wrapper_material",
    "load_wrapper_state",
    "wrapper_mcp_surfaces_path",
    "wrapper_operator_contract_path",
    "wrapper_profile_path",
    "wrapper_state_path",
    "write_wrapper_material",
    "write_wrapper_state",
]
