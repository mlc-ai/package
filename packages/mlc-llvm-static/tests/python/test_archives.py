"""Regression checks for the SDK's native-object archive requirement."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "prepare_llvm.py"
spec = importlib.util.spec_from_file_location("prepare_llvm", SCRIPT)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def archive_member(payload: bytes, name: bytes = b"test.o/") -> bytes:
    header = name.ljust(16) + b"0".ljust(12) + b"0".ljust(6) + b"0".ljust(6)
    header += b"644".ljust(8) + str(len(payload)).encode().ljust(10) + b"`\n"
    return header + payload + (b"\n" if len(payload) % 2 else b"")


def test_accepts_native_objects_with_padding_and_bsd_names(tmp_path):
    path = tmp_path / "native.a"
    path.write_bytes(b"!<arch>\n" + archive_member(b"\x7fELFobject") +
                     archive_member(b"longname.o\x00\xfe\xed\xfa\xcfobject", b"#1/11"))
    prepare.validate_native_archive(path)


@pytest.mark.parametrize("magic", [b"BC\xc0\xde", b"\xde\xc0\x17\x0b"])
@pytest.mark.parametrize("bsd", [False, True])
def test_rejects_lto_even_after_bsd_extended_filename(tmp_path, magic, bsd):
    path = tmp_path / "lto.a"
    member = archive_member(b"longname.o\x00" + magic, b"#1/11") if bsd else archive_member(magic)
    path.write_bytes(b"!<arch>\n" + member)
    with pytest.raises(RuntimeError, match="LTO bitcode"):
        prepare.validate_native_archive(path)


@pytest.mark.parametrize("payload", [b"!<thin>\n", b"!<arch>\ntruncated"])
def test_rejects_thin_or_corrupt_archives(tmp_path, payload):
    path = tmp_path / "invalid.a"
    path.write_bytes(payload)
    with pytest.raises(RuntimeError):
        prepare.validate_native_archive(path)
