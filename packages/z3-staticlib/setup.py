"""Build z3-staticlib wheels."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py as _build_py


class build_py(_build_py):
    """Stage the static Z3 artifacts before packaging Python files."""

    def run(self) -> None:
        package_dir = Path(__file__).resolve().parent / "z3_staticlib"
        static_dir = package_dir / "static"
        if not static_dir.exists():
            if os.environ.get("STATICLIB_Z3_ALLOW_SOURCE_BUILD") != "1":
                raise RuntimeError(
                    "z3-staticlib source builds are disabled by default. "
                    "Install a prebuilt wheel, or set STATICLIB_Z3_ALLOW_SOURCE_BUILD=1 "
                    "to build Z3 from source explicitly."
                )
            env = os.environ.copy()
            env.setdefault("STATICLIB_Z3_PACKAGE_DIR", str(package_dir))
            env.setdefault(
                "STATICLIB_Z3_BUILD_ROOT", str(Path(__file__).resolve().parent / "build" / "z3")
            )
            subprocess.check_call(
                [sys.executable, "scripts/z3_staticlib_builder.py"],
                cwd=Path(__file__).resolve().parent,
                env=env,
            )
        super().run()


try:
    from wheel.bdist_wheel import bdist_wheel as _bdist_wheel
except Exception:  # pragma: no cover
    _bdist_wheel = None


if _bdist_wheel is not None:

    class bdist_wheel(_bdist_wheel):
        """Emit py3-none-platform wheels for native development artifacts."""

        def finalize_options(self) -> None:
            super().finalize_options()
            self.root_is_pure = False

        def get_tag(self) -> tuple[str, str, str]:
            _python, _abi, platform = super().get_tag()
            return "py3", "none", os.environ.get("STATICLIB_Z3_PLAT_NAME", platform)


    cmdclass = {"build_py": build_py, "bdist_wheel": bdist_wheel}
else:
    cmdclass = {"build_py": build_py}


setup(cmdclass=cmdclass)

