#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import platform
import runpy
import shlex
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE_DIR = PROJECT_ROOT / "src" / "mlc_doxygen_bin"

# version.py at the package root is the single source of truth for the pinned
# Doxygen release; a version bump edits only that file.
_VERSION = runpy.run_path(str(PROJECT_ROOT / "version.py"))
PACKAGE_VERSION: str = _VERSION["__version__"]
DOXYGEN_VERSION: str = _VERSION["DOXYGEN_VERSION"]
DOXYGEN_TAG: str = _VERSION["DOXYGEN_TAG"]
DOXYGEN_ARCHIVE_SHA256: str = _VERSION["DOXYGEN_ARCHIVE_SHA256"]
DOXYGEN_ARCHIVE_URL = (
    "https://github.com/doxygen/doxygen/releases/download/"
    f"{DOXYGEN_TAG}/doxygen-{DOXYGEN_VERSION}.src.tar.gz"
)

# The outer scikit-build-core project forwards its CMake executable so the
# inner Doxygen build uses the same CMake rather than whatever `cmake` happens
# to be first on PATH.
CMAKE = os.environ.get("MLC_DOXYGEN_BIN_CMAKE_COMMAND") or "cmake"

# Doxygen's bundled Windows iconv (deps/iconv_winbuild) only ships x86/x64
# libraries, so Windows ARM64 builds link a pinned win-iconv (public domain,
# Win32-API based) compiled for the target instead. This is a build-tool pin,
# independent of the Doxygen version in version.py.
WIN_ICONV_VERSION = "0.0.10"
WIN_ICONV_ARCHIVE_URL = f"https://github.com/win-iconv/win-iconv/archive/refs/tags/v{WIN_ICONV_VERSION}.tar.gz"
WIN_ICONV_ARCHIVE_SHA256 = "58493387c7c9c70d61e711ec2feec5db0a59d164556642d2b427dde4ef756bc1"


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


def verify_archive(path: Path, expected_sha256: str) -> bool:
    if not path.is_file():
        return False
    actual = sha256(path)
    if actual == expected_sha256:
        return True
    print(f"Discarding {path}: expected {expected_sha256}, got {actual}", flush=True)
    path.unlink()
    return False


def download_archive(url: str, expected_sha256: str, archive: Path) -> Path:
    if verify_archive(archive, expected_sha256):
        return archive

    archive.parent.mkdir(parents=True, exist_ok=True)
    tmp = archive.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    print(f"Downloading {url}", flush=True)
    with urllib.request.urlopen(url, timeout=60) as response, tmp.open("wb") as dest:
        shutil.copyfileobj(response, dest)
    actual = sha256(tmp)
    if actual != expected_sha256:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"SHA-256 mismatch for {url}: expected {expected_sha256}, got {actual}")
    tmp.replace(archive)
    return archive


