"""Keep both SDK distributions and their exact-version requirements in sync."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import runpy

from packaging.version import Version

PROJECT = Path(__file__).resolve().parents[1]


def stamp_version(requested: str | None = None, *, packages: Path = PROJECT.parent) -> str:
    source = packages / "mlc-llvm-static/src/mlc_llvm_static/_version.py"
    current = runpy.run_path(str(source))
    version = Version(requested or current["__version__"])
    if version.base_version != current["LLVM_VERSION"]:
        raise ValueError(f"Package version must be based on LLVM {current['LLVM_VERSION']}")
    for name, relative in (("mlc-llvm-static", "src/mlc_llvm_static/_version.py"),
                           ("mlc-llvm-static-extra-targets", "version.py")):
        project = packages / name
        metadata = project / "pyproject.toml"
        text = re.sub(r'(mlc-llvm-static(?:-extra-targets)?==)[^"\]]+',
                      lambda match: match[1] + str(version), metadata.read_text(encoding="utf-8"))
        metadata.write_text(text, encoding="utf-8")
        path = project / relative
        text = re.sub(r'__version__ = "[^"]+"', f'__version__ = "{version}"', path.read_text(encoding="utf-8"))
        path.write_text(text, encoding="utf-8")
    return str(version)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", default="", help="Defaults to the checked-in package version")
    version = stamp_version(parser.parse_args().version)
    print(version)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"version={version}\n")
