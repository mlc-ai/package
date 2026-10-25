"""Mirrors never weaken source-digest verification."""
import hashlib
import importlib.util
import io
from pathlib import Path
import tarfile

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/prepare_llvm.py"
spec = importlib.util.spec_from_file_location("prepare_sources", SCRIPT)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def source_spec(monkeypatch):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as archive:
        content = b"cmake_minimum_required(VERSION 3.31)\n"
        entry = tarfile.TarInfo("zlib-source/CMakeLists.txt")
        entry.size = len(content)
        archive.addfile(entry, io.BytesIO(content))
    payload = buffer.getvalue()
    monkeypatch.setattr(prepare, "SOURCES", {"zlib": {
        "url": "https://primary.example/zlib.tar.gz", "mirrors": ["https://mirror.example/zlib.tar.gz"],
        "sha256": hashlib.sha256(payload).hexdigest(), "version": "fixture"}})
    return payload


def test_rejects_bad_primary_and_accepts_only_verified_mirror(tmp_path, monkeypatch):
    payload = source_spec(monkeypatch)
    calls = []

    def download(url, timeout):
        calls.append(url)
        return io.BytesIO(payload if "mirror.example" in url else b"untrusted HTTP 200 response")

    monkeypatch.setattr(prepare.urllib.request, "urlopen", download)
    tree = prepare.source_tree("zlib", tmp_path)
    assert (tree / "CMakeLists.txt").is_file()
    assert len(calls) == 2
    assert prepare.source_tree("zlib", tmp_path) == tree
    assert len(calls) == 2


def test_rejects_every_unverified_download(tmp_path, monkeypatch):
    source_spec(monkeypatch)
    monkeypatch.setattr(prepare.urllib.request, "urlopen", lambda *args, **kwargs: io.BytesIO(b"wrong source"))
    with pytest.raises(RuntimeError, match="Could not fetch verified source"):
        prepare.source_tree("zlib", tmp_path)
    assert not (tmp_path / "sources/zlib.tar.gz").exists()


def test_orc_install_directory_uses_the_configured_llvm_major(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    import split_sdk

    source, work, prefix = (tmp_path / name for name in ("source", "work", "prefix"))
    (source / "llvm/tools").mkdir(parents=True)
    (prefix / "lib").mkdir(parents=True)
    configurations = []

    def configure(source, build, destination, options):
        configurations.append((source, destination))
        if build.name == "build-llvm":
            variables = build / "tools/llvm-config/BuildVariables.inc"
            variables.parent.mkdir(parents=True, exist_ok=True)
            variables.write_text('#define LLVM_SYSTEM_LIBS ""\n')

    monkeypatch.setattr(prepare, "LLVM_VERSION", "99.2.3")
    monkeypatch.setattr(prepare.platform, "system", lambda: "Linux")
    monkeypatch.setattr(prepare, "configure", configure)
    monkeypatch.setattr(prepare, "install", lambda *args: None)
    monkeypatch.setattr(prepare, "run", lambda *args, **kwargs: "riscv64-unknown-linux-gnu")
    monkeypatch.setattr(split_sdk, "distribution_options", lambda *args: [])
    monkeypatch.setattr(split_sdk, "record_build", lambda *args: None)
    prepare.build_llvm(source, work, prefix)
    assert configurations[-1] == (source / "compiler-rt", prefix / "lib/clang/99")
