"""Recompression must preserve installed bytes, RECORD, and executable modes."""
import base64
import hashlib
import importlib.util
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/compress_wheel.py"
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


@pytest.mark.parametrize("corrupt", [False, True])
def test_strong_deflate_preserves_modes_and_rejects_changed_payload(tmp_path, monkeypatch, corrupt):
    path = tmp_path / "sdk-py3-none-macosx_14_0_arm64.whl"
    member = ZipInfo("sdk/bin/llvm-config", (2020, 1, 2, 3, 4, 6))
    member.external_attr = 0o100755 << 16
    member.comment = b"original member comment"
    content = b"#!/usr/bin/env python3\n"
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.comment = b"original archive comment"
        archive.writestr(member, content)
    original = path.read_bytes()

    def encode(command, cwd, **kwargs):
        assert "-mm=Deflate" in command
        assert "-mpass=3" in command
        with ZipFile(command[-2], "w", ZIP_DEFLATED) as archive:
            archive.writestr(member.filename, b"changed" if corrupt else (Path(cwd) / member.filename).read_bytes())

    monkeypatch.setattr(module.subprocess, "run", encode)
    if corrupt:
        with pytest.raises(RuntimeError, match="changed wheel payload"):
            module.compress_wheel(path, seven_zip="fixture-tool")
        assert path.read_bytes() == original
    else:
        module.compress_wheel(path, seven_zip="fixture-tool")
        with ZipFile(path) as archive:
            actual = archive.getinfo(member.filename)
            assert archive.read(member.filename) == content
            assert actual.external_attr == member.external_attr
            assert actual.date_time == member.date_time
            assert actual.comment == member.comment
            assert archive.comment == b"original archive comment"
    assert not path.with_suffix(".whl.tmp").exists()
