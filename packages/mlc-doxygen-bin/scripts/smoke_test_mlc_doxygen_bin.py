#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import mlc_doxygen_bin


def run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    print("+ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def write_minimal_project(root: Path) -> Path:
    source = root / "src"
    output = root / "docs"
    source.mkdir()
    (source / "main.cpp").write_text(
        """
/// Adds two integers.
int add(int left, int right) {
  return left + right;
}
""".lstrip(),
        encoding="utf-8",
    )
    doxyfile = root / "Doxyfile"
    doxyfile.write_text(
        f"""
PROJECT_NAME = smoke
OUTPUT_DIRECTORY = {output}
INPUT = {source}
QUIET = YES
WARN_AS_ERROR = YES
GENERATE_HTML = YES
GENERATE_LATEX = NO
HAVE_DOT = NO
""".lstrip(),
        encoding="utf-8",
    )
    return doxyfile


def main() -> None:
    executable = mlc_doxygen_bin.get_executable_path()
    direct = run([executable, "--version"])
    wrapped = run([sys.executable, "-m", "mlc_doxygen_bin", "--version"])
    expected = mlc_doxygen_bin.__version__
    if direct.stdout.strip() != expected:
        raise RuntimeError(f"Expected direct Doxygen version {expected}, got {direct.stdout.strip()!r}")
    if wrapped.stdout.strip() != expected:
        raise RuntimeError(f"Expected wrapped Doxygen version {expected}, got {wrapped.stdout.strip()!r}")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        doxyfile = write_minimal_project(root)
        run([sys.executable, "-m", "mlc_doxygen_bin", str(doxyfile)], cwd=root)
        index = root / "docs" / "html" / "index.html"
        if not index.is_file():
            raise RuntimeError(f"Doxygen did not generate expected HTML index: {index}")


if __name__ == "__main__":
    try:
        main()
    except Exception as err:
        print(f"smoke test failed: {err}", file=sys.stderr)
        raise
