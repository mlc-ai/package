#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

Z3_VERSION = "4.16.0"
Z3_TAG = "z3-4.16.0"
Z3_COMMIT = "ddb49568d3520e99799e364fb22f35fc67d887b1"
Z3_ARCHIVE_URL = f"https://github.com/Z3Prover/z3/archive/{Z3_COMMIT}.tar.gz"
Z3_ARCHIVE_SHA256 = "34deac6d0d46002b1040c56a51c4385ebb4ea56baa95fa8dd66e315a25b0cfa6"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE_DIR = PROJECT_ROOT / "src" / "mlc_z3_static"


def run(cmd: list[str | Path], *, cwd: Path | None = None) -> None:
    printable = " ".join(shlex.quote(str(part)) for part in cmd)
    print(f"+ {printable}", flush=True)
    subprocess.run([str(part) for part in cmd], cwd=cwd, check=True)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_archive(path: Path) -> bool:
    if not path.is_file():
        return False
    actual = sha256(path)
    if actual == Z3_ARCHIVE_SHA256:
        return True
    print(f"Discarding {path}: expected {Z3_ARCHIVE_SHA256}, got {actual}", flush=True)
    path.unlink()
    return False


def download_source_archive(work_root: Path) -> Path:
    archive = work_root / f"z3-{Z3_COMMIT}.tar.gz"
    if verify_archive(archive):
        return archive

    tmp = archive.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    print(f"Downloading Z3 {Z3_TAG} source from {Z3_ARCHIVE_URL}", flush=True)
    with urllib.request.urlopen(Z3_ARCHIVE_URL) as response, tmp.open("wb") as dest:
        shutil.copyfileobj(response, dest)
    actual = sha256(tmp)
    if actual != Z3_ARCHIVE_SHA256:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Z3 source archive SHA-256 mismatch: expected {Z3_ARCHIVE_SHA256}, got {actual}")
    tmp.replace(archive)
    return archive


