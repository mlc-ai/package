"""Verify that CMake can consume the packaged static Z3 library."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import z3_static


def run(cmd: list[str], *, cwd: Path) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.check_call(cmd, cwd=cwd)


def get_cmake_dir_from_config() -> str:
    """Return the CMake directory reported by the z3_static.config CLI."""
    output = subprocess.check_output(
        [sys.executable, "-m", "z3_static.config", "--cmake-dir"], text=True
    )
    cmake_dir = output.strip()
    if cmake_dir != z3_static.get_cmake_dir():
        raise RuntimeError(
            f"Unexpected z3_static.config --cmake-dir output: {cmake_dir}"
        )
    return cmake_dir


def main() -> None:
    cmake = shutil.which("cmake")
    if not cmake:
        raise RuntimeError("cmake is required")
    z3_cmake_dir = get_cmake_dir_from_config()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "CMakeLists.txt").write_text(
            """
cmake_minimum_required(VERSION 3.20)
project(z3_static_smoke LANGUAGES CXX)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
find_package(Z3 CONFIG REQUIRED)
add_executable(smoke main.cc)
target_link_libraries(smoke PRIVATE z3::libz3)
""".strip()
            + "\n"
        )
        (root / "main.cc").write_text(
            """
#include <z3++.h>

int main() {
  z3::context ctx;
  z3::solver solver(ctx);
  z3::expr x = ctx.int_const("x");
  solver.add(x > 0);
  return solver.check() == z3::sat ? 0 : 1;
}
""".strip()
            + "\n"
        )

        build = root / "build"
        run(
            [cmake, "-S", str(root), "-B", str(build), f"-DZ3_DIR={z3_cmake_dir}"],
            cwd=root,
        )
        if sys.platform == "win32":
            run([cmake, "--build", str(build), "--config", "Release"], cwd=root)
            exe = build / "Release" / "smoke.exe"
        else:
            run([cmake, "--build", str(build)], cwd=root)
            exe = build / "smoke"
        run([str(exe)], cwd=root)


if __name__ == "__main__":
    main()

