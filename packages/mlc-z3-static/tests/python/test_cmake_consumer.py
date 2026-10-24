"""Configure, link, and run a C++ consumer against the packaged static Z3 library."""
from __future__ import annotations

import platform
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import mlc_z3_static

CMAKELISTS = """
cmake_minimum_required(VERSION 3.20)
project(mlc_z3_static_consumer LANGUAGES C CXX)
find_package(Z3 CONFIG REQUIRED)
get_target_property(Z3_IMPORTED_LOCATION z3::libz3 IMPORTED_LOCATION_RELEASE)
if(NOT Z3_IMPORTED_LOCATION)
  get_target_property(Z3_IMPORTED_LOCATION z3::libz3 IMPORTED_LOCATION)
endif()
file(REAL_PATH "${Z3_IMPORTED_LOCATION}" Z3_IMPORTED_LOCATION_REAL)
file(REAL_PATH "${Z3_EXPECTED_PREFIX}" Z3_EXPECTED_PREFIX_REAL)
string(FIND "${Z3_IMPORTED_LOCATION_REAL}" "${Z3_EXPECTED_PREFIX_REAL}/" Z3_PREFIX_POSITION)
if(NOT Z3_PREFIX_POSITION EQUAL 0)
  message(FATAL_ERROR "z3::libz3 resolves outside the wheel: ${Z3_IMPORTED_LOCATION_REAL}")
endif()
add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE z3::libz3)
"""

MAIN_CPP = """
#include <z3++.h>

int main() {
  z3::context ctx;
  z3::solver solver(ctx);
  solver.add(ctx.bool_const("x"));
  if (solver.check() != z3::sat) return 1;

  Z3_config cfg = Z3_mk_config();
  Z3_context c = Z3_mk_context(cfg);
  Z3_del_context(c);
  Z3_del_config(cfg);
  return 0;
}
"""


def dynamic_dependencies(exe: Path) -> str | None:
    """Return the executable's dynamic library list, or None if no tool is available."""
    system = platform.system()
    tool = {"Linux": ["ldd"], "Darwin": ["otool", "-L"]}.get(system)
    if tool is None or shutil.which(tool[0]) is None:
        return None
    return subprocess.run([*tool, str(exe)], check=True, text=True, stdout=subprocess.PIPE).stdout


@pytest.mark.skipif(shutil.which("cmake") is None, reason="cmake is not installed")
def test_cmake_consumer(tmp_path: Path) -> None:
    source, build = tmp_path / "src", tmp_path / "build"
    source.mkdir()
    (source / "CMakeLists.txt").write_text(CMAKELISTS, encoding="utf-8")
    (source / "main.cpp").write_text(MAIN_CPP, encoding="utf-8")
    prefix = mlc_z3_static.get_cmake_prefix_path()
    configure = ["cmake", "-S", str(source), "-B", str(build), "-DCMAKE_BUILD_TYPE=Release",
                 f"-DCMAKE_PREFIX_PATH={prefix}", f"-DZ3_EXPECTED_PREFIX={prefix}"]
    if platform.system() != "Windows" and shutil.which("ninja"):
        configure += ["-G", "Ninja"]
    subprocess.run(configure, check=True)
    subprocess.run(["cmake", "--build", str(build), "--config", "Release"], check=True)

    # Visual Studio generators are multi-config and add a Release subdirectory.
    exe = build / "Release" / "consumer.exe" if platform.system() == "Windows" else build / "consumer"
    subprocess.run([str(exe)], check=True)

    # Z3 must be linked into the executable, with no runtime Z3 dependency.
    dependencies = dynamic_dependencies(exe)
    if dependencies is not None:
        # Install names may be versioned: libz3.so.5.3 on Linux, libz3.5.3.dylib on macOS.
        links_libz3 = re.search(r"libz3(\.[0-9]+)*\.(so|dylib)\b", dependencies) is not None
        assert not links_libz3, dependencies
