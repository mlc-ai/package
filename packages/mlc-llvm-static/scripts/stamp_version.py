"""Stamp the shared SDK version in version.py and both exact-version requirements.

mlc-llvm-static and mlc-llvm-static-extra-targets both read their version from
the root version.py. The package version must stay based on the pinned
LLVM_VERSION; only a PEP 440 suffix (such as .post1, rc0, or .dev0) may be
added on top of it.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import runpy

from packaging.version import Version

PROJECT = Path(__file__).resolve().parents[1]
UPSTREAM_KEY = "LLVM_VERSION"


def stamp_version(requested: str | None = None, *, suffix: str | None = None,
                  project: Path = PROJECT) -> str:
    source = project / "version.py"
    current = runpy.run_path(str(source))
    upstream = current[UPSTREAM_KEY]
    if suffix is not None:
        if requested:
            raise ValueError("Choose an explicit version or a suffix, not both")
        requested = upstream + suffix
    version = Version(requested or current["__version__"])
    if version.base_version != upstream:
        raise ValueError(f"Package version {version} must be based on {UPSTREAM_KEY} {upstream}")
    text, count = re.subn(r'^__version__ = "[^"]*"$', f'__version__ = "{version}"',
                          source.read_text(encoding="utf-8"), flags=re.M)
    if count != 1:
        raise ValueError(f"Expected exactly one __version__ assignment in {source}")
    updates = {source: text}
    # Each distribution pins the other at exactly the same version.
    for metadata in (project / "pyproject.toml", project / "extra-targets/pyproject.toml"):
        text, count = re.subn(r'(mlc-llvm-static(?:-extra-targets)?==)[^"\]]+',
                              lambda match: match[1] + str(version), metadata.read_text(encoding="utf-8"))
        if count != 1:
            raise ValueError(f"Expected exactly one exact-version SDK requirement in {metadata}")
        updates[metadata] = text
    for path, text in updates.items():
        path.write_text(text, encoding="utf-8")
    return str(version)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", default="", help="Defaults to the checked-in package version")
    parser.add_argument("--suffix", help=f"Append to the pinned {UPSTREAM_KEY}; empty for stable")
    args = parser.parse_args()
    version = stamp_version(args.version, suffix=args.suffix)
    print(version)
    if os.environ.get("GITHUB_OUTPUT"):
        with open(os.environ["GITHUB_OUTPUT"], "a") as output:
            output.write(f"version={version}\n")
