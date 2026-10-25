"""Native SDK configuration keeps user flags and enables archive dead stripping."""
import platform
import shutil
import subprocess

import pytest

from prepare_llvm import configure


@pytest.mark.skipif(platform.system() != "Linux", reason="ELF section inspection")
@pytest.mark.parametrize("split_sections", [False, True])
def test_native_archive_dead_stripping(tmp_path, monkeypatch, split_sections):
    for tool in ("cmake", "ninja", "cc", "c++", "nm"):
        if not shutil.which(tool):
            pytest.skip(f"{tool} is required for the native configure probe")
    monkeypatch.setenv("CFLAGS", "-DCALLER_C_FLAG=1")
    monkeypatch.setenv("CXXFLAGS", "-DCALLER_CXX_FLAG=1")
    (tmp_path / "CMakeLists.txt").write_text('''
cmake_minimum_required(VERSION 3.31)
project(section_probe LANGUAGES C CXX)
add_library(probe STATIC c.c cxx.cpp)
add_executable(consumer main.cpp)
target_link_libraries(consumer PRIVATE probe)
target_link_options(consumer PRIVATE "LINKER:--gc-sections")
''')
    for filename, flag, suffix in (("c.c", "CALLER_C_FLAG", "c"),
                                  ("cxx.cpp", "CALLER_CXX_FLAG", "cxx")):
        (tmp_path / filename).write_text(f'''
#ifndef {flag}
#error caller flag was lost
#endif
int unused_data_{suffix} = 7;
int unused_function_{suffix}(void) {{ return unused_data_{suffix}; }}
int used_{suffix}(void) {{ return 21; }}
''')
    (tmp_path / "main.cpp").write_text('''
extern "C" int used_c(void);
int used_cxx(void);
int main() { return used_c() + used_cxx() != 42; }
''')
    build = tmp_path / "build"
    configure(tmp_path, build, tmp_path / "prefix", [])
    configure(tmp_path, build, tmp_path / "prefix", [], split_sections=split_sections)
    subprocess.run(["cmake", "--build", str(build)], check=True)
    subprocess.run([str(build / "consumer")], check=True)
    archive = subprocess.check_output(["nm", "-C", str(build / "libprobe.a")], text=True)
    linked = subprocess.check_output(["nm", "-C", str(build / "consumer")], text=True)
    for symbol in ("unused_data_c", "unused_data_cxx", "unused_function_c", "unused_function_cxx"):
        assert symbol in archive
        assert (symbol not in linked) == split_sections
