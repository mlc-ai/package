"""Build and stage static Z3 development artifacts."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=cwd, env=env)


def _tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required tool not found on PATH: {name}")
    return path


def _download_source(tag: str, build_root: Path) -> Path:
    archive = build_root / f"{tag}.tar.gz"
    source_dir = build_root / f"z3-{tag}"
    if source_dir.exists():
        return source_dir

    url = f"https://github.com/Z3Prover/z3/archive/refs/tags/{tag}.tar.gz"
    print(f"Downloading {url}", flush=True)
    urllib.request.urlretrieve(url, archive)

    extract_dir = build_root / "src"
    shutil.rmtree(extract_dir, ignore_errors=True)
    extract_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:gz") as tar:
        tar.extractall(extract_dir)

    children = [p for p in extract_dir.iterdir() if p.is_dir()]
    if len(children) != 1:
        raise RuntimeError(f"Expected one extracted Z3 source directory, got {children}")
    children[0].rename(source_dir)
    return source_dir


def _copy_tree(src: Path, dst: Path) -> None:
    if src.exists():
        shutil.copytree(src, dst, dirs_exist_ok=True)


def _normalize_metadata_library_dirs(static_dir: Path) -> None:
    """Point staged CMake/pkg-config metadata at the normalized lib directory."""
    metadata_files = [
        *static_dir.glob("lib/cmake/z3/*.cmake"),
        *static_dir.glob("lib/pkgconfig/*.pc"),
    ]
    for path in metadata_files:
        text = path.read_text(encoding="utf-8")
        normalized = text.replace("/lib64", "/lib")
        if normalized != text:
            path.write_text(normalized, encoding="utf-8")


def main() -> None:
    tag = os.environ.get("STATICLIB_Z3_TAG", "z3-4.16.0")
    package_dir = Path(
        os.environ.get("STATICLIB_Z3_PACKAGE_DIR", Path.cwd() / "build/local-package/z3_static")
    ).resolve()
    build_root = Path(os.environ.get("STATICLIB_Z3_BUILD_ROOT", Path.cwd() / "build/z3")).resolve()
    source_env = os.environ.get("STATICLIB_Z3_SOURCE_DIR") or None

    cmake = _tool("cmake")
    ninja = _tool("ninja")

    build_root.mkdir(parents=True, exist_ok=True)
    source_dir = Path(source_env).resolve() if source_env else _download_source(tag, build_root)
    if not source_dir.exists():
        raise RuntimeError(f"Z3 source directory does not exist: {source_dir}")

    build_dir = build_root / "build"
    install_dir = build_root / "install"
    shutil.rmtree(build_dir, ignore_errors=True)
    shutil.rmtree(install_dir, ignore_errors=True)
    build_dir.mkdir(parents=True, exist_ok=True)

    cmake_args = [
        cmake,
        "-S",
        str(source_dir),
        "-B",
        str(build_dir),
        "-G",
        "Ninja",
        f"-DCMAKE_MAKE_PROGRAM={ninja}",
        f"-DCMAKE_INSTALL_PREFIX={install_dir}",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DZ3_BUILD_LIBZ3_SHARED=OFF",
        "-DZ3_BUILD_EXECUTABLE=OFF",
        "-DZ3_BUILD_PYTHON_BINDINGS=OFF",
        "-DZ3_BUILD_TEST_EXECUTABLES=OFF",
    ]
    if sys.platform == "darwin":
        deployment_target = os.environ.get("MACOSX_DEPLOYMENT_TARGET") or "14.0"
        cmake_args.append(f"-DCMAKE_OSX_DEPLOYMENT_TARGET={deployment_target}")
    _run(cmake_args)
    _run([cmake, "--build", str(build_dir), "--parallel"])
    _run([cmake, "--install", str(build_dir)])

    static_dir = package_dir / "static"
    shutil.rmtree(static_dir, ignore_errors=True)
    static_dir.mkdir(parents=True, exist_ok=True)

    _copy_tree(install_dir / "include", static_dir / "include")
    _copy_tree(install_dir / "lib", static_dir / "lib")
    _copy_tree(install_dir / "lib64", static_dir / "lib")
    _copy_tree(install_dir / "share", static_dir / "share")
    _normalize_metadata_library_dirs(static_dir)

    license_src = source_dir / "LICENSE.txt"
    if not license_src.exists():
        license_src = source_dir / "LICENSE"
    if not license_src.exists():
        raise RuntimeError("Could not find upstream Z3 license file")
    shutil.copy2(license_src, static_dir / "LICENSE.Z3")

    if not (static_dir / "include" / "z3++.h").exists():
        raise RuntimeError("Z3 C++ header was not staged")
    libs = list((static_dir / "lib").glob("libz3.a")) + list((static_dir / "lib").glob("*.lib"))
    if not libs:
        raise RuntimeError("Static Z3 library was not staged")
    cmake_dirs = list((static_dir / "lib").glob("cmake/z3"))
    if not cmake_dirs:
        raise RuntimeError("Z3 CMake package files were not staged")

    print(f"Staged Z3 static artifacts under {static_dir}", flush=True)


if __name__ == "__main__":
    main()

