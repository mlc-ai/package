"""Run the packaged Doxygen executable through every entry point."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import pytest

import mlc_doxygen_bin


def run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(cmd, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return result.stdout.strip()


def console_script() -> str:
    name = "doxygen.exe" if os.name == "nt" else "doxygen"
    path = Path(sysconfig.get_path("scripts")) / name
    return str(path) if path.is_file() else shutil.which("doxygen") or str(path)


@pytest.mark.parametrize(
    "prefix",
    [
        pytest.param([mlc_doxygen_bin.get_executable_path()], id="executable"),
        pytest.param([sys.executable, "-m", "mlc_doxygen_bin"], id="module"),
        pytest.param([console_script()], id="console-script"),
    ],
)
def test_version(prefix: list[str]) -> None:
    # The binary reports the upstream release, without any package suffix.
    assert run([*prefix, "--version"]) == mlc_doxygen_bin.DOXYGEN_VERSION


def test_generates_html(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "add.cpp").write_text("/// Adds two integers.\nint add(int a, int b) { return a + b; }\n", encoding="utf-8")
    doxyfile = tmp_path / "Doxyfile"
    doxyfile.write_text(
        f"PROJECT_NAME = smoke\nOUTPUT_DIRECTORY = {tmp_path / 'docs'}\nINPUT = {source}\n"
        "QUIET = YES\nWARN_AS_ERROR = YES\nGENERATE_HTML = YES\nGENERATE_LATEX = NO\nHAVE_DOT = NO\n",
        encoding="utf-8",
    )
    run([sys.executable, "-m", "mlc_doxygen_bin", str(doxyfile)], cwd=tmp_path)
    assert (tmp_path / "docs" / "html" / "index.html").is_file()
