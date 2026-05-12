from __future__ import annotations

import argparse

from .validator import print_inventory, validate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", nargs="?", choices=["validate", "inventory"], default="validate")
    parser.add_argument("--debug-inventory", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "inventory":
        print_inventory()
        return 0
    return validate(debug_inventory=args.debug_inventory)
