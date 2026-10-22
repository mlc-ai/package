#!/usr/bin/env python3
"""Build a pinned LLVM SDK using upstream's distribution install targets."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path

LLVM_VERSION = "23.1.1"
DEFAULT_TARGETS = "Native"
SOURCES = {
    "llvm": {
        "version": LLVM_VERSION,
        "url": f"https://github.com/llvm/llvm-project/releases/download/llvmorg-{LLVM_VERSION}/llvm-project-{LLVM_VERSION}.src.tar.xz",
        "sha256": "ebe9be46fe8756d58c5b198ffad0fa2a766257add81a4dc52179bfacc7888ee6",
    },
    "zlib": {
        "version": "1.3.1",
        "url": "https://zlib.net/fossils/zlib-1.3.1.tar.gz",
        "sha256": "9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23",
    },
    "zstd": {
        "version": "1.5.7",
        "url": "https://github.com/facebook/zstd/releases/download/v1.5.7/zstd-1.5.7.tar.gz",
        "sha256": "eb33e51f49a15e023950cd7825ca74a4a2b43db8354825ac24fc1b7ee09e6fa3",
    },
}


def run(command: list[str | Path], *, capture: bool = False) -> str:
    command = [str(part) for part in command]
    print("+ " + shlex.join(command), flush=True)
    result = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_tree(name: str, work: Path) -> Path:
    override = os.environ.get(f"MLC_LLVM_STATIC_{name.upper()}_SOURCE_DIR")
    if override:
        path = Path(override).resolve()
        cmake_file = {"llvm": "llvm/CMakeLists.txt", "zstd": "build/cmake/CMakeLists.txt"}.get(name, "CMakeLists.txt")
        if not (path / cmake_file).is_file():
            raise RuntimeError(f"Invalid {name} source tree: {path}")
        return path
    spec = SOURCES[name]
    cache = Path(os.environ.get("MLC_LLVM_STATIC_SOURCE_CACHE", str(work / "sources"))).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    filename = spec["url"].rsplit("/", 1)[1]
    archive = cache / filename
    if not archive.is_file() or sha256(archive) != spec["sha256"]:
        temporary = archive.with_name(filename + ".part")
        with urllib.request.urlopen(spec["url"], timeout=120) as response, temporary.open("wb") as stream:
            shutil.copyfileobj(response, stream)
        if sha256(temporary) != spec["sha256"]:
            temporary.unlink()
            raise RuntimeError(f"Source checksum mismatch: {filename}")
        temporary.replace(archive)
    destination = work / "sources" / name
    stamp = destination / ".mlc-source-sha256"
    if stamp.is_file() and stamp.read_text() == spec["sha256"]:
        return destination
    temporary = work / "sources" / f"extract-{name}"
    if temporary.exists():
        shutil.rmtree(temporary)
    temporary.mkdir(parents=True)
    # data_filter rejects escaping paths, links, and special files before extraction.
    if not hasattr(tarfile, "data_filter"):
        raise RuntimeError("Source extraction requires a Python with tarfile.data_filter (3.12+ or a maintained 3.10/3.11)")
    with tarfile.open(archive) as stream:
        stream.extractall(temporary, filter="data")
    roots = list(temporary.iterdir())
    if len(roots) != 1 or not roots[0].is_dir():
        raise RuntimeError(f"Expected one source directory in {archive}")
    if destination.exists():
        shutil.rmtree(destination)
    roots[0].replace(destination)
    temporary.rmdir()
    stamp.write_text(spec["sha256"])
    return destination


def configure(source: Path, build: Path, prefix: Path, options: list[str]) -> None:
    command: list[str | Path] = [
        "cmake", "-S", source, "-B", build, "-G", "Ninja",
        "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_INSTALL_PREFIX={prefix}",
        "-DCMAKE_INSTALL_LIBDIR=lib", "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
        "-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL",
    ]
    deployment = os.environ.get("MACOSX_DEPLOYMENT_TARGET")
    if platform.system() == "Darwin" and deployment:
        command.append(f"-DCMAKE_OSX_DEPLOYMENT_TARGET={deployment}")
    run(command + options)


def install(build: Path, target: str = "install") -> None:
    run(["cmake", "--build", build, "--target", target, "--parallel",
         os.environ.get("CMAKE_BUILD_PARALLEL_LEVEL", "2")])


def build_dependencies(work: Path, prefix: Path) -> None:
    source = source_tree("zlib", work)
    build = work / "build-zlib"
    configure(source, build, prefix, ["-DZLIB_BUILD_EXAMPLES=OFF"])
    # zlib 1.3.1 always defines a shared target. Install only the static target
    # and its public headers; no unused DLL/dylib is carried into the SDK.
    run(["cmake", "--build", build, "--target", "zlibstatic"])
    (prefix / "include").mkdir(parents=True, exist_ok=True)
    (prefix / "lib").mkdir(parents=True, exist_ok=True)
    for header in (source / "zlib.h", build / "zconf.h"):
        shutil.copy2(header, prefix / "include" / header.name)
    candidates = [build / "libz.a", build / "zlibstatic.lib", build / "z.lib"]
    library = next((path for path in candidates if path.is_file()), None)
    if library is None:
        raise RuntimeError("zlib static archive was not built")
    shutil.copy2(library, prefix / "lib" / library.name)
    source = source_tree("zstd", work)
    build = work / "build-zstd"
    configure(source / "build" / "cmake", build, prefix, [
        "-DZSTD_BUILD_PROGRAMS=OFF", "-DZSTD_BUILD_TESTS=OFF",
        "-DZSTD_BUILD_SHARED=OFF", "-DZSTD_BUILD_STATIC=ON",
        "-DZSTD_MULTITHREAD_SUPPORT=OFF",
    ])
    install(build)


def build_llvm(source: Path, work: Path, prefix: Path) -> None:
    build = work / "build-llvm"
    configure(source / "llvm", build, prefix, [
        f"-DCMAKE_PREFIX_PATH={prefix}", f"-DLLVM_TARGETS_TO_BUILD={os.environ.get('MLC_LLVM_STATIC_TARGETS', DEFAULT_TARGETS)}",
        "-DLLVM_DISTRIBUTION_COMPONENTS=llvm-headers;llvm-libraries;cmake-exports;llvm-config",
        # Define tool install targets so llvm-config can be a distribution
        # component; install-distribution builds only the selected components.
        "-DLLVM_BUILD_TOOLS=ON", "-DLLVM_BUILD_UTILS=OFF",
        "-DLLVM_INCLUDE_TESTS=OFF", "-DLLVM_INCLUDE_BENCHMARKS=OFF",
        "-DLLVM_INCLUDE_EXAMPLES=OFF", "-DLLVM_INCLUDE_DOCS=OFF",
        "-DLLVM_TOOL_LTO_BUILD=OFF", "-DLLVM_TOOL_REMARKS_SHLIB_BUILD=OFF",
        "-DBUILD_SHARED_LIBS=OFF", "-DLLVM_BUILD_LLVM_DYLIB=OFF",
        "-DLLVM_LINK_LLVM_DYLIB=OFF", "-DLLVM_ENABLE_PIC=ON",
        "-DLLVM_ENABLE_LTO=OFF", "-DLLVM_ENABLE_ASSERTIONS=OFF",
        "-DLLVM_ABI_BREAKING_CHECKS=FORCE_OFF", "-DLLVM_ENABLE_RTTI=ON",
        "-DLLVM_ENABLE_EH=OFF", "-DLLVM_USE_CRT_RELEASE=MD",
        "-DLLVM_ENABLE_ZLIB=FORCE_ON", "-DZLIB_USE_STATIC_LIBS=ON",
        "-DLLVM_ENABLE_ZSTD=FORCE_ON", "-DLLVM_USE_STATIC_ZSTD=ON", "-DLLVM_ENABLE_LIBXML2=OFF",
        "-DLLVM_ENABLE_LIBEDIT=OFF", "-DLLVM_ENABLE_FFI=OFF",
        "-DLLVM_ENABLE_Z3_SOLVER=OFF", "-DLLVM_ENABLE_CURL=OFF",
        "-DLLVM_ENABLE_HTTPLIB=OFF",
    ])
    # Upstream llvm-config embeds the absolute zstd archive location in
    # LLVM_SYSTEM_LIBS when zstd is static. Emit a library name instead, using
    # the SDK's --ldflags search path, so a relocated SDK cannot retain it.
    variables = build / "tools" / "llvm-config" / "BuildVariables.inc"
    text = variables.read_text(encoding="utf-8")
    line = re.search(r'^#define LLVM_SYSTEM_LIBS .*$', text, re.MULTILINE)
    if line is None:
        raise RuntimeError("Cannot find LLVM_SYSTEM_LIBS in llvm-config's build variables")
    normalized = line.group()
    for library in (prefix / "lib").iterdir():
        if library.suffix not in (".a", ".lib"):
            continue
        flag = library.name if os.name == "nt" else "-l" + library.stem.removeprefix("lib")
        normalized = normalized.replace(library.as_posix(), flag)
    variables.write_text(text[:line.start()] + normalized + text[line.end():], encoding="utf-8")
    install(build, "install-distribution")
    if platform.system() == "Linux":
        triple = run([prefix / "bin" / "llvm-config", "--host-target"], capture=True)
        build = work / "build-orc"
        configure(source / "compiler-rt", build, prefix / "lib" / "clang" / "23", [
            f"-DLLVM_CMAKE_DIR={prefix / 'lib' / 'cmake' / 'llvm'}",
            f"-DCMAKE_C_COMPILER_TARGET={triple}", f"-DCMAKE_CXX_COMPILER_TARGET={triple}",
            "-DCOMPILER_RT_DEFAULT_TARGET_ONLY=ON", "-DCOMPILER_RT_INCLUDE_TESTS=OFF",
            "-DCOMPILER_RT_BUILD_BUILTINS=OFF", "-DCOMPILER_RT_BUILD_SANITIZERS=OFF",
            "-DCOMPILER_RT_BUILD_XRAY=OFF", "-DCOMPILER_RT_BUILD_LIBFUZZER=OFF",
            "-DCOMPILER_RT_BUILD_PROFILE=OFF", "-DCOMPILER_RT_BUILD_CTX_PROFILE=OFF",
            "-DCOMPILER_RT_BUILD_MEMPROF=OFF", "-DCOMPILER_RT_BUILD_ORC=ON",
            "-DCOMPILER_RT_BUILD_GWP_ASAN=OFF", "-DCOMPILER_RT_BUILD_SCUDO_STANDALONE=OFF",
        ])
        install(build, "install-orc")


def validate_native_archive(path: Path) -> None:
    with path.open("rb") as stream:
        if stream.read(8) != b"!<arch>\n":
            raise RuntimeError(f"Expected a regular static archive: {path}")
        while header := stream.read(60):
            if len(header) != 60 or header[58:] != b"`\n":
                raise RuntimeError(f"Invalid archive member header: {path}")
            size = int(header[48:58].strip())
            start = stream.tell()
            if header[:16].startswith(b"#1/"):
                stream.seek(int(header[:16][3:].strip()), 1)
            if stream.read(4) in (b"BC\xc0\xde", b"\xde\xc0\x17\x0b"):
                raise RuntimeError(f"LTO bitcode is not allowed in the portable SDK: {path}")
            stream.seek(start + size + size % 2)


def validate_prefix(prefix: Path) -> dict:
    executable = prefix / "bin" / ("llvm-config.exe" if os.name == "nt" else "llvm-config")
    for path in (executable, prefix / "include" / "llvm" / "IR" / "Module.h",
                 prefix / "lib" / "cmake" / "llvm" / "LLVMConfig.cmake"):
        if not path.is_file():
            raise RuntimeError(f"Required SDK artifact missing: {path}")
    tools = sorted(path.name for path in (prefix / "bin").iterdir())
    if tools != [executable.name]:
        raise RuntimeError(f"Only llvm-config may be installed in bin/: {tools}")
    archives = []
    for path in prefix.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix in (".so", ".dylib", ".dll") or ".so." in path.name:
            raise RuntimeError(f"Unexpected shared library: {path}")
        if path.suffix in (".a", ".lib"):
            validate_native_archive(path)
            archives.append(path)
    if not any(path.name in ("libLLVMCore.a", "LLVMCore.lib") for path in archives):
        raise RuntimeError("LLVMCore static archive is missing")
    version = run([executable, "--version"], capture=True)
    if version != LLVM_VERSION:
        raise RuntimeError(f"Expected LLVM {LLVM_VERSION}, found {version}")
    reported = Path(run([executable, "--prefix"], capture=True)).resolve()
    if reported != prefix.resolve():
        raise RuntimeError(f"llvm-config is not relocatable: {reported} != {prefix}")
    if platform.system() == "Linux" and not list(prefix.glob("lib/clang/*/lib/**/liborc_rt*.a")):
        raise RuntimeError("Linux SDK is missing the ORC runtime archive")
    return {
        "llvm_version": version,
        "targets": run([executable, "--targets-built"], capture=True).split(),
        "archive_count": len(archives),
    }


def relocate_pkgconfig(prefix: Path) -> None:
    for path in (prefix / "lib" / "pkgconfig").glob("*.pc"):
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"^prefix=.*$", "prefix=${pcfiledir}/../..", text, flags=re.MULTILINE)
        path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    args = parser.parse_args()
    output, work = args.output.resolve(), args.work_root.resolve()
    prefix = output / "static"
    output.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    supplied = os.environ.get("MLC_LLVM_STATIC_PREFIX")
    if supplied:
        supplied = Path(supplied).resolve()
        package = supplied.parent
        validate_prefix(supplied)
        if supplied != prefix:
            if prefix.exists():
                shutil.rmtree(prefix)
            if (output / "licenses").exists():
                shutil.rmtree(output / "licenses")
            shutil.copytree(supplied, prefix, dirs_exist_ok=True)
            shutil.copytree(package / "licenses", output / "licenses", dirs_exist_ok=True)
            shutil.copy2(package / "staticlib.json", output / "staticlib.json")
        relocate_pkgconfig(prefix)
        manifest_path = output / "staticlib.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for path in (prefix / "lib" / "pkgconfig").glob("*.pc"):
            manifest["files"][path.relative_to(prefix).as_posix()] = {
                "sha256": sha256(path), "size": path.stat().st_size,
            }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        validate_prefix(prefix)
        return
    if os.environ.get("MLC_LLVM_STATIC_ALLOW_SOURCE_BUILD") != "1":
        raise RuntimeError("Set MLC_LLVM_STATIC_ALLOW_SOURCE_BUILD=1 to build LLVM explicitly")
    if prefix.exists():
        shutil.rmtree(prefix)
    build_dependencies(work, prefix)
    source = source_tree("llvm", work)
    build_llvm(source, work, prefix)
    relocate_pkgconfig(prefix)
    details = validate_prefix(prefix)
    licenses = output / "licenses"
    licenses.mkdir(exist_ok=True)
    for name, source_license in (
        ("LLVM.txt", source / "llvm" / "LICENSE.TXT"),
        ("compiler-rt.txt", source / "compiler-rt" / "LICENSE.TXT"),
        ("zlib.txt", source_tree("zlib", work) / "README"),
        ("zstd.txt", source_tree("zstd", work) / "LICENSE"),
    ):
        shutil.copy2(source_license, licenses / name)
    details.update({
        "schema_version": 1, "sources": SOURCES,
        "source_overrides": [name for name in SOURCES if os.environ.get(f"MLC_LLVM_STATIC_{name.upper()}_SOURCE_DIR")],
        "system": platform.system(), "machine": platform.machine(),
        "build": {"type": "Release", "pic": True, "lto": False,
                  "assertions": False, "rtti": True, "exceptions": False},
        "files": {str(path.relative_to(prefix)).replace(os.sep, "/"): {
            "sha256": sha256(path), "size": path.stat().st_size,
        } for path in sorted(prefix.rglob("*")) if path.is_file()},
    })
    (output / "staticlib.json").write_text(json.dumps(details, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
