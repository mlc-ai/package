"""Version constants, artifact paths, and the config CLI of the installed wheel."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

import mlc_z3_static

KINDS = ["static"]


def test_version_constants() -> None:
    # __version__ may add a PEP 440 suffix such as .post1 to the upstream release.
    assert mlc_z3_static.__version__.startswith(mlc_z3_static.Z3_VERSION)
    assert mlc_z3_static.Z3_TAG == f"z3-{mlc_z3_static.Z3_VERSION}"
    assert len(mlc_z3_static.Z3_COMMIT) == 40
    metadata = mlc_z3_static.metadata()
    assert metadata["z3_version"] == mlc_z3_static.Z3_VERSION
    assert metadata["z3_commit"] == mlc_z3_static.Z3_COMMIT
    assert metadata["package_version"] == mlc_z3_static.__version__


def test_artifact_kinds() -> None:
    assert mlc_z3_static.artifact_kinds() == sorted(KINDS)


@pytest.mark.parametrize("kind", KINDS)
def test_artifact_paths(kind: str) -> None:
    assert (Path(mlc_z3_static.get_include_dir(kind)) / "z3++.h").is_file()
    assert (Path(mlc_z3_static.get_cmake_dir(kind)) / "Z3Config.cmake").is_file()
    assert Path(mlc_z3_static.get_library_path(kind)).is_file()


def test_library_flavors() -> None:
    assert Path(mlc_z3_static.get_static_library_path()).suffix in {".a", ".lib"}
    assert not hasattr(mlc_z3_static, "get_shared_library_path")
    with pytest.raises(ValueError):
        mlc_z3_static.get_library_path("shared")


def test_static_only_inventory() -> None:
    root = Path(mlc_z3_static.__file__).parent
    assert set(mlc_z3_static.metadata()["artifacts"]) == {"static"}
    assert not (root / "shared").exists()
    assert not any(path.suffix in {".dll", ".dylib"} or ".so" in path.suffixes
                   for path in root.rglob("*") if path.is_file())


def test_cli_rejects_shared() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mlc_z3_static.config", "--prefix", "--kind", "shared"],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "invalid choice" in result.stderr


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize(
    ("flag", "getter"),
    [
        ("--prefix", mlc_z3_static.get_cmake_prefix_path),
        ("--cmake-dir", mlc_z3_static.get_cmake_dir),
        ("--include-dir", mlc_z3_static.get_include_dir),
        ("--library-dir", mlc_z3_static.get_library_dir),
    ],
)
def test_config_cli(kind: str, flag: str, getter) -> None:
    output = subprocess.check_output(
        [sys.executable, "-m", "mlc_z3_static.config", flag, "--kind", kind], text=True
    )
    assert output.strip() == getter(kind)


def test_bundled_z3_license_is_upstream_mit() -> None:
    license_path = Path(mlc_z3_static.__file__).parent / "licenses" / "LICENSE-Z3.txt"
    assert "Permission is hereby granted, free of charge" in license_path.read_text(encoding="utf-8")
