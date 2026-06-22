from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from ism.config import load_config
from ism.planning import build_execution_plan


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ism")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser(
        "validate-config",
        help="validate and print a resolved experiment config",
    )
    validate.add_argument("--config", required=True, type=Path)

    dry_run = subparsers.add_parser(
        "dry-run",
        help="validate config and print the bounded execution plan",
    )
    dry_run.add_argument("--config", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "validate-config":
            sys.stdout.write(config.stable_json())
            return
        if args.command == "dry-run":
            payload = {
                "config_hash": config.config_hash(),
                "plan": build_execution_plan(config).to_dict(),
            }
            sys.stdout.write(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
            )
            return
        parser.error(f"unsupported command: {args.command}")
    except (OSError, ValueError, ValidationError) as error:
        parser.exit(2, f"error: {error}\n")
