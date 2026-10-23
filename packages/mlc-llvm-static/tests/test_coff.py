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


def library(big, code=b"\xc3", public=b"public", debug=b"debug", labels=False, weak=False,
            selection=2, section_number=0, bss=False, bss_file_data=False):
    header_size = 56 if big else 20
    symbol_size = 20 if big else 18
    symbol_count = (8 if weak else 6) if labels else 1
    relocation_offset = header_size + 80 + len(code) + len(debug)
    relocations = struct.pack("<IIH", 0, 4, 4) if labels and not weak else b""
    symbol_offset = relocation_offset + len(relocations)
    if big:
        header = struct.pack("<HHHHI16sIIIIIII", 0, 0xffff, 2, 0x8664, 0,
                             bytes(16), 0, 0, 0, 0, 2, symbol_offset, symbol_count)
    else:
        header = struct.pack("<HHIIIHH", 0x8664, 2, 0, symbol_offset, symbol_count, 0, 0)
    sections = b""
    offset = header_size + 80
    for name, contents, flags in [(b".bss" if bss else b".text", code, 0xc0100080 if bss else 0x60000020),
                                   (b".debug$S", debug, 0x42100040)]:
        referenced = name == b".text" and bool(relocations)
        sections += struct.pack("<8sIIIIIIHHI", name, 0, 0, len(contents),
                                0 if bss and not bss_file_data and name == b".bss" else offset,
                                relocation_offset if referenced else 0, 0, int(referenced), 0, flags)
        offset += len(contents)
    symbol = struct.pack("<8sIiHBB" if big else "<8sIhHBB", public, 0, 1, 0x20, 2, 0)
    if labels:
        fmt = "<8sIiHBB" if big else "<8sIhHBB"
        auxiliary = bytearray(symbol_size)
        auxiliary[14] = selection
        struct.pack_into("<H", auxiliary, 12, section_number)
        symbol += struct.pack(fmt, b".text", 0, 1, 0, 3, 1) + auxiliary
        symbol += struct.pack(fmt, b"$dead", 0, 1, 0, 3, 0)
        symbol += struct.pack(fmt, b"$keep", 0, 1, 0, 3, 0)
        if weak:
            symbol += struct.pack(fmt, b"weak", 0, 0, 0, 105, 1)
            symbol += struct.pack("<I", 4) + bytes(symbol_size - 4)
        symbol += struct.pack(fmt, b"@feat.00", 0x800, -1, 0, 3, 0)
    payload = header + sections + code + debug + relocations + symbol + struct.pack("<I", 4)
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


@pytest.mark.parametrize("big", [False, True])
@pytest.mark.parametrize("weak", [False, True])
def test_only_unreferenced_labels_can_be_removed(tmp_path, big, weak):
    path = tmp_path / "test.lib"
    path.write_bytes(library(big, labels=True, weak=weak))
    assert module.coff_contents(path, removable=True) == {b"$dead"}
    # A name may be local in one member and public in another.
    path.write_bytes(library(big, labels=True, weak=weak) + library(big, public=b"$dead")[8:])
    assert module.coff_contents(path, removable=True) == set()


@pytest.mark.parametrize("big", [False, True])
def test_comdat_selection_is_part_of_the_preservation_check(tmp_path, big):
    path = tmp_path / "test.lib"
    path.write_bytes(library(big, labels=True, selection=2))
    original = module.coff_contents(path)
    path.write_bytes(library(big, labels=True, selection=3))
    assert module.coff_contents(path) != original


@pytest.mark.parametrize("big", [False, True])
def test_ignores_non_associative_comdat_number_normalization(tmp_path, big):
    path = tmp_path / "test.lib"
    path.write_bytes(library(big, labels=True, section_number=0))
    original = module.coff_contents(path)
    path.write_bytes(library(big, labels=True, section_number=1))
    assert module.coff_contents(path) == original


@pytest.mark.parametrize("big", [False, True])
def test_bss_preserves_logical_size_with_or_without_file_data(tmp_path, big):
    path = tmp_path / "test.lib"
    path.write_bytes(library(big, bss=True, code=bytes(16)))
    original = module.coff_contents(path)
    path.write_bytes(library(big, bss=True, bss_file_data=True, code=bytes(16)))
    assert module.coff_contents(path) == original
    path.write_bytes(library(big, bss=True, code=bytes(32)))
    assert module.coff_contents(path) != original


def test_bigobj_to_ordinary_coff_preserves_section_definitions(tmp_path):
    path = tmp_path / "test.lib"
    path.write_bytes(library(True, labels=True))
    original = module.coff_contents(path)
    path.write_bytes(library(False, labels=True))
    assert module.coff_contents(path) == original