def safe_extract(archive: Path, source_dir: Path) -> Path:
    if (source_dir / "CMakeLists.txt").is_file():
        return source_dir

    source_root = source_dir.parent
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
        extract_kwargs = {"filter": "data"} if hasattr(tarfile, "data_filter") else {}
        tar.extractall(extract_dir, **extract_kwargs)

    roots = [path for path in extract_dir.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise RuntimeError(f"Expected one root directory in {archive}, found {roots}")

    if source_dir.exists():
        shutil.rmtree(source_dir)
    shutil.move(str(roots[0]), source_dir)
    shutil.rmtree(extract_dir)
    return source_dir


def get_source_tree(work_root: Path) -> Path:
    source_override = os.environ.get("MLC_DOXYGEN_BIN_SOURCE_DIR")
    if source_override:
        source_dir = Path(source_override).resolve()
        if not (source_dir / "CMakeLists.txt").is_file():
            raise RuntimeError(f"MLC_DOXYGEN_BIN_SOURCE_DIR is not a Doxygen source tree: {source_dir}")
        return source_dir

    archive = download_archive(
        DOXYGEN_ARCHIVE_URL, DOXYGEN_ARCHIVE_SHA256, work_root / f"doxygen-{DOXYGEN_VERSION}.src.tar.gz"
    )
    return safe_extract(archive, work_root / "src" / f"doxygen-{DOXYGEN_VERSION}")


def find_program(env_name: str, candidates: tuple[str, ...]) -> str | None:
    configured = os.environ.get(env_name)
    if configured:
        return configured
    if platform.system() == "Darwin":
        brew = shutil.which("brew")
        if brew:
            for candidate in candidates:
                result = subprocess.run(
                    [brew, "--prefix", "--installed", candidate],
                    check=False,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                if result.returncode == 0:
                    path = Path(result.stdout.strip()) / "bin" / candidate
                    if path.is_file():
                        return str(path)
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    return None


# platform.machine() of the (native) build interpreter -> Visual Studio -A value.
_WINDOWS_GENERATOR_PLATFORMS = {"AMD64": "x64", "X86_64": "x64", "ARM64": "ARM64", "AARCH64": "ARM64", "X86": "Win32"}


def cmake_generator_platform(generator: str | None) -> str | None:
    """Return the Visual Studio ``-A`` platform matching the wheel being built.

    The outer scikit-build-core configure forwards its CMAKE_GENERATOR_PLATFORM
    (derived from the target wheel platform, e.g. ARM64 for win_arm64). Without
    it, fall back to the build interpreter's platform.machine() so a native
    ARM64 build never silently produces an x64 executable.
    """
    if platform.system() != "Windows":
        return None
    if generator and not generator.startswith("Visual Studio"):
        return None
    explicit = os.environ.get("MLC_DOXYGEN_BIN_CMAKE_GENERATOR_PLATFORM")
    if explicit:
        return explicit
    return _WINDOWS_GENERATOR_PLATFORMS.get(platform.machine().upper())


def cmake_generator_args() -> list[str]:
    args: list[str] = []
    generator = os.environ.get("MLC_DOXYGEN_BIN_CMAKE_GENERATOR")
    if generator:
        args.extend(["-G", generator])
    elif platform.system() != "Windows" and shutil.which("ninja"):
        args.extend(["-G", "Ninja"])
    generator_platform = cmake_generator_platform(generator or os.environ.get("CMAKE_GENERATOR"))
    if generator_platform:
        args.extend(["-A", generator_platform])
    return args


def windows_target_arch() -> str | None:
    """Return the Windows target architecture (x64, ARM64, ...) or None."""
    if platform.system() != "Windows":
        return None
    return os.environ.get("MLC_DOXYGEN_BIN_CMAKE_GENERATOR_PLATFORM") or _WINDOWS_GENERATOR_PLATFORMS.get(
        platform.machine().upper()
    )


def build_win_iconv(work_root: Path) -> Path:
    """Build a static win-iconv for the target and return its install prefix."""
    archive = download_archive(
        WIN_ICONV_ARCHIVE_URL, WIN_ICONV_ARCHIVE_SHA256, work_root / f"win-iconv-{WIN_ICONV_VERSION}.tar.gz"
    )
    source_dir = safe_extract(archive, work_root / "src" / f"win-iconv-{WIN_ICONV_VERSION}")
    build_dir = work_root / "build-win-iconv"
    prefix = work_root / "win-iconv"
    for path in (build_dir, prefix):
        if path.exists():
            shutil.rmtree(path)
    build_type = os.environ.get("MLC_DOXYGEN_BIN_BUILD_TYPE", "Release")
    run([
        CMAKE, "-S", source_dir, "-B", build_dir, *cmake_generator_args(),
        f"-DCMAKE_BUILD_TYPE={build_type}",
        f"-DCMAKE_INSTALL_PREFIX={prefix}",
        # Only the static library: a shared iconv.lib import library in the
        # same prefix would be preferred by FindIconv and add a DLL dependency.
        "-DWIN_ICONV_BUILD_STATIC=ON",
        "-DWIN_ICONV_BUILD_SHARED=OFF",
        "-DWIN_ICONV_BUILD_EXECUTABLE=OFF",
        "-DWIN_ICONV_BUILD_TEST=OFF",
        # Match Doxygen's win_static=ON (/MT) runtime.
        "-DCMAKE_POLICY_DEFAULT_CMP0091=NEW",
        "-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded$<$<CONFIG:Debug>:Debug>",
    ])
    run([CMAKE, "--build", build_dir, "--config", build_type, "--target", "install"])
    return prefix


def cmake_configure_command(source_dir: Path, build_dir: Path, stage_dir: Path,
                            iconv_dir: Path | None = None) -> list[str | Path]:
    build_type = os.environ.get("MLC_DOXYGEN_BIN_BUILD_TYPE", "Release")
    cmd: list[str | Path] = [
        CMAKE,
        "-S",
        source_dir,
        "-B",
        build_dir,
    ]

    cmd.extend(cmake_generator_args())

    cmd.extend(
        [
            f"-DCMAKE_BUILD_TYPE={build_type}",
            f"-DCMAKE_INSTALL_PREFIX={stage_dir}",
            "-Dbuild_wizard=OFF",
            "-Dbuild_app=OFF",
            "-Dbuild_parse=OFF",
            "-Dbuild_search=OFF",
            "-Dbuild_doc=OFF",
            "-Dbuild_doc_chm=OFF",
            "-Duse_libclang=OFF",
            "-Duse_sys_spdlog=OFF",
            "-Duse_sys_fmt=OFF",
            "-Duse_sys_sqlite3=OFF",
        ]
    )

    flex = find_program("FLEX_EXECUTABLE", ("flex", "win_flex", "win_flex.exe"))
    if flex:
        cmd.append(f"-DFLEX_EXECUTABLE={flex}")
    bison = find_program("BISON_EXECUTABLE", ("bison", "win_bison", "win_bison.exe"))
    if bison:
        cmd.append(f"-DBISON_EXECUTABLE={bison}")

    if platform.system() == "Darwin":
        deployment_target = os.environ.get("MACOSX_DEPLOYMENT_TARGET")
        if deployment_target:
            cmd.append(f"-DMACOS_VERSION_MIN={deployment_target}")
            cmd.append(f"-DCMAKE_OSX_DEPLOYMENT_TARGET={deployment_target}")

    if platform.system() == "Windows":
        cmd.append("-Dwin_static=ON")
    if iconv_dir is not None:
        cmd.append(f"-DICONV_DIR={iconv_dir}")

    extra_args = os.environ.get("MLC_DOXYGEN_BIN_EXTRA_CMAKE_ARGS")
    if extra_args:
        cmd.extend(shlex.split(extra_args))

    return cmd


def executable_name() -> str:
    return "doxygen.exe" if platform.system() == "Windows" else "doxygen"


def validate_stage(stage_dir: Path) -> Path:
    executable = stage_dir / "bin" / executable_name()
    if not executable.is_file():
        raise RuntimeError(f"Doxygen install tree is missing executable: {executable}")
    return executable


def clean_package_outputs(package_dir: Path) -> None:
    for name in ("bin", "licenses"):
        shutil.rmtree(package_dir / name, ignore_errors=True)
    for name in ("doxygen.json", "_version.py"):
        (package_dir / name).unlink(missing_ok=True)


def copy_runtime(stage_dir: Path, package_dir: Path) -> Path:
    source_bin = stage_dir / "bin"
    dest_bin = package_dir / "bin"
    shutil.copytree(source_bin, dest_bin)
    executable = dest_bin / executable_name()
    if platform.system() != "Windows":
        executable.chmod(executable.stat().st_mode | 0o755)
    return executable


def rel(package_dir: Path, path: Path) -> str:
    return path.relative_to(package_dir).as_posix()


def write_version_module(package_dir: Path) -> None:
    """Generate the runtime ``mlc_doxygen_bin/_version.py`` from ``version.py``."""
    (package_dir / "_version.py").write_text(
        (
            "# Generated by scripts/prepare_doxygen.py from version.py; do not edit.\n"
            f"__version__ = {PACKAGE_VERSION!r}\n"
            f"DOXYGEN_VERSION = {DOXYGEN_VERSION!r}\n"
            f"DOXYGEN_TAG = {DOXYGEN_TAG!r}\n"
        ),
        encoding="utf-8",
    )


def write_license(package_dir: Path, source_dir: Path) -> str:
    licenses_dir = package_dir / "licenses"
    licenses_dir.mkdir(parents=True, exist_ok=True)
    source_license = source_dir / "LICENSE"
    dest = licenses_dir / "LICENSE-Doxygen.txt"
    if source_license.is_file():
        shutil.copy2(source_license, dest)
    else:
        dest.write_text("See https://github.com/doxygen/doxygen/blob/master/LICENSE\n", encoding="utf-8")
    return rel(package_dir, dest)


def write_metadata(package_dir: Path, executable: Path, source_dir: Path, license_path: str) -> None:
    metadata = {
        "name": "doxygen",
        "doxygen_version": DOXYGEN_VERSION,
        "doxygen_tag": DOXYGEN_TAG,
        "source_repository": "https://github.com/doxygen/doxygen",
        "source_archive_url": DOXYGEN_ARCHIVE_URL,
        "source_archive_sha256": DOXYGEN_ARCHIVE_SHA256,
        "source_dir": str(source_dir),
        "package_version": PACKAGE_VERSION,
        "executable": rel(package_dir, executable),
        "license": license_path,
        "features": {
            "cli": True,
            "doxywizard": False,
            "search_tools": False,
            "libclang": False,
        },
        "platform": platform.platform(),
        "python": sys.version.split()[0],
    }
    (package_dir / "doxygen.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def build_and_install(source_dir: Path, work_root: Path) -> Path:
    build_dir = work_root / "build"
    stage_dir = work_root / "stage"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if stage_dir.exists():
        shutil.rmtree(stage_dir)

    iconv_dir = None
    extra_args = os.environ.get("MLC_DOXYGEN_BIN_EXTRA_CMAKE_ARGS", "")
    if windows_target_arch() == "ARM64" and "-DICONV_DIR=" not in extra_args:
        iconv_dir = build_win_iconv(work_root)

    run(cmake_configure_command(source_dir, build_dir, stage_dir, iconv_dir))

    build_type = os.environ.get("MLC_DOXYGEN_BIN_BUILD_TYPE", "Release")
    build_cmd: list[str | Path] = [
        CMAKE,
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
    validate_stage(stage_dir)
    return stage_dir


def main() -> None:
    package_dir = Path(os.environ.get("MLC_DOXYGEN_BIN_PACKAGE_DIR", DEFAULT_PACKAGE_DIR)).resolve()
    build_root = Path(
        os.environ.get("MLC_DOXYGEN_BIN_BUILD_ROOT", PROJECT_ROOT / "build" / f"doxygen-v{DOXYGEN_VERSION}")
    ).resolve()
    package_dir.mkdir(parents=True, exist_ok=True)
    build_root.mkdir(parents=True, exist_ok=True)

    source_dir = get_source_tree(build_root)
    clean_package_outputs(package_dir)
    stage_dir = build_and_install(source_dir, build_root)
    executable = copy_runtime(stage_dir, package_dir)
    license_path = write_license(package_dir, source_dir)
    write_version_module(package_dir)
    write_metadata(package_dir, executable, source_dir, license_path)


if __name__ == "__main__":
    main()
