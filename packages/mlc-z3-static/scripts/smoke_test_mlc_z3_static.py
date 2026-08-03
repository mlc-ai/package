#!/usr/bin/env python3
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import mlc_z3_static


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    print("+ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def runtime_env(kind: str) -> dict[str, str]:
    env = os.environ.copy()
    if kind != "shared":
        return env

    # Use the directory that actually contains the shared library: on Windows
    # the DLL is installed under shared/bin, not shared/lib.
    lib_dir = str(Path(mlc_z3_static.get_shared_library_path()).parent)
    system = platform.system()
    if system == "Darwin":
        key = "DYLD_LIBRARY_PATH"
    elif system == "Windows":
        key = "PATH"
    else:
        key = "LD_LIBRARY_PATH"
    existing = env.get(key)
    env[key] = f"{lib_dir}{os.pathsep}{existing}" if existing else lib_dir
    return env


def check_config_cli(kind: str) -> None:
    output = subprocess.check_output(
        [sys.executable, "-m", "mlc_z3_static.config", "--cmake-dir", "--kind", kind], text=True
    )
    cmake_dir = output.strip()
    if cmake_dir != mlc_z3_static.get_cmake_dir(kind):
        raise RuntimeError(f"Unexpected mlc_z3_static.config --cmake-dir output: {cmake_dir}")


def build_consumer(root: Path, kind: str) -> None:
    source = root / f"src-{kind}"
    build = root / f"build-{kind}"
    prefix = mlc_z3_static.get_cmake_prefix_path(kind)
    source.mkdir()
    (source / "CMakeLists.txt").write_text(
        """
cmake_minimum_required(VERSION 3.20)
project(mlc_z3_static_smoke LANGUAGES C CXX)
find_package(Z3 CONFIG REQUIRED)
get_target_property(Z3_IMPORTED_LOCATION z3::libz3 IMPORTED_LOCATION_RELEASE)
if(NOT Z3_IMPORTED_LOCATION)
  get_target_property(Z3_IMPORTED_LOCATION z3::libz3 IMPORTED_LOCATION)
endif()
if(NOT Z3_IMPORTED_LOCATION)
  message(FATAL_ERROR "z3::libz3 does not expose an imported library location")
endif()
file(REAL_PATH "${Z3_IMPORTED_LOCATION}" Z3_IMPORTED_LOCATION_REAL)
file(REAL_PATH "${Z3_EXPECTED_PREFIX}" Z3_EXPECTED_PREFIX_REAL)
string(FIND "${Z3_IMPORTED_LOCATION_REAL}" "${Z3_EXPECTED_PREFIX_REAL}/" Z3_PREFIX_POSITION)
if(NOT Z3_PREFIX_POSITION EQUAL 0)
  message(
    FATAL_ERROR
    "z3::libz3 resolves outside the installed wheel prefix.\\n"
    "  imported: ${Z3_IMPORTED_LOCATION_REAL}\\n"
    "  expected prefix: ${Z3_EXPECTED_PREFIX_REAL}"
  )
endif()
add_executable(mlc_z3_static_smoke main.cpp)
target_link_libraries(mlc_z3_static_smoke PRIVATE z3::libz3)
""".lstrip(),
        encoding="utf-8",
    )
    (source / "main.cpp").write_text(
        """
#include <z3++.h>

int main() {
  z3::context cxx_ctx;
  z3::expr x = cxx_ctx.bool_const("x");
  z3::solver cxx_solver(cxx_ctx);
  cxx_solver.add(x);
  if (cxx_solver.check() != z3::sat) {
    return 1;
  }

  Z3_config cfg = Z3_mk_config();
  Z3_context ctx = Z3_mk_context(cfg);
  Z3_solver solver = Z3_mk_solver(ctx);
  Z3_solver_inc_ref(ctx, solver);
  Z3_solver_dec_ref(ctx, solver);
  Z3_del_context(ctx);
  Z3_del_config(cfg);
  return 0;
}
""".lstrip(),
        encoding="utf-8",
    )

    configure_cmd = [
        "cmake",
        "-S",
        str(source),
        "-B",
        str(build),
        f"-DCMAKE_PREFIX_PATH={prefix}",
        f"-DZ3_EXPECTED_PREFIX={prefix}",
        "-DCMAKE_BUILD_TYPE=Release",
    ]
    if platform.system() != "Windows" and shutil.which("ninja"):
        configure_cmd.extend(["-G", "Ninja"])
    run(configure_cmd)
    run(["cmake", "--build", str(build), "--config", "Release"])

    if platform.system() == "Windows":
        # The Visual Studio generator is multi-config and places binaries in a
        # per-configuration subdirectory.
        exe = build / "Release" / "mlc_z3_static_smoke.exe"
    else:
        exe = build / "mlc_z3_static_smoke"
    run([str(exe)], env=runtime_env(kind))


def main() -> None:
    print(f"Z3 tag: {mlc_z3_static.Z3_TAG}")
    print(f"Z3 commit: {mlc_z3_static.Z3_COMMIT}")
    print(f"Z3 static library: {mlc_z3_static.get_static_library_path()}")
    print(f"Z3 shared library: {mlc_z3_static.get_shared_library_path()}")

    check_config_cli("static")
    check_config_cli("shared")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        build_consumer(root, "static")
        build_consumer(root, "shared")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"smoke test failed: {err}", file=sys.stderr)
        raise
