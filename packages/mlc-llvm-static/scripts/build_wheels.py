#!/usr/bin/env python3
"""Build one All-target SDK and package its native and extra-targets wheels."""
from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import zipfile

import prepare_llvm
from split_sdk import split_sdk

PROJECT = Path(__file__).resolve().parents[1]


def run(command, *, env=None):
    subprocess.run([str(value) for value in command], check=True, env=env)


def version() -> str:
    return runpy.run_path(str(PROJECT / "src/mlc_llvm_static/_version.py"))["__version__"]


def stage(native: Path, work: Path) -> Path | None:
    supplied = os.environ.get("MLC_LLVM_STATIC_PREFIX")
    if supplied and (Path(supplied) / "share/mlc-llvm-static/base.json").is_file():
        # Repackaging a prepared native payload never compiles LLVM.
        run([sys.executable, PROJECT / "scripts/prepare_llvm.py", "--output", native, "--work-root", work])
        return None
    raw = work / "raw/mlc_llvm_static"
    source_work = Path(os.environ.get("MLC_LLVM_STATIC_BUILD_WORK", str(work / "source-build")))
    run([sys.executable, PROJECT / "scripts/prepare_llvm.py", "--output", raw, "--work-root", source_work])
    if not (raw / "static/share/mlc-llvm-static/build.json").is_file():
        raise RuntimeError("A cached/supplied SDK must include the All-target build graph and split CMake exports")
    if os.environ.get("MLC_LLVM_STATIC_USE_CACHE") == "1":
        cache = PROJECT / ".sdk-cache/all-sdk.zip"
        if not cache.exists():
            cache.parent.mkdir(exist_ok=True)
            temporary = cache.with_suffix(".part")
            with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for path in sorted(raw.rglob("*")):
                    if path.is_file():
                        archive.write(path, "mlc_llvm_static/" + path.relative_to(raw).as_posix())
            temporary.replace(cache)
    extra = native.parent / "extra/mlc_llvm_static"
    split_sdk(raw, native, extra, version(), PROJECT / "src/mlc_llvm_static/_llvm_config.py")
    # Upstream's executable remains in the raw build/cache, never either wheel.
    # Verify every installed component's dependency order against that build.
    sys.path.insert(0, str(PROJECT / "src"))
    from mlc_llvm_static._llvm_config import Configuration
    config = Configuration(native / "static", "native")
    executable = raw / "static/bin" / ("llvm-config.exe" if os.name == "nt" else "llvm-config")
    for profile in ("native", "all"):
        reference = copy.copy(config)
        # The raw prefix contains every archive; this comparison does not need
        # to mutate either installed payload or install the add-on prematurely.
        reference.prefix = raw / "static"
        reference.profile = profile
        reference.components = config.base["profiles"][profile]["components"]
        reference.libraries = config.base["profiles"][profile]["libraries"]
        count = 0
        for component in sorted(reference.components):
            if profile == "native" and component in ("all", "all-targets"):
                continue
            expected = subprocess.check_output([str(executable), "--link-static", "--libnames", component], text=True).strip()
            actual = reference.query(["--link-static", "--libnames", component]).strip()
            if actual != expected:
                raise RuntimeError(f"Python llvm-config differs from upstream for {profile}/{component}: {actual!r} != {expected!r}")
            count += 1
        print(f"Compared {count} {profile} component queries with upstream llvm-config", flush=True)
    return extra


def build(output: Path, work: Path, tag: str | None) -> None:
    native = work / "native/mlc_llvm_static"
    extra = stage(native, work)
    if extra is None:
        raise RuntimeError("Build both wheels from the raw All-target SDK, not an already split native payload")
    env = dict(os.environ, MLC_LLVM_STATIC_PREFIX=str(native / "static"),
               MLC_LLVM_STATIC_EXTRA_PAYLOAD=str(extra))
    destination = work / "wheels"
    destination.mkdir(parents=True, exist_ok=True)
    for project in (PROJECT, PROJECT.parent / "mlc-llvm-static-extra-targets"):
        run([sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", destination, project], env=env)
    if tag:
        for wheel in sorted(destination.glob("*.whl")):
            run([sys.executable, "-m", "wheel", "tags", "--remove", "--platform-tag", tag, wheel])
    wheels = sorted(destination.glob("*.whl"))
    if len(wheels) != 2:
        raise RuntimeError(f"Expected two wheels, got {wheels}")
    paths = []
    for wheel in wheels:
        with zipfile.ZipFile(wheel) as archive:
            paths.append({name for name in archive.namelist() if name.startswith("mlc_llvm_static/")})
    if paths[0] & paths[1]:
        raise RuntimeError(f"Wheels have overlapping file ownership: {sorted(paths[0] & paths[1])}")
    output.mkdir(parents=True, exist_ok=True)
    for wheel in wheels:
        shutil.copy2(wheel, output / wheel.name)
        print(f"Prepared {wheel.name}: {wheel.stat().st_size / 1_000_000:.1f} MB", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage-native", type=Path)
    parser.add_argument("--output", type=Path, default=PROJECT / "wheelhouse")
    parser.add_argument("--work-root", type=Path, default=PROJECT / "build/split-sdk")
    parser.add_argument("--platform-tag")
    args = parser.parse_args()
    if args.stage_native:
        stage(args.stage_native.resolve(), args.work_root.resolve())
    else:
        build(args.output.resolve(), args.work_root.resolve(), args.platform_tag)


if __name__ == "__main__":
    main()
