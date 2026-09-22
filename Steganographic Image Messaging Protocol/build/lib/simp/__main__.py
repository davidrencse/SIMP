"""Unified command-line entry point for SIMP."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        return _messenger([])
    parser = argparse.ArgumentParser(
        prog="simp",
        description="SIMP - Steganographic Image Messaging Protocol",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("workbench", "messenger", "relay", "codec"),
        help="component to run",
    )
    namespace = parser.parse_args(arguments[:1])
    remaining = arguments[1:]
    if namespace.command is None:
        parser.print_help()
        return 0

    runners: dict[str, Callable[[list[str] | None], int]] = {
        "workbench": _workbench,
        "messenger": _messenger,
        "relay": _relay,
        "codec": _codec,
    }
    return runners[namespace.command](remaining)


def _workbench(arguments: list[str] | None) -> int:
    from .workbench import main as run

    return run(arguments)


def _messenger(arguments: list[str] | None) -> int:
    from .chat import main as run

    return run(arguments)


def _relay(arguments: list[str] | None) -> int:
    from .relay import main as run

    return run(arguments)


def _codec(arguments: list[str] | None) -> int:
    from .steg import main as run

    return run(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
