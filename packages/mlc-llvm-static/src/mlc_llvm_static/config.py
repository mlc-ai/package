"""Print paths for the Python environment containing the SDK."""
from __future__ import annotations

import argparse

from . import get_cmake_dir, get_include_dir, get_library_dir, get_llvm_config, get_prefix


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    for flag in ("prefix", "cmake-dir", "include-dir", "library-dir", "llvm-config"):
        group.add_argument(f"--{flag}", action="store_true")
    args = parser.parse_args()
    for name, getter in (
        ("prefix", get_prefix), ("cmake_dir", get_cmake_dir),
        ("include_dir", get_include_dir), ("library_dir", get_library_dir),
        ("llvm_config", get_llvm_config),
    ):
        if getattr(args, name):
            print(getter())


if __name__ == "__main__":
    main()
