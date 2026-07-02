from __future__ import annotations

import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CONSOLE_DIST_DIR = REPO_ROOT / "apps" / "console" / "dist"
PACKAGED_CONSOLE_ASSETS_DIR = (
    REPO_ROOT / "apps" / "api" / "src" / "autoclaw" / "interfaces" / "web_console" / "assets"
)


def main() -> int:
    index_path = CONSOLE_DIST_DIR / "index.html"
    if not index_path.is_file():
        raise SystemExit(
            "Console dist is missing. Run `make console-build` before syncing package assets."
        )

    if PACKAGED_CONSOLE_ASSETS_DIR.exists():
        shutil.rmtree(PACKAGED_CONSOLE_ASSETS_DIR)
    shutil.copytree(CONSOLE_DIST_DIR, PACKAGED_CONSOLE_ASSETS_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
