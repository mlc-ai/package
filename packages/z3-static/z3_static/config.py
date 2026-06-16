"""Command-line configuration helpers for z3-static."""

from __future__ import annotations

import argparse
import sys

from . import get_cmake_dir


def main(argv: list[str] | None = None) -> None:
    """Print z3-static configuration paths."""
    parser = argparse.ArgumentParser(
        description="Get configuration information needed to compile with z3-static"
    )
    parser.add_argument(
        "--cmake-dir", action="store_true", help="Print Z3 CMake package directory"
    )

    args = parser.parse_args(argv)
    if argv is None and len(sys.argv) == 1:
        parser.print_help()
        return

    if args.cmake_dir:
        print(get_cmake_dir())


if __name__ == "__main__":
    main()
