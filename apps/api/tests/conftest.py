from __future__ import annotations

import os

os.environ.setdefault("AUTOCLAW_ENV", "test")
os.environ.setdefault("AUTOCLAW_API_KEY", "autoclaw-operator-test-key")
os.environ.setdefault("AUTOCLAW_INTERNAL_API_KEY", "autoclaw-internal-test-key")

from app.config import get_settings

get_settings.cache_clear()
