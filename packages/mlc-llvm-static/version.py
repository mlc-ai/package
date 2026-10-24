"""Single source of truth for the mlc-llvm-static release.

Bumping LLVM means editing only this file and then running
``scripts/stamp_version.py`` (see "Bumping the version" in README.md). Both
the mlc-llvm-static and mlc-llvm-static-extra-targets distributions, their
exact-version requirements, the build scripts, and the generated runtime
module ``mlc_llvm_static/_version.py`` derive from these values.
"""

__version__ = "23.1.1"
LLVM_VERSION = "23.1.1"
LLVM_ARCHIVE_SHA256 = "ebe9be46fe8756d58c5b198ffad0fa2a766257add81a4dc52179bfacc7888ee6"
