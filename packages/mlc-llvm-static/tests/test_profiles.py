"""Profile selection and static link ordering must agree across package changes."""
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from mlc_llvm_static._llvm_config import Configuration, ConfigurationError
from split_sdk import filter_headers, partitions, read_components, split_sdk


@pytest.fixture
def sdk(tmp_path):
    graph = {
        "support": {"library": "LLVMSupport", "requires": []},
        "core": {"library": "LLVMCore", "requires": ["support"]},
        "x86codegen": {"library": "LLVMX86CodeGen", "requires": ["core", "support"]},
        "armcodegen": {"library": "LLVMARMCodeGen", "requires": ["core", "support"]},
        "x86": {"library": None, "requires": ["x86codegen"]},
        "arm": {"library": None, "requires": ["armcodegen"]},
        "native": {"library": None, "requires": ["x86"]},
        "all-targets": {"library": None, "requires": ["x86", "arm"]},
        "all": {"library": None, "requires": ["support", "core", "x86codegen", "armcodegen", "all-targets", "native", "x86", "arm"]},
    }
    native_graph, extras = partitions(graph, ["X86", "ARM"], "X86")
    libraries = {entry["library"]: "lib/lib" + entry["library"] + ".a"
                 for entry in graph.values() if entry["library"]}
    for relative in libraries.values():
        path = tmp_path / relative
        path.parent.mkdir(exist_ok=True)
        path.write_bytes(b"!<arch>\n")
    directory = tmp_path / "share/mlc-llvm-static"
    directory.mkdir(parents=True)
    base = {"build_id": "one-build", "sdk_version": "23.1.1.dev1", "llvm_version": "23.1.1",
            "system": "Linux", "targets": ["X86"], "host_target": "x86_64-unknown-linux-gnu",
            "build": {"type": "Release", "rtti": True, "assertions": False},
            "flags": {"cxxflags": ["-std=c++17", "-fno-exceptions"], "cflags": [], "cppflags": [],
                      "ldflags": [], "system-libs": ["-lz", "-lzstd", "-ldl"]},
            "profiles": {"native": {"components": native_graph,
                        "libraries": {name: path for name, path in libraries.items() if name not in extras}},
                        "all": {"components": graph, "libraries": libraries}}}
    (directory / "base.json").write_text(json.dumps(base))
    return tmp_path, directory, base


def install_extra(directory, **overrides):
    extra = {"build_id": "one-build", "sdk_version": "23.1.1.dev1", "targets": ["X86", "ARM"]}
    extra.update(overrides)
    (directory / "extra.json").write_text(json.dumps(extra))


def test_native_has_no_foreign_component_or_target(sdk):
    prefix, _, _ = sdk
    config = Configuration(prefix)
    assert config.profile == "native"
    assert config.query(["--targets-built"]) == "X86\n"
    assert "armcodegen" not in config.query(["--components"])
    with pytest.raises(ConfigurationError, match="unavailable"):
        config.query(["--libfiles", "ARM"])
    with pytest.raises(ConfigurationError, match="requires"):
        Configuration(prefix, "all")


def test_install_remove_and_explicit_native_profile(sdk):
    prefix, directory, _ = sdk
    install_extra(directory)
    assert Configuration(prefix).targets == ["X86", "ARM"]
    assert Configuration(prefix).query(["--libs", "ARM"]) == "-lLLVMARMCodeGen -lLLVMCore -lLLVMSupport\n"
    assert Configuration(prefix, "native").targets == ["X86"]
    assert "-DMLC_LLVM_STATIC_NATIVE_ONLY=1" in Configuration(prefix, "native").query(["--cxxflags"])
    assert "MLC_LLVM_STATIC_NATIVE_ONLY" not in Configuration(prefix).query(["--cxxflags"])
    (directory / "extra.json").unlink()
    assert Configuration(prefix).targets == ["X86"]


@pytest.mark.parametrize("field,value", [("build_id", "other-build"), ("sdk_version", "23.1.1.dev2")])
def test_rejects_mixed_sdk_builds(sdk, field, value):
    prefix, directory, _ = sdk
    install_extra(directory, **{field: value})
    with pytest.raises(ConfigurationError, match="different SDK builds"):
        Configuration(prefix)


def test_dependency_order_and_deduplication(sdk):
    prefix, _, _ = sdk
    assert Configuration(prefix).query(["--link-static", "--libs", "Core", "native"]) == "-lLLVMX86CodeGen -lLLVMCore -lLLVMSupport\n"
    assert Configuration(prefix).query(["--libs", "--system-libs", "Core"]) == "-lLLVMCore -lLLVMSupport\n-lz -lzstd -ldl\n"


def test_missing_archive_fails_before_link(sdk):
    prefix, _, _ = sdk
    (prefix / "lib/libLLVMSupport.a").unlink()
    with pytest.raises(ConfigurationError, match="missing static archive"):
        Configuration(prefix).query(["--libs", "native"])


@pytest.mark.parametrize("args", [["--link-shared", "--libs"], ["--unknown"], ["Core"], []])
def test_unsupported_queries_fail(sdk, args):
    prefix, _, _ = sdk
    with pytest.raises(ConfigurationError):
        Configuration(prefix).query(args)


