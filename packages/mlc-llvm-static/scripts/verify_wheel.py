#!/usr/bin/env python3
"""Exercise the installed wheel after relocating its SDK, including ORC JIT."""
from __future__ import annotations

import hashlib
import os
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

def run(command: list[str | Path], *, capture: bool = False) -> str:
    command = [str(item) for item in command]
    print("+ " + shlex.join(command), flush=True)
    result = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ""


def dynamic_sdk_dependencies(output: str) -> list[str]:
    """Read library basenames from ldd, otool, or dumpbin output."""
    pattern = re.compile(
        r"^(?:lib)?(?:LLVM[^/\\]*|zlib[^/\\]*|zstd[^/\\]*|z(?:\.\d+)*|"
        r"(?:xml2|edit|ffi|z3|curl|(?:cpp-)?httplib|pfm|icu[^/\\]*|iconv|tinfo|ncurses[^/\\]*|msdia)[^/\\]*)"
        r"\.(?:so(?:\.\d+)*|dylib|dll)$", re.IGNORECASE,
    )
    dependencies = []
    for line in output.splitlines():
        candidate = line.strip().split(" => ", 1)[0].split(" (", 1)[0]
        name = candidate.replace("\\", "/").rsplit("/", 1)[-1].rstrip(":")
        if pattern.fullmatch(name):
            dependencies.append(name)
    return dependencies


def exported_symbols(output: str, system: str) -> set[str]:
    """Read nm -D --format=posix, nm -gUj, or dumpbin /EXPORTS output."""
    if system == "Windows":
        return set(re.findall(r"^\s*\d+\s+[0-9A-Fa-f]+\s+[0-9A-Fa-f]+\s+(\S+)", output, re.MULTILINE))
    return {line.split()[0] for line in output.splitlines() if line.strip()}


def verify_linux_abi(path: Path) -> None:
    # Symbol ceilings from auditwheel's manylinux_2_28 policy for both release
    # architectures. Inspect linked consumers, not just archive filenames.
    if platform.system() != "Linux":
        return
    output = run(["readelf", "--version-info", path], capture=True)
    for namespace, maximum in (("GLIBC", (2, 28)), ("GLIBCXX", (3, 4, 24)),
                               ("CXXABI", (1, 3, 11)), ("GCC", (7, 0, 0))):
        versions = re.findall(r"\b" + namespace + r"_([0-9.]+)", output)
        for version in versions:
            if tuple(map(int, version.split("."))) > maximum:
                raise RuntimeError(f"{path.name} requires {namespace}_{version}, above manylinux_2_28")


