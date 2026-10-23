#!/usr/bin/env python3
"""Install, exercise, and remove the add-on without changing base-owned files."""
from __future__ import annotations

import argparse
import importlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile


def run(command, *, env=None):
    subprocess.run([str(value) for value in command], check=True, env=env)


def targets(profile: str):
    import mlc_llvm_static as sdk
    env = dict(os.environ, MLC_LLVM_STATIC_PROFILE=profile)
    prefix = sdk.get_prefix()
    from mlc_llvm_static._llvm_config import Configuration
    config = Configuration(Path(prefix), profile)
    triples = [config.base["host_target"]] if profile == "native" else [
        "x86_64-unknown-linux-gnu", "aarch64-unknown-linux-gnu",
        "riscv64-unknown-linux-gnu", "wasm32-unknown-unknown",
        "x86_64-pc-windows-msvc", "aarch64-apple-macosx14.0.0"]
    with tempfile.TemporaryDirectory(prefix="llvm-cross-profile-") as directory:
        build = Path(directory)
        run(["cmake", "-S", Path(__file__).resolve().parents[1] / "verify/targets", "-B", build,
             "-G", "Ninja", "-DCMAKE_BUILD_TYPE=Release", f"-DCMAKE_PREFIX_PATH={prefix}",
             f"-DLLVM_DIR={sdk.get_cmake_dir()}", f"-DMLC_LLVM_STATIC_PROFILE={profile}"], env=env)
        run(["cmake", "--build", build, "--parallel", "2"], env=env)
        program = build / ("mlc_llvm_targets.exe" if os.name == "nt" else "mlc_llvm_targets")
        from verify_wheel import verify_linux_abi
        verify_linux_abi(program)
        run([program, *triples], env=env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wheelhouse", type=Path)
    args = parser.parse_args()
    wheels = sorted(args.wheelhouse.resolve().glob("*.whl"))
    base = next(wheel for wheel in wheels if wheel.name.startswith("mlc_llvm_static-"))
    extra = next(wheel for wheel in wheels if wheel.name.startswith("mlc_llvm_static_extra_targets-"))
    with zipfile.ZipFile(base) as first, zipfile.ZipFile(extra) as second:
        overlap = {name for name in first.namelist() if name.startswith("mlc_llvm_static/")} & set(second.namelist())
        if overlap:
            raise RuntimeError(f"Overlapping wheel file ownership: {overlap}")
    run([sys.executable, "-m", "pip", "uninstall", "-y", "mlc-llvm-static-extra-targets"])
    run([sys.executable, "-m", "pip", "install", "--no-deps", "--force-reinstall", base])
    importlib.invalidate_caches()
    import mlc_llvm_static as sdk
    if sdk.metadata()["profile"] != "native":
        raise RuntimeError("Base-only installation did not select the native profile")
    verifier = Path(__file__).with_name("verify_wheel.py")
    run([sys.executable, verifier])
    targets("native")
    run([sys.executable, "-m", "pip", "install", "--no-deps", extra])
    run([sys.executable, "-m", "pip", "check"])
    metadata = sdk.metadata()
    expected_targets = set(metadata["profiles"]["all"]["components"]["all-targets"]["requires"])
    if metadata["profile"] != "all" or {target.lower() for target in metadata["targets"]} != expected_targets:
        raise RuntimeError("The add-on did not enable all standard LLVM targets")
    run([sys.executable, verifier])
    targets("all")
    # A consumer may explicitly choose Native even when all archives exist.
    targets("native")
    run([sys.executable, "-m", "pip", "uninstall", "-y", "mlc-llvm-static-extra-targets"])
    if sdk.metadata()["profile"] != "native":
        raise RuntimeError("Removing the add-on did not restore the native profile")
    run([sys.executable, verifier])
    print("Verified Native, All, explicit Native, and add-on uninstall", flush=True)


if __name__ == "__main__":
    main()
