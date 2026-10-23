"""Recompression must preserve installed bytes, RECORD, and executable modes."""
import base64
import hashlib
import importlib.util
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/compress_wheel.py"
spec = importlib.util.spec_from_file_location("compress_wheel", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_preserves_payload_record_and_archive_metadata(tmp_path):
    path = tmp_path / "sdk.whl"
    name = "mlc_llvm_static/static/bin/llvm-config"
    payload = b"#!/usr/bin/env python3\n" + b"# LLVM SDK\n" * 10000
    digest = base64.urlsafe_b64encode(hashlib.sha256(payload).digest()).rstrip(b"=").decode()
    record = f"{name},sha256={digest},{len(payload)}\nsdk.dist-info/RECORD,,\n".encode()
    executable = ZipInfo(name, (2020, 1, 2, 3, 4, 6))
    executable.external_attr = 0o100755 << 16
    executable.comment = b"executable frontend"
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.comment = b"SDK wheel"
        archive.writestr(executable, payload)
        archive.writestr("sdk.dist-info/RECORD", record)
    before = path.stat().st_size
    module.compress_wheel(path)
    with ZipFile(path) as archive:
        assert archive.namelist() == [name, "sdk.dist-info/RECORD"]
        assert archive.read(name) == payload
        assert archive.read("sdk.dist-info/RECORD") == record
        member = archive.getinfo(name)
        assert member.external_attr == executable.external_attr
        assert member.date_time == executable.date_time
        assert member.comment == executable.comment
        assert member.compress_type == ZIP_DEFLATED
        assert archive.comment == b"SDK wheel"
    assert path.stat().st_size < before
    assert not path.with_suffix(".whl.tmp").exists()
