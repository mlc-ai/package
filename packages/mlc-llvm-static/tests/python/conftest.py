"""Make the source package importable the way the wheel installs it.

The runtime ``mlc_llvm_static/_version.py`` is generated at build time, so the
tests import a temporary copy of ``python/mlc_llvm_static`` that carries the
generated module, and import the build scripts from ``scripts/``.
"""
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from prepare_llvm import write_version_module  # noqa: E402

_PACKAGE_ROOT = tempfile.TemporaryDirectory(prefix="mlc-llvm-static-tests-")
_package = Path(_PACKAGE_ROOT.name) / "mlc_llvm_static"
shutil.copytree(ROOT / "python/mlc_llvm_static", _package)
write_version_module(_package)
sys.path.insert(0, _PACKAGE_ROOT.name)


def pytest_unconfigure(config):
    _PACKAGE_ROOT.cleanup()
