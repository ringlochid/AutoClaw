from __future__ import annotations

from app.api.deps import API_KEY_HEADER
from app.config import get_settings


def operator_api_key_headers() -> dict[str, str]:
    return {API_KEY_HEADER: get_settings().api_key}


def internal_api_key_headers() -> dict[str, str]:
    return {API_KEY_HEADER: get_settings().internal_api_key}


def api_key_headers() -> dict[str, str]:
    return internal_api_key_headers()
