#!/usr/bin/env python3
"""Exercise the installed wheel after relocating its SDK, including ORC JIT."""
from __future__ import annotations

import ctypes
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

import mlc_llvm_static as sdk


def run(command: list[str | Path], *, capture: bool = False) -> str:
    command = [str(item) for item in command]
    print("+ " + shlex.join(command), flush=True)
    result = subprocess.run(command, check=True, text=True, stdout=subprocess.PIPE if capture else None)
    return result.stdout.strip() if capture else ""


def verify_linux_abi(path: Path) -> None:
    # Symbol ceilings from auditwheel's manylinux_2_28 policy for both release
    # architectures. Check both the packaged
    # llvm-config executable and a linked consumer, not just archive filenames.
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
    metadata = sdk.metadata()
    original = Path(sdk.get_prefix())
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
        executable = prefix / "bin" / Path(sdk.get_llvm_config()).name
        if sorted(path.name for path in (prefix / "bin").iterdir()) != [executable.name]:
            raise RuntimeError("SDK unexpectedly contains LLVM tools other than llvm-config")
        if run([executable, "--version"], capture=True) != sdk.LLVM_VERSION:
            raise RuntimeError("LLVM version mismatch")
        for flag, expected in (("--prefix", prefix), ("--includedir", prefix / "include"),
                               ("--libdir", prefix / "lib"), ("--cmakedir", prefix / "lib/cmake/llvm")):
            if Path(run([executable, flag], capture=True)).resolve() != expected.resolve():
                raise RuntimeError(f"llvm-config {flag} is not relocatable")
        system_libs = run([executable, "--link-static", "--system-libs"], capture=True)
        if str(original) in system_libs or any(token.startswith(("/private/", "/tmp/", "/project/")) for token in shlex.split(system_libs)):
            raise RuntimeError(f"llvm-config retained build-time system library paths: {system_libs}")
        for path in prefix.rglob("*"):
            if path.is_file() and (path.suffix in (".so", ".dll", ".dylib") or ".so." in path.name):
                raise RuntimeError(f"SDK unexpectedly contains a shared library: {path}")
        verify_linux_abi(executable)
        source = Path(__file__).resolve().parents[1] / "verify"
        build = root / "build"
        run(["cmake", "-S", source, "-B", build, "-G", "Ninja",
             "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_PREFIX_PATH={prefix}",
             f"-DLLVM_DIR={prefix / 'lib/cmake/llvm'}", f"-DMLC_LLVM_EXPECTED_PREFIX={prefix}"])
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
        if re.search(r"(?:lib)?(?:LLVM|zstd|zlib)[^\s]*\.(?:so|dylib|dll)", dependencies, re.IGNORECASE):
            raise RuntimeError(f"Consumer links a dynamic SDK dependency:\n{dependencies}")
        probe = ctypes.CDLL(str(library))
        probe.mlc_llvm_probe.restype = ctypes.c_int
        if probe.mlc_llvm_probe() != 42:
            raise RuntimeError("LLVM consumer did not generate and JIT-execute the expected result")
    print(f"Verified LLVM {sdk.LLVM_VERSION}: {metadata['archive_count']} archives; targets: {metadata['targets']}")


if __name__ == "__main__":
    main()
