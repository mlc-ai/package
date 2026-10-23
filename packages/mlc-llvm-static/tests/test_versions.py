"""Version changes must follow metadata rather than the current LLVM release."""
import importlib.util
from pathlib import Path
import runpy

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/stamp_version.py"
spec = importlib.util.spec_from_file_location("stamp_version", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def packages(tmp_path):
    for name, version_file, dependency in (
        ("mlc-llvm-static", "src/mlc_llvm_static/_version.py", "mlc-llvm-static-extra-targets"),
        ("mlc-llvm-static-extra-targets", "version.py", "mlc-llvm-static"),
    ):
        project = tmp_path / name
        path = project / version_file
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('__version__ = "99.2.3.dev4"\nLLVM_VERSION = "99.2.3"\n')
        (project / "pyproject.toml").write_text(f'dependencies = ["{dependency}==99.2.3.dev4"]\n')
    return tmp_path


@pytest.mark.parametrize("version", [None, "99.2.3rc1", "99.2.3.post1.dev2", "99.2.3+local"])
def test_stamps_both_versions_and_exact_requirements(packages, version):
    result = module.stamp_version(version, packages=packages)
    assert result == (version or "99.2.3.dev4")
    for name, relative in (("mlc-llvm-static", "src/mlc_llvm_static/_version.py"),
                           ("mlc-llvm-static-extra-targets", "version.py")):
        project = packages / name
        assert runpy.run_path(str(project / relative))["__version__"] == result
        assert f"=={result}" in (project / "pyproject.toml").read_text()


@pytest.mark.parametrize("version", ["98.2.3", "99.2.4", "invalid"])
def test_rejects_invalid_versions_without_modifying_files(packages, version):
    before = {path: path.read_bytes() for path in packages.rglob("*") if path.is_file()}
    with pytest.raises(ValueError):
        module.stamp_version(version, packages=packages)
    assert all(path.read_bytes() == contents for path, contents in before.items())
