"""Locate the packaged static Z3 development artifacts."""

from __future__ import annotations

from pathlib import Path

__version__ = "4.16.0"


def get_prefix() -> str:
    """Return the packaged native artifact prefix."""
    return str(Path(__file__).resolve().parent / "static")


def get_cmake_dir() -> str:
    """Return the Z3 CMake package directory."""
    return str(Path(get_prefix()) / "lib" / "cmake" / "z3")


def get_include_dir() -> str:
    """Return the Z3 include directory."""
    return str(Path(get_prefix()) / "include")


def get_library_dir() -> str:
    """Return the Z3 library directory."""
    return str(Path(get_prefix()) / "lib")

