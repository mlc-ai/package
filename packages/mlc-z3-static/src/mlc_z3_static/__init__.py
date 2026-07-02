from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._version import Z3_COMMIT, Z3_TAG, __version__

__all__ = [
    "__version__",
    "Z3_COMMIT",
    "Z3_TAG",
    "artifact_kinds",
    "get_cmake_dir",
    "get_cmake_prefix_path",
    "get_include_dir",
    "get_library_dir",
    "get_library_path",
    "get_pkgconfig_dir",
    "get_shared_library_path",
    "get_static_library_path",
    "metadata",
]

_VALID_KINDS = {"static", "shared"}


def _package_dir() -> Path:
    return Path(__file__).resolve().parent


def _artifact_dir(kind: str) -> Path:
    if kind not in _VALID_KINDS:
        raise ValueError(f"Expected artifact kind to be one of {sorted(_VALID_KINDS)}, got {kind!r}")
    path = _package_dir() / kind
    if not path.is_dir():
        raise FileNotFoundError(f"Z3 {kind} artifact directory is missing: {path}")
    return path


def artifact_kinds() -> list[str]:
    return [kind for kind in sorted(_VALID_KINDS) if (_package_dir() / kind).is_dir()]


def get_include_dir(kind: str = "static") -> str:
    path = _artifact_dir(kind) / "include"
    if not path.is_dir():
        raise FileNotFoundError(f"Z3 include directory is missing: {path}")
    return str(path)


def get_library_dir(kind: str = "static") -> str:
    path = _artifact_dir(kind) / "lib"
    if not path.is_dir():
        raise FileNotFoundError(f"Z3 library directory is missing: {path}")
    return str(path)


def _library_candidates(kind: str, artifact_dir: Path) -> list[Path]:
    lib_dir = artifact_dir / "lib"
    bin_dir = artifact_dir / "bin"
    if kind == "static":
        return [
            lib_dir / "libz3.a",
            lib_dir / "z3.lib",
            lib_dir / "libz3.lib",
        ]

    candidates = [
        lib_dir / "libz3.dylib",
        lib_dir / "libz3.so",
        bin_dir / "z3.dll",
        bin_dir / "libz3.dll",
        lib_dir / "z3.dll",
        lib_dir / "libz3.dll",
    ]
    candidates.extend(sorted(lib_dir.glob("libz3.so*")))
    return candidates


def get_library_path(kind: str = "static") -> str:
    artifact_dir = _artifact_dir(kind)
    for candidate in _library_candidates(kind, artifact_dir):
        if candidate.is_file():
            return str(candidate)
    raise FileNotFoundError(f"Z3 {kind} library is missing in {artifact_dir / 'lib'}")


def get_static_library_path() -> str:
    return get_library_path("static")


def get_shared_library_path() -> str:
    return get_library_path("shared")


def get_cmake_prefix_path(kind: str = "static") -> str:
    return str(_artifact_dir(kind))


def get_cmake_dir(kind: str = "static") -> str:
    path = _artifact_dir(kind) / "lib" / "cmake" / "z3"
    if not path.is_dir():
        raise FileNotFoundError(f"Z3 CMake package directory is missing: {path}")
    return str(path)


def get_pkgconfig_dir(kind: str = "static") -> str:
    path = _artifact_dir(kind) / "lib" / "pkgconfig"
    if not path.is_dir():
        raise FileNotFoundError(f"Z3 pkg-config directory is missing: {path}")
    return str(path)


def metadata() -> dict[str, Any]:
    path = _package_dir() / "staticlib.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))
