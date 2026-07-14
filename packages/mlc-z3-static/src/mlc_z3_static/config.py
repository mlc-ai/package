"""Command-line configuration helpers for mlc-z3-static."""

from __future__ import annotations

import argparse
import sys

from . import get_cmake_dir, get_cmake_prefix_path, get_include_dir, get_library_dir


def main(argv: list[str] | None = None) -> None:
    """Print mlc-z3-static configuration paths."""
    parser = argparse.ArgumentParser(
        description="Get configuration information needed to compile with mlc-z3-static"
    )
    parser.add_argument(
        "--kind",
        choices=["static", "shared"],
        default="static",
        help="Artifact flavor to report (default: static)",
    )
    parser.add_argument(
        "--prefix", action="store_true", help="Print the Z3 CMake prefix path"
    )
    parser.add_argument(
        "--cmake-dir", action="store_true", help="Print the Z3 CMake package directory"
    )
    parser.add_argument(
        "--include-dir", action="store_true", help="Print the Z3 include directory"
    )
    parser.add_argument(
        "--library-dir", action="store_true", help="Print the Z3 library directory"
    )

    args = parser.parse_args(argv)
    if argv is None and len(sys.argv) == 1:
        parser.print_help()
        return

    if args.prefix:
        print(get_cmake_prefix_path(args.kind))
    if args.cmake_dir:
        print(get_cmake_dir(args.kind))
    if args.include_dir:
        print(get_include_dir(args.kind))
    if args.library_dir:
        print(get_library_dir(args.kind))


if __name__ == "__main__":
    main()
