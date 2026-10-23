"""Version changes must follow metadata rather than the current LLVM release."""
import importlib.util
from pathlib import Path
import runpy
import tomllib

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

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
        metadata = ('[project.optional-dependencies]\nall' if name == "mlc-llvm-static"
                    else '[project]\ndependencies')
        (project / "pyproject.toml").write_text(f'{metadata} = ["{dependency}==99.2.3.dev4"]\n')
    return tmp_path


@pytest.mark.parametrize("version", [None, "99.2.3", "99.2.3rc1", "99.2.3.rc0",
                                     "99.2.3.post1.dev2", "99.2.3+local"])
def test_stamps_both_versions_and_exact_requirements(packages, version):
    result = module.stamp_version(version, packages=packages)
    assert result == str(Version(version or "99.2.3.dev4"))
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


@pytest.mark.parametrize("suffix,expected", [
    ("", "99.2.3"),
    ("rc0", "99.2.3rc0"),
    (".rc0", "99.2.3rc0"),
    ("rc007", "99.2.3rc7"),
    ("dev0", "99.2.3.dev0"),
    ("post0", "99.2.3.post0"),
    ("a1", "99.2.3a1"),
    ("b1", "99.2.3b1"),
    ("post1.dev2", "99.2.3.post1.dev2"),
])
def test_suffix_selection_locks_both_dependencies(packages, suffix, expected):
    result = module.stamp_version(suffix=suffix, packages=packages)
    assert result == expected
    base = tomllib.loads((packages / "mlc-llvm-static/pyproject.toml").read_text())["project"]
    extra = tomllib.loads((packages / "mlc-llvm-static-extra-targets/pyproject.toml").read_text())["project"]
    assert base["optional-dependencies"]["all"] == [f"mlc-llvm-static-extra-targets=={expected}"]
    assert extra["dependencies"] == [f"mlc-llvm-static=={expected}"]
    assert runpy.run_path(str(packages / "mlc-llvm-static/src/mlc_llvm_static/_version.py"))["__version__"] == expected
    assert runpy.run_path(str(packages / "mlc-llvm-static-extra-targets/version.py"))["__version__"] == expected


@pytest.mark.parametrize("options", [
    {"suffix": value} for value in ("invalid", ".9", "4", "rc1;echo", "rc1rc2", "dev1post1")
] + [{"requested": "99.2.3", "suffix": "rc0"}])
def test_rejects_invalid_suffix_selection_without_modifying_files(packages, options):
    before = {path: path.read_bytes() for path in packages.rglob("*") if path.is_file()}
    with pytest.raises(ValueError):
        module.stamp_version(packages=packages, **options)
    assert all(path.read_bytes() == contents for path, contents in before.items())


def test_checked_in_metadata_keeps_native_install_optional_and_versions_locked():
    root = SCRIPT.parents[2]
    base = tomllib.loads((root / "mlc-llvm-static/pyproject.toml").read_text())["project"]
    extra = tomllib.loads((root / "mlc-llvm-static-extra-targets/pyproject.toml").read_text())["project"]
    versions = runpy.run_path(str(root / "mlc-llvm-static/src/mlc_llvm_static/_version.py"))
    version = versions["__version__"]
    assert Version(version).base_version == versions["LLVM_VERSION"]
    assert runpy.run_path(str(root / "mlc-llvm-static-extra-targets/version.py"))["__version__"] == version
    assert base["optional-dependencies"]["all"] == [f"mlc-llvm-static-extra-targets=={version}"]
    assert extra["dependencies"] == [f"mlc-llvm-static=={version}"]
    assert not any(Requirement(value).name == "mlc-llvm-static-extra-targets"
                   for value in base.get("dependencies", []))