def main() -> None:
    import mlc_llvm_static as sdk

    metadata = sdk.metadata()
    original = Path(sdk.get_prefix())
    if run([sdk.get_llvm_config(), "--version"], capture=True) != sdk.LLVM_VERSION:
        raise RuntimeError("The installed llvm-config launcher returned an incorrect version")
    if Path(run([sdk.get_llvm_config(), "--prefix"], capture=True)).resolve() != original.resolve():
        raise RuntimeError("The installed llvm-config launcher resolved a different SDK")
    for relative, record in metadata["files"].items():
        path = original / relative
        if not path.is_file():
            raise RuntimeError(f"Installed wheel is missing {relative}")
        checksum = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                checksum.update(chunk)
        digest = checksum.hexdigest()
        if digest != record["sha256"]:
            raise RuntimeError(f"Installed payload checksum mismatch: {relative}")
    for flag, expected in (("--prefix", sdk.get_prefix()), ("--cmake-dir", sdk.get_cmake_dir()),
                           ("--llvm-config", sdk.get_llvm_config())):
        if run([sys.executable, "-m", "mlc_llvm_static.config", flag], capture=True) != expected:
            raise RuntimeError(f"Configuration helper returned an incorrect {flag}")
    with tempfile.TemporaryDirectory(prefix="mlc-llvm-verify-") as temporary:
        root = Path(temporary)
        prefix = root / "relocated SDK with spaces"
        shutil.copytree(original, prefix)
        command = [sys.executable, prefix / "bin/llvm-config.py"]
        if any(path.is_file() and path.name not in ("llvm-config", "llvm-config.py")
               for path in (prefix / "bin").iterdir()):
            raise RuntimeError("SDK unexpectedly contains compiled LLVM tools")
        if run([*command, "--version"], capture=True) != sdk.LLVM_VERSION:
            raise RuntimeError("LLVM version mismatch")
        for flag, expected in (("--prefix", prefix), ("--includedir", prefix / "include"),
                               ("--libdir", prefix / "lib"), ("--cmakedir", prefix / "lib/cmake/llvm")):
            if Path(run([*command, flag], capture=True)).resolve() != expected.resolve():
                raise RuntimeError(f"llvm-config {flag} is not relocatable")
        system_libs = run([*command, "--link-static", "--system-libs"], capture=True)
        if str(original) in system_libs or any(token.startswith(("/private/", "/tmp/", "/project/")) for token in shlex.split(system_libs)):
            raise RuntimeError(f"llvm-config retained build-time system library paths: {system_libs}")
        for path in prefix.rglob("*"):
            if path.is_file() and (path.suffix in (".so", ".dll", ".dylib") or ".so." in path.name):
                raise RuntimeError(f"SDK unexpectedly contains a shared library: {path}")
        for path in (prefix / "lib" / "pkgconfig").glob("*.pc"):
            if "prefix=${pcfiledir}/../.." not in path.read_text(encoding="utf-8"):
                raise RuntimeError(f"pkg-config metadata is not relocatable: {path}")
        source = Path(__file__).resolve().parents[1] / "verify"
        for link_mode in ("cmake", "llvm-config"):
            build = root / link_mode
            run(["cmake", "-S", source, "-B", build, "-G", "Ninja",
                 "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_PREFIX_PATH={prefix}",
                 f"-DLLVM_DIR={prefix / 'lib/cmake/llvm'}", f"-DMLC_LLVM_EXPECTED_PREFIX={prefix}",
                 f"-DMLC_LLVM_USE_CONFIG_FLAGS={'ON' if link_mode == 'llvm-config' else 'OFF'}"])
            run(["cmake", "--build", build, "--parallel", "2"])
            library = next(path for path in build.rglob("*mlc_llvm_probe*")
                           if path.suffix in (".dll", ".so", ".dylib"))
            verify_linux_abi(library)
            if platform.system() == "Linux":
                dependencies = run(["ldd", library], capture=True)
            elif platform.system() == "Darwin":
                dependencies = run(["otool", "-L", library], capture=True)
            else:
                dependencies = run(["dumpbin", "/DEPENDENTS", library], capture=True)
            if dynamic_sdk_dependencies(dependencies):
                raise RuntimeError(f"Consumer links a dynamic SDK dependency:\n{dependencies}")
            system = platform.system()
            if system == "Linux":
                symbols = run(["nm", "-D", "--defined-only", "--format=posix", library], capture=True)
            elif system == "Darwin":
                symbols = run(["nm", "-gUj", library], capture=True)
            else:
                symbols = run(["dumpbin", "/EXPORTS", library], capture=True)
            expected = "_mlc_llvm_probe" if system == "Darwin" else "mlc_llvm_probe"
            allowed = {expected}
            if system == "Windows":
                # LLVM_ALWAYS_EXPORT in OrcTargetProcess/JITLoaderGDB.cpp
                # embeds /EXPORT directives in these static archive members.
                allowed.update({"__jit_debug_descriptor", "__jit_debug_register_code"})
            exports = exported_symbols(symbols, system)
            if expected not in exports or exports - allowed:
                raise RuntimeError(f"Consumer exposes unexpected symbols:\n{symbols}")
            # A child process releases the DLL before TemporaryDirectory cleanup on
            # Windows, where a loaded DLL cannot be deleted.
            run([sys.executable, "-c", """
import ctypes
import sys
probe = ctypes.CDLL(sys.argv[1])
probe.mlc_llvm_probe.restype = ctypes.c_int
result = probe.mlc_llvm_probe()
if result != 42:
    raise SystemExit(f"LLVM consumer returned {result}, expected 42")
            """, library])
    print(f"Verified LLVM {sdk.LLVM_VERSION}: {metadata['archive_count']} archives; targets: {metadata['targets']}")


if __name__ == "__main__":
    main()
