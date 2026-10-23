"""Stamp the mlc-z3-static package version in the root version.py.

The package version must stay based on the pinned upstream Z3_VERSION; only a
PEP 440 suffix (such as .post1, rc0, or .dev0) may be added on top of it.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import runpy

from packaging.version import Version

PROJECT = Path(__file__).resolve().parents[1]
UPSTREAM_KEY = "Z3_VERSION"


def stamp_version(requested: str | None = None, *, suffix: str | None = None,
                  source: Path = PROJECT / "version.py") -> str:
    current = runpy.run_path(str(source))
    upstream = current[UPSTREAM_KEY]
    if suffix is not None:
        if requested:
            raise ValueError("Choose an explicit version or a suffix, not both")
        requested = upstream + suffix
    version = Version(requested or current["__version__"])
    if version.base_version != upstream:
        raise ValueError(f"Package version {version} must be based on {UPSTREAM_KEY} {upstream}")
    text = source.read_text(encoding="utf-8")
    text, count = re.subn(r'^__version__ = "[^"]*"$', f'__version__ = "{version}"', text, flags=re.M)
    if count != 1:
        raise ValueError(f"Expected exactly one __version__ assignment in {source}")
    source.write_text(text, encoding="utf-8")
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