def safe_extract(archive: Path, source_root: Path) -> Path:
    source_dir = source_root / f"z3-{Z3_COMMIT}"
    if (source_dir / "CMakeLists.txt").is_file():
        return source_dir

    extract_dir = source_root / "_extract"
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    base = extract_dir.resolve()
    with tarfile.open(archive, "r:gz") as tar:
        members = tar.getmembers()
        for member in members:
            target = (extract_dir / member.name).resolve()
            if target != base and base not in target.parents:
                raise RuntimeError(f"Refusing to extract path outside destination: {member.name}")
        tar.extractall(extract_dir)

    roots = [path for path in extract_dir.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise RuntimeError(f"Expected one root directory in {archive}, found {roots}")

    if source_dir.exists():
        shutil.rmtree(source_dir)
    shutil.move(str(roots[0]), source_dir)
    shutil.rmtree(extract_dir)
    return source_dir


def get_source_tree(work_root: Path) -> Path:
    source_override = os.environ.get("MLC_Z3_STATIC_SOURCE_DIR")
    if source_override:
        source_dir = Path(source_override).resolve()
        if not (source_dir / "CMakeLists.txt").is_file():
            raise RuntimeError(f"MLC_Z3_STATIC_SOURCE_DIR is not a Z3 source tree: {source_dir}")
        return source_dir

    archive = download_source_archive(work_root)
    return safe_extract(archive, work_root / "src")


def cmake_configure_command(source_dir: Path, build_dir: Path, stage_dir: Path, kind: str) -> list[str | Path]:
    build_type = os.environ.get("MLC_Z3_STATIC_BUILD_TYPE", "Release")
    shared = "ON" if kind == "shared" else "OFF"
    cmd: list[str | Path] = [
        "cmake",
        "-S",
        source_dir,
        "-B",
        build_dir,
    ]

    generator = os.environ.get("MLC_Z3_STATIC_CMAKE_GENERATOR")
    if generator:
        cmd.extend(["-G", generator])
    elif platform.system() != "Windows" and shutil.which("ninja"):
        cmd.extend(["-G", "Ninja"])

    cmd.extend(
        [
            f"-DCMAKE_BUILD_TYPE={build_type}",
            f"-DCMAKE_INSTALL_PREFIX={stage_dir}",
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_INSTALL_INCLUDEDIR=include",
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
            "-DCMAKE_CXX_STANDARD=20",
            "-DCMAKE_CXX_STANDARD_REQUIRED=ON",
            f"-DZ3_BUILD_LIBZ3_SHARED={shared}",
            "-DZ3_BUILD_PYTHON_BINDINGS=OFF",
            "-DZ3_INSTALL_PYTHON_BINDINGS=OFF",
            "-DZ3_BUILD_DOTNET_BINDINGS=OFF",
            "-DZ3_INSTALL_DOTNET_BINDINGS=OFF",
            "-DZ3_BUILD_JAVA_BINDINGS=OFF",
            "-DZ3_INSTALL_JAVA_BINDINGS=OFF",
            "-DZ3_BUILD_GO_BINDINGS=OFF",
            "-DZ3_BUILD_OCAML_BINDINGS=OFF",
            "-DZ3_BUILD_JULIA_BINDINGS=OFF",
            "-DZ3_ENABLE_EXAMPLE_TARGETS=OFF",
            "-DZ3_BUILD_EXECUTABLE=OFF",
            "-DZ3_BUILD_TEST_EXECUTABLES=OFF",
            "-DZ3_USE_LIB_GMP=OFF",
            "-DZ3_INCLUDE_GIT_DESCRIBE=OFF",
            "-DZ3_INCLUDE_GIT_HASH=OFF",
        ]
    )

    if platform.system() == "Darwin" and os.environ.get("MACOSX_DEPLOYMENT_TARGET"):
        cmd.append(f"-DCMAKE_OSX_DEPLOYMENT_TARGET={os.environ['MACOSX_DEPLOYMENT_TARGET']}")

    for env_name in ("MLC_Z3_STATIC_EXTRA_CMAKE_ARGS", f"MLC_Z3_STATIC_{kind.upper()}_EXTRA_CMAKE_ARGS"):
        extra_args = os.environ.get(env_name)
        if extra_args:
            cmd.extend(shlex.split(extra_args))

    return cmd


def build_and_install(source_dir: Path, work_root: Path, package_dir: Path, kind: str) -> Path:
    build_dir = work_root / f"build-{kind}"
    stage_dir = package_dir / kind
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if stage_dir.exists():
        shutil.rmtree(stage_dir)

    run(cmake_configure_command(source_dir, build_dir, stage_dir, kind))

    build_type = os.environ.get("MLC_Z3_STATIC_BUILD_TYPE", "Release")
    build_cmd: list[str | Path] = [
        "cmake",
        "--build",
        build_dir,
        "--config",
        build_type,
        "--target",
        "install",
    ]
    parallel = os.environ.get("CMAKE_BUILD_PARALLEL_LEVEL")
    if parallel:
        build_cmd.extend(["--parallel", parallel])
    run(build_cmd)
    normalize_installed_metadata(stage_dir, kind)
    validate_stage(stage_dir, kind)
    return stage_dir


def library_candidates(stage_dir: Path, kind: str) -> list[Path]:
    lib_dir = stage_dir / "lib"
    bin_dir = stage_dir / "bin"
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


def first_library(stage_dir: Path, kind: str) -> Path:
    for candidate in library_candidates(stage_dir, kind):
        if candidate.is_file():
            return candidate
    raise RuntimeError(f"Z3 {kind} install tree is missing a libz3 library: {stage_dir}")


def validate_stage(stage_dir: Path, kind: str) -> Path:
    required = [
        stage_dir / "include" / "z3.h",
        stage_dir / "include" / "z3++.h",
        stage_dir / "lib" / "cmake" / "z3" / "Z3Config.cmake",
        stage_dir / "lib" / "cmake" / "z3" / "Z3Targets.cmake",
    ]
    for path in required:
        if not path.is_file():
            raise RuntimeError(f"Z3 {kind} install tree is missing {path.relative_to(stage_dir)}")
    library = first_library(stage_dir, kind)
    validate_relocatable_cmake_exports(stage_dir, kind)
    validate_relocatable_pkgconfig(stage_dir, kind)
    return library


def normalize_installed_metadata(stage_dir: Path, kind: str) -> None:
    relativize_cmake_exports(stage_dir, kind)
    relativize_pkgconfig_files(stage_dir)


def relativize_cmake_exports(stage_dir: Path, kind: str) -> None:
    targets_path = stage_dir / "lib" / "cmake" / "z3" / "Z3Targets.cmake"
    if not targets_path.is_file():
        return

    absolute_stage = str(stage_dir)
    text = targets_path.read_text(encoding="utf-8")
    absolute_import_prefix = f'set(_IMPORT_PREFIX "{absolute_stage}")'
    if absolute_import_prefix not in text:
        return

    relative_import_prefix = """get_filename_component(_IMPORT_PREFIX "${CMAKE_CURRENT_LIST_FILE}" PATH)
get_filename_component(_IMPORT_PREFIX "${_IMPORT_PREFIX}" PATH)
get_filename_component(_IMPORT_PREFIX "${_IMPORT_PREFIX}" PATH)
get_filename_component(_IMPORT_PREFIX "${_IMPORT_PREFIX}" PATH)
if(_IMPORT_PREFIX STREQUAL "/")
  set(_IMPORT_PREFIX "")
endif()"""
    targets_path.write_text(
        text.replace(absolute_import_prefix, relative_import_prefix),
        encoding="utf-8",
    )
    print(f"Relativized Z3 {kind} CMake export: {targets_path.relative_to(stage_dir)}", flush=True)


def relativize_pkgconfig_files(stage_dir: Path) -> None:
    pkgconfig_dir = stage_dir / "lib" / "pkgconfig"
    if not pkgconfig_dir.is_dir():
        return

    replacements = {
        "prefix": "${pcfiledir}/../..",
        "exec_prefix": "${prefix}",
        "libdir": "${exec_prefix}/lib",
        "sharedlibdir": "${exec_prefix}/lib",
        "includedir": "${prefix}/include",
    }
    for path in sorted(pkgconfig_dir.glob("*.pc")):
        lines = []
        changed = False
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, _value = line.partition("=")
            if sep and key in replacements:
                line = f"{key}={replacements[key]}"
                changed = True
            lines.append(line)
        if changed:
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def validate_relocatable_cmake_exports(stage_dir: Path, kind: str) -> None:
    cmake_dir = stage_dir / "lib" / "cmake" / "z3"
    exported_files = [
        path for path in cmake_dir.glob("Z3Targets*.cmake") if path.is_file()
    ]
    if not exported_files:
        raise RuntimeError(f"Z3 {kind} install tree is missing exported CMake targets in {cmake_dir}")

    absolute_stage = str(stage_dir)
    for path in exported_files:
        text = path.read_text(encoding="utf-8")
        if absolute_stage in text:
            raise RuntimeError(
                f"Z3 {kind} CMake export is not relocatable: "
                f"{path.relative_to(stage_dir)} contains {absolute_stage!r}. "
                "Use relative CMake install destinations."
            )


def validate_relocatable_pkgconfig(stage_dir: Path, kind: str) -> None:
    pkgconfig_dir = stage_dir / "lib" / "pkgconfig"
    if not pkgconfig_dir.is_dir():
        return

    absolute_stage = str(stage_dir)
    for path in sorted(pkgconfig_dir.glob("*.pc")):
        text = path.read_text(encoding="utf-8")
        if absolute_stage in text:
            raise RuntimeError(
                f"Z3 {kind} pkg-config metadata is not relocatable: "
                f"{path.relative_to(stage_dir)} contains {absolute_stage!r}."
            )


def clean_package_outputs(package_dir: Path) -> None:
    for name in ("static", "shared", "licenses"):
        shutil.rmtree(package_dir / name, ignore_errors=True)
    for name in ("staticlib.json",):
        (package_dir / name).unlink(missing_ok=True)


def rel(package_dir: Path, path: Path) -> str:
    return path.relative_to(package_dir).as_posix()


def write_version_file(package_dir: Path) -> None:
    (package_dir / "_version.py").write_text(
        (
            f'__version__ = "{Z3_VERSION}"\n'
            f'Z3_TAG = "{Z3_TAG}"\n'
            f'Z3_COMMIT = "{Z3_COMMIT}"\n'
        ),
        encoding="utf-8",
    )


def write_license(package_dir: Path, source_dir: Path) -> str:
    licenses_dir = package_dir / "licenses"
    licenses_dir.mkdir(parents=True, exist_ok=True)
    source_license = source_dir / "LICENSE.txt"
    dest = licenses_dir / "LICENSE-Z3.txt"
    if source_license.is_file():
        shutil.copy2(source_license, dest)
    else:
        dest.write_text("See https://github.com/Z3Prover/z3/blob/master/LICENSE.txt\n", encoding="utf-8")
    return rel(package_dir, dest)


def write_metadata(package_dir: Path, stages: dict[str, Path], source_dir: Path, license_path: str) -> None:
    artifacts: dict[str, dict[str, str]] = {}
    for kind, stage_dir in stages.items():
        library = validate_stage(stage_dir, kind)
        artifacts[kind] = {
            "prefix": rel(package_dir, stage_dir),
            "include_dir": rel(package_dir, stage_dir / "include"),
            "library_dir": rel(package_dir, stage_dir / "lib"),
            "library": rel(package_dir, library),
            "cmake_prefix_path": rel(package_dir, stage_dir),
            "cmake_dir": rel(package_dir, stage_dir / "lib" / "cmake" / "z3"),
            "pkgconfig_dir": rel(package_dir, stage_dir / "lib" / "pkgconfig"),
        }

    metadata = {
        "name": "z3",
        "z3_version": Z3_VERSION,
        "z3_tag": Z3_TAG,
        "z3_commit": Z3_COMMIT,
        "source_repository": "https://github.com/Z3Prover/z3",
        "source_archive_url": Z3_ARCHIVE_URL,
        "source_archive_sha256": Z3_ARCHIVE_SHA256,
        "source_dir": str(source_dir),
        "package_version": Z3_VERSION,
        "artifacts": artifacts,
        "license": license_path,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
    }
    (package_dir / "staticlib.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    package_dir = Path(os.environ.get("MLC_Z3_STATIC_PACKAGE_DIR", DEFAULT_PACKAGE_DIR)).resolve()
    build_root = Path(os.environ.get("MLC_Z3_STATIC_BUILD_ROOT", PROJECT_ROOT / "build" / "z3-v4.16.0")).resolve()
    package_dir.mkdir(parents=True, exist_ok=True)
    build_root.mkdir(parents=True, exist_ok=True)

    source_dir = get_source_tree(build_root)
    clean_package_outputs(package_dir)
    stages = {
        "static": build_and_install(source_dir, build_root, package_dir, "static"),
        "shared": build_and_install(source_dir, build_root, package_dir, "shared"),
    }
    license_path = write_license(package_dir, source_dir)
    write_version_file(package_dir)
    write_metadata(package_dir, stages, source_dir, license_path)


if __name__ == "__main__":
    main()
