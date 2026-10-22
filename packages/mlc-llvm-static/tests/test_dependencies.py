"""Regression checks using native dependency-tool output formats."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_wheel.py"
spec = importlib.util.spec_from_file_location("verify_wheel", SCRIPT)
verify = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify)


def test_otool_does_not_mistake_the_probe_for_a_dependency():
    output = """/tmp/SDK with spaces/build/libmlc_llvm_probe.dylib:
    @rpath/libmlc_llvm_probe.dylib (compatibility version 0.0.0, current version 0.0.0)
    /usr/lib/libSystem.B.dylib (compatibility version 1.0.0, current version 1351.0.0)
    /usr/lib/libc++.1.dylib (compatibility version 1.0.0, current version 1900.180.0)
"""
    assert verify.dynamic_sdk_dependencies(output) == []


def test_dumpbin_does_not_mistake_the_probe_for_a_dependency():
    output = r"""Dump of file C:\SDK with spaces\build\mlc_llvm_probe.dll
    Image has the following dependencies:
        KERNEL32.dll
        MSVCP140.dll
        VCRUNTIME140.dll
"""
    assert verify.dynamic_sdk_dependencies(output) == []


@pytest.mark.parametrize("output,name", [
    ("libLLVM-23.so.1 => /lib/libLLVM-23.so.1 (0x1234)", "libLLVM-23.so.1"),
    ("libz.so.1 => /lib/libz.so.1 (0x1234)", "libz.so.1"),
    ("libzstd.so.1 => not found", "libzstd.so.1"),
    ("/path with spaces/libLLVM.dylib (compatibility version 1.0.0)", "libLLVM.dylib"),
    ("/usr/lib/libz.1.dylib (compatibility version 1.0.0)", "libz.1.dylib"),
    ("/usr/lib/libzstd.1.dylib (compatibility version 1.0.0)", "libzstd.1.dylib"),
    ("    LLVM.dll", "LLVM.dll"),
    ("    zlib1.dll", "zlib1.dll"),
    ("    libzstd.dll", "libzstd.dll"),
])
def test_rejects_dynamic_sdk_libraries(output, name):
    assert verify.dynamic_sdk_dependencies(output) == [name]