def test_header_dispatch_does_not_overwrite_another_wheels_files(tmp_path):
    base, extra = tmp_path / "base", tmp_path / "extra"
    headers = base / "include/llvm/Config"
    headers.mkdir(parents=True)
    (headers / "Targets.def").write_text("LLVM_TARGET(X86)\nLLVM_TARGET(ARM)\n#undef LLVM_TARGET\n")
    (headers / "Targets.h").write_text("#define LLVM_HAS_X86_TARGET 1\n#define LLVM_HAS_ARM_TARGET 1\n")
    filter_headers(base, extra, "X86")
    assert "LLVM_TARGET(ARM)" not in (headers / "mlc-native/Targets.def").read_text()
    assert "#define LLVM_HAS_ARM_TARGET 0" in (headers / "mlc-native/Targets.h").read_text()
    assert "LLVM_TARGET(ARM)" in (extra / "include/llvm/Config/mlc-all/Targets.def").read_text()
    assert "__has_include" in (headers / "Targets.def").read_text()
    assert not ({p.relative_to(base) for p in base.rglob("*") if p.is_file()}
                & {p.relative_to(extra) for p in extra.rglob("*") if p.is_file()})


def test_component_table_requires_complete_graph(tmp_path):
    path = tmp_path / "LibraryDependencies.inc"
    path.write_text('{ "core", "LLVMCore", true, {"support"} },\n{ "all", nullptr, true, {"core"} },\n')
    assert read_components(path)["core"]["requires"] == ["support"]
    path.write_text("Unexpected future LLVM component format")
    with pytest.raises(RuntimeError, match="Unrecognized"):
        read_components(path)


@pytest.mark.parametrize("system", ["Linux", "Windows"])
def test_split_removes_reference_executable_and_keeps_disjoint_ownership(tmp_path, sdk, system):
    prefix, _, base_metadata = sdk
    raw = tmp_path / "raw"
    import shutil
    shutil.copytree(prefix, raw / "static")
    static = raw / "static"
    (static / "share/mlc-llvm-static/base.json").unlink()
    config = static / "lib/cmake/llvm"
    config.mkdir(parents=True)
    (config / "LLVMConfig.cmake").write_text(
        'set(LLVM_AVAILABLE_LIBS LLVMCore;LLVMSupport;LLVMX86CodeGen;LLVMARMCodeGen)\n'
        'set(LLVM_TARGETS_TO_BUILD X86;ARM)\n'
        'include("${LLVM_CMAKE_DIR}/LLVMBaseExports.cmake" OPTIONAL)\n'
        'include("${LLVM_CMAKE_DIR}/LLVMExtraExports.cmake" OPTIONAL)\n'
        'include("${LLVM_CMAKE_DIR}/LLVMReferenceExports.cmake" OPTIONAL)\n')
    for name in ("Base", "Extra", "Reference"):
        (config / f"LLVM{name}Exports.cmake").write_text("# fixture export set\n")
    headers = static / "include/llvm/Config"
    headers.mkdir(parents=True)
    (headers / "Targets.def").write_text("LLVM_TARGET(X86)\nLLVM_TARGET(ARM)\n#undef LLVM_TARGET\n")
    (headers / "Targets.h").write_text("#define LLVM_HAS_X86_TARGET 1\n#define LLVM_HAS_ARM_TARGET 1\n")
    (static / "bin").mkdir()
    (static / "bin" / ("llvm-config.exe" if system == "Windows" else "llvm-config")).write_bytes(b"reference executable")
    (raw / "licenses").mkdir()
    (raw / "licenses/LLVM.txt").write_text("fixture license")
    metadata = {"llvm_version": "23.1.1", "system": system, "build": base_metadata["build"], "files": {}}
    (raw / "staticlib.json").write_text(json.dumps(metadata))
    data = {"components": base_metadata["profiles"]["all"]["components"],
            "native_components": base_metadata["profiles"]["native"]["components"],
            "extra_libraries": ["LLVMARMCodeGen"], "native": "X86", "targets": ["X86", "ARM"],
            "flags": base_metadata["flags"], "host_target": base_metadata["host_target"]}
    (static / "share/mlc-llvm-static/build.json").write_text(json.dumps(data))
    native, extra = tmp_path / "native", tmp_path / "extra"
    split_sdk(raw, native, extra, "23.1.1.dev1", ROOT / "src/mlc_llvm_static/_llvm_config.py")
    native_files = {p.relative_to(native / "static") for p in (native / "static").rglob("*") if p.is_file()}
    extra_files = {p.relative_to(extra / "static") for p in (extra / "static").rglob("*") if p.is_file()}
    assert not native_files & extra_files
    assert Path("lib/libLLVMARMCodeGen.a") not in native_files
    assert Path("lib/libLLVMARMCodeGen.a") in extra_files
    assert not list((native / "static/lib/cmake/llvm").glob("LLVMReferenceExports*"))
    assert "LLVMReferenceExports" not in (native / "static/lib/cmake/llvm/LLVMConfig.cmake").read_text()
    assert not (native / "static/bin/llvm-config.exe").exists()
    assert Configuration(native / "static").targets == ["X86"]
    from prepare_llvm import validate_prefix
    validate_prefix(native / "static")
