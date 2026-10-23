"""Packaging tools must be verified before executing downloaded binaries."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/packaging_tools.py"
spec = importlib.util.spec_from_file_location("packaging_tools", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def fixture_archive(monkeypatch):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:xz") as archive:
        content = b"packaging executable fixture\n"
        entry = tarfile.TarInfo("7zzs")
        entry.size = len(content)
        archive.addfile(entry, io.BytesIO(content))
    data = buffer.getvalue()
    monkeypatch.delenv("MLC_LLVM_STATIC_7ZIP", raising=False)
    monkeypatch.setattr(module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(module.platform, "machine", lambda: "aarch64")
    monkeypatch.setattr(module, "SEVEN_ZIP", {("Linux", "aarch64"): (
        "tool.tar.xz", "7zzs", hashlib.sha256(data).hexdigest())})
    return data


def test_verified_download_and_cached_archive(tmp_path, monkeypatch):
    data = fixture_archive(monkeypatch)
    calls = []

    def download(url, timeout):
        calls.append(url)
        return io.BytesIO(data)

    monkeypatch.setattr(module.urllib.request, "urlopen", download)
    executable = Path(module.seven_zip(tmp_path))
    assert executable.read_bytes() == b"packaging executable fixture\n"
    assert executable.stat().st_mode & 0o111
    # Re-extract from the verified cached archive rather than trusting an old
    # executable that may have been modified by a previous packaging run.
    executable.write_bytes(b"modified")
    assert module.seven_zip(tmp_path) == str(executable)
    assert executable.read_bytes() == b"packaging executable fixture\n"
    assert len(calls) == 1


def test_bad_download_never_creates_executable(tmp_path, monkeypatch):
    fixture_archive(monkeypatch)
    monkeypatch.setattr(module.urllib.request, "urlopen", lambda *args, **kwargs: io.BytesIO(b"wrong binary"))
    with pytest.raises(RuntimeError, match="checksum mismatch"):
        module.seven_zip(tmp_path)
    assert not (tmp_path / "7zzs").exists()
    assert not (tmp_path / "tool.tar.xz").exists()
    assert not (tmp_path / "tool.tar.part").exists()
