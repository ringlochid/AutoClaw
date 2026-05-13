from __future__ import annotations

import argparse

from .load import EXAMPLES_PATH, INVENTORY_PATH, load_catalog
from .render import (
    render_generated_examples_md,
    render_inventory_debug,
    render_inventory_md,
)
from .validation import validate_catalog


def generate() -> int:
    data = load_catalog()
    errors = validate_catalog(data, skip_inventory_checks=True)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    INVENTORY_PATH.write_text(render_inventory_md(data), encoding="utf-8")
    EXAMPLES_PATH.write_text(render_generated_examples_md(data), encoding="utf-8")
    return 0


def validate() -> int:
    data = load_catalog()
    errors = validate_catalog(data)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("Prompt catalog validation passed.")
    return 0


def inventory() -> int:
    data = load_catalog()
    print(render_inventory_debug(data), end="")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["generate", "validate", "inventory"])
    args = parser.parse_args(argv)
    if args.command == "generate":
        return generate()
    if args.command == "inventory":
        return inventory()
    return validate()


if __name__ == "__main__":
    raise SystemExit(main())
