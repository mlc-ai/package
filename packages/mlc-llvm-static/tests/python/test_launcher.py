"""Windows console discovery must respect the wheel's real install scheme."""
from pathlib import PurePosixPath
from types import SimpleNamespace

import pytest

import mlc_llvm_static as sdk


def test_uses_record_for_user_install_instead_of_default_scripts(tmp_path, monkeypatch):
    executable = tmp_path / "user/Scripts/llvm-config.exe"
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b"pip launcher")
    record = PurePosixPath("../../Scripts/llvm-config.exe")
    installed = SimpleNamespace(files=[record], locate_file=lambda _: executable)
    monkeypatch.setattr(sdk, "distribution", lambda _: installed)
    monkeypatch.setattr(sdk.sysconfig, "get_path", lambda _: str(tmp_path / "wrong-default/Scripts"))
    assert sdk._windows_launcher() == str(executable)


def test_missing_launcher_does_not_use_an_unrelated_path_program(tmp_path, monkeypatch):
    installed = SimpleNamespace(files=[])
    monkeypatch.setattr(sdk, "distribution", lambda _: installed)
    monkeypatch.setattr(sdk.sysconfig, "get_path", lambda _: str(tmp_path / "Scripts"))
    monkeypatch.setenv("PATH", str(tmp_path / "unrelated-llvm/bin"))
    with pytest.raises(FileNotFoundError, match="pip-installed"):
        sdk._windows_launcher()
