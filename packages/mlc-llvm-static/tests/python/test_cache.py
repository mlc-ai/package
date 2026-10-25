"""Cached SDK extraction retains executable modes and confines file paths."""
import importlib.util
from pathlib import Path
import runpy
from zipfile import ZipFile, ZipInfo

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "prepare_llvm.py"
spec = importlib.util.spec_from_file_location("prepare_cache", SCRIPT)
prepare = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prepare)


def setup_cache(tmp_path, monkeypatch):
    monkeypatch.setenv("MLC_LLVM_STATIC_USE_CACHE", "1")
    monkeypatch.setattr(prepare, "__file__", str(tmp_path / "scripts/prepare_llvm.py"))
    cache = tmp_path / ".sdk-cache"
    cache.mkdir()
    return cache / "all-sdk.zip"


def test_restores_only_sdk_payload_with_executable_permissions(tmp_path, monkeypatch):
    wheel = setup_cache(tmp_path, monkeypatch)
    with ZipFile(wheel, "w") as archive:
        executable = ZipInfo("mlc_llvm_static/static/bin/llvm-config")
        executable.external_attr = 0o100755 << 16
        archive.writestr(executable, b"executable")
        archive.writestr("mlc_llvm_static/staticlib.json", "{}")
        archive.writestr("mlc_llvm_static/licenses/LLVM.txt", "license")
        archive.writestr("mlc_llvm_static/__init__.py", "unrelated Python code")
    prefix = prepare.cached_prefix(tmp_path / "work")
    assert (prefix / "bin/llvm-config").read_bytes() == b"executable"
    if prepare.os.name != "nt":
        assert (prefix / "bin/llvm-config").stat().st_mode & 0o111
    assert (prefix.parent / "licenses/LLVM.txt").read_text() == "license"
    assert not (prefix.parent / "__init__.py").exists()


def test_rejects_a_cached_sdk_path_that_escapes_the_work_directory(tmp_path, monkeypatch):
    wheel = setup_cache(tmp_path, monkeypatch)
    with ZipFile(wheel, "w") as archive:
        archive.writestr("mlc_llvm_static/static/../../../escape", "invalid")
    with pytest.raises(RuntimeError, match="Invalid cached SDK path"):
        prepare.cached_prefix(tmp_path / "work")


def test_recipe_cache_separates_compilers_but_not_parallelism(monkeypatch):
    monkeypatch.syspath_prepend(str(SCRIPT.parent))
    for name in ("CC", "CXX"):
        monkeypatch.delenv(name, raising=False)

    def key():
        return runpy.run_path(str(SCRIPT.with_name("cache_key.py")))["key"]

    default = key()
    monkeypatch.setenv("CC", "")
    monkeypatch.setenv("CXX", "")
    monkeypatch.setenv("CMAKE_BUILD_PARALLEL_LEVEL", "1")
    assert key() == default
    monkeypatch.setenv("CC", "clang-cl")
    c_override = key()
    assert c_override != default
    monkeypatch.setenv("CXX", "clang-cl")
    both_overrides = key()
    assert both_overrides not in (default, c_override)
    monkeypatch.setenv("CXX", "cl")
    assert key() not in (default, c_override, both_overrides)


def test_recipe_cache_includes_native_build_policy(tmp_path, monkeypatch):
    import prepare_llvm

    def key():
        return runpy.run_path(str(SCRIPT.with_name("cache_key.py")))["key"]

    original = key()
    policy = tmp_path / "sdk_build_options.cmake"
    policy.write_text(SCRIPT.with_name(policy.name).read_text())
    monkeypatch.setattr(prepare_llvm, "__file__", str(tmp_path / "prepare_llvm.py"))
    assert key() == original
    policy.write_text(policy.read_text() + "\nadd_compile_options(-fno-rtti)\n")
    assert key() != original
