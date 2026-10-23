"""COFF compaction may change debug metadata, never public code or definitions."""
import importlib.util
from pathlib import Path
import struct
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/compact_coff.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("compact_coff", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def library(big, code=b"\xc3", public=b"public", debug=b"debug"):
    header_size = 56 if big else 20
    symbol_offset = header_size + 80 + len(code) + len(debug)
    if big:
        header = struct.pack("<HHHHI16sIIIIIII", 0, 0xffff, 2, 0x8664, 0,
                             bytes(16), 0, 0, 0, 0, 2, symbol_offset, 1)
    else:
        header = struct.pack("<HHIIIHH", 0x8664, 2, 0, symbol_offset, 1, 0, 0)
    sections = b""
    offset = header_size + 80
    for name, contents, flags in [(b".text", code, 0x60000020), (b".debug$S", debug, 0x42100040)]:
        sections += struct.pack("<8sIIIIIIHHI", name, 0, 0, len(contents), offset, 0, 0, 0, 0, flags)
        offset += len(contents)
    symbol = struct.pack("<8sIiHBB" if big else "<8sIhHBB", public, 0, 1, 0x20, 2, 0)
    payload = header + sections + code + debug + symbol + struct.pack("<I", 4)
    member = b"file.obj/".ljust(16) + b"0".ljust(12) + b"0".ljust(6) + b"0".ljust(6)
    member += b"644".ljust(8) + str(len(payload)).encode().ljust(10) + b"`\n"
    return b"!<arch>\n" + member + payload + (b"\n" if len(payload) % 2 else b"")


@pytest.mark.parametrize("big", [False, True])
def test_fingerprint_ignores_debug_but_protects_code_and_public_names(tmp_path, big):
    path = tmp_path / "test.lib"
    path.write_bytes(library(big))
    expected = module.coff_contents(path)
    path.write_bytes(library(big, debug=b"different debug data"))
    assert module.coff_contents(path) == expected
    path.write_bytes(library(big, code=b"\x90"))
    assert module.coff_contents(path) != expected
    path.write_bytes(library(big, public=b"other"))
    assert module.coff_contents(path) != expected
