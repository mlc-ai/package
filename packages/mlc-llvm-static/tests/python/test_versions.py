"""Version changes must follow metadata rather than the current LLVM release."""
import importlib.util
from pathlib import Path
import runpy
import tomllib

import pytest
from packaging.requirements import Requirement
from packaging.version import Version

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/stamp_version.py"
spec = importlib.util.spec_from_file_location("stamp_version", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def project(tmp_path):
    (tmp_path / "version.py").write_text('__version__ = "99.2.3.dev4"\nLLVM_VERSION = "99.2.3"\n')
    (tmp_path / "pyproject.toml").write_text(
        '[project.optional-dependencies]\nall = ["mlc-llvm-static-extra-targets==99.2.3.dev4"]\n')
    (tmp_path / "extra-targets").mkdir()
    (tmp_path / "extra-targets/pyproject.toml").write_text(
        '[project]\ndependencies = ["mlc-llvm-static==99.2.3.dev4"]\n')
    return tmp_path


@pytest.mark.parametrize("version", [None, "99.2.3", "99.2.3rc1", "99.2.3.rc0",
                                     "99.2.3.post1.dev2", "99.2.3+local"])
def test_stamps_version_and_both_exact_requirements(project, version):
    result = module.stamp_version(version, project=project)
    assert result == str(Version(version or "99.2.3.dev4"))
    assert runpy.run_path(str(project / "version.py"))["__version__"] == result
    for metadata in (project / "pyproject.toml", project / "extra-targets/pyproject.toml"):
        assert f"=={result}" in metadata.read_text()


@pytest.mark.parametrize("version", ["98.2.3", "99.2.4", "invalid"])
def test_rejects_invalid_versions_without_modifying_files(project, version):
    before = {path: path.read_bytes() for path in project.rglob("*") if path.is_file()}
    with pytest.raises(ValueError):
        module.stamp_version(version, project=project)
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
def test_suffix_selection_locks_both_dependencies(project, suffix, expected):
    result = module.stamp_version(suffix=suffix, project=project)
    assert result == expected
    base = tomllib.loads((project / "pyproject.toml").read_text())["project"]
    extra = tomllib.loads((project / "extra-targets/pyproject.toml").read_text())["project"]
    assert base["optional-dependencies"]["all"] == [f"mlc-llvm-static-extra-targets=={expected}"]
    assert extra["dependencies"] == [f"mlc-llvm-static=={expected}"]
    assert runpy.run_path(str(project / "version.py"))["__version__"] == expected


@pytest.mark.parametrize("options", [
    {"suffix": value} for value in ("invalid", ".9", "4", "rc1;echo", "rc1rc2", "dev1post1")
] + [{"requested": "99.2.3", "suffix": "rc0"}])
def test_rejects_invalid_suffix_selection_without_modifying_files(project, options):
    before = {path: path.read_bytes() for path in project.rglob("*") if path.is_file()}
    with pytest.raises(ValueError):
        module.stamp_version(project=project, **options)
    assert all(path.read_bytes() == contents for path, contents in before.items())


def test_checked_in_metadata_keeps_native_install_optional_and_versions_locked():
    root = SCRIPT.parents[1]
    base_metadata = tomllib.loads((root / "pyproject.toml").read_text())
    extra_metadata = tomllib.loads((root / "extra-targets/pyproject.toml").read_text())
    base, extra = base_metadata["project"], extra_metadata["project"]
    versions = runpy.run_path(str(root / "version.py"))
    version = versions["__version__"]
    assert Version(version).base_version == versions["LLVM_VERSION"]
    # Both distributions read the version from the single root version.py.
    assert base_metadata["tool"]["scikit-build"]["metadata"]["version"]["input"] == "version.py"
    extra_input = extra_metadata["tool"]["scikit-build"]["metadata"]["version"]["input"]
    assert (root / "extra-targets" / extra_input).resolve() == (root / "version.py").resolve()
    assert base["optional-dependencies"]["all"] == [f"mlc-llvm-static-extra-targets=={version}"]
    assert extra["dependencies"] == [f"mlc-llvm-static=={version}"]
    assert not any(Requirement(value).name == "mlc-llvm-static-extra-targets"
                   for value in base.get("dependencies", []))


def test_runtime_version_module_is_generated_from_version_py(tmp_path):
    from prepare_llvm import write_version_module

    write_version_module(tmp_path)
    generated = runpy.run_path(str(tmp_path / "_version.py"))
    versions = runpy.run_path(str(SCRIPT.parents[1] / "version.py"))
    assert generated["__version__"] == versions["__version__"]
    assert generated["LLVM_VERSION"] == versions["LLVM_VERSION"]
    import mlc_llvm_static
    assert mlc_llvm_static.__version__ == versions["__version__"]
    assert mlc_llvm_static.LLVM_VERSION == versions["LLVM_VERSION"]
