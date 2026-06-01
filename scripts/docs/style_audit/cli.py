from __future__ import annotations

import argparse

from .config import build_audit_settings
from .report import render_audit_report
from .scan import run_style_audit


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--fail-on-findings",
        action="store_true",
        help="exit non-zero when the audit reports findings",
    )
    args = parser.parse_args(argv)

    settings = build_audit_settings()
    results = run_style_audit(settings)
    print(render_audit_report(results, settings), end="")
    return 1 if args.fail_on_findings and results.has_findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
