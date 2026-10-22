"""Partition one All-target LLVM build into disjoint, version-locked payloads."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess


def read_components(path: Path) -> dict:
    pattern = r'\{ "([^"]+)", (nullptr|"[^"]+"), true, \{([^}]*)\} \}'
    result = {}
    for name, library, requires in re.findall(pattern, path.read_text(encoding="utf-8")):
        result[name] = {"library": None if library == "nullptr" else library.strip('"'),
                        "requires": re.findall(r'"([^"]+)"', requires)}
    if "all" not in result or "core" not in result:
        raise RuntimeError("Unrecognized LLVM component table")
    return result


def closure(graph: dict, roots) -> set[str]:
    visited = set()

    def visit(name):
        if name not in visited:
            visited.add(name)
            for dep in graph[name]["requires"]:
                visit(dep)

    for root in roots:
        visit(root)
    return visited


def partitions(graph: dict, targets: list[str], native: str) -> tuple[dict, set[str]]:
    # LLVM's backend component groups explicitly enumerate their libraries.
    # Common dependencies are promoted to the base by dependency closure.
    other = {dep for target in targets if target != native
             for dep in graph[target.lower()]["requires"]}
    roots = {name for name, entry in graph.items() if entry["library"] and name not in other}
    base_names = closure(graph, roots)
    base_libraries = {graph[name]["library"] for name in base_names if graph[name]["library"]}
    extra_libraries = {entry["library"] for entry in graph.values() if entry["library"]} - base_libraries
    native_graph = {}
    for name, entry in graph.items():
        if name in ("all", "all-targets"):
            continue
        if name in {target.lower() for target in targets if target != native}:
            continue
        required = closure(graph, [name])
        if all(graph[dep]["library"] not in extra_libraries for dep in required):
            native_graph[name] = entry
    native_graph["all-targets"] = {"library": None, "requires": [native.lower()]}
    native_graph["all"] = {"library": None, "requires": [name for name in graph["all"]["requires"]
                                                           if name in native_graph]}
    return native_graph, extra_libraries


def cmake_value(path: Path, name: str) -> str:
    match = re.search(r"^set\(" + re.escape(name) + r'\s+([^\n)]*)\)', path.read_text(), re.MULTILINE)
    if not match:
        raise RuntimeError(f"Missing {name} in {path}")
    return match[1].strip().strip('"')


def distribution_options(build: Path) -> list[str]:
    graph = read_components(build / "tools/llvm-config/LibraryDependencies.inc")
    config = build / "lib/cmake/llvm/LLVMConfig.cmake"
    targets = cmake_value(config, "LLVM_TARGETS_TO_BUILD").split(";")
    native = cmake_value(config, "LLVM_NATIVE_ARCH")
    if native not in targets or len(targets) < 2:
        raise RuntimeError("Split SDKs require an All-target build containing the native backend")
    _, extra = partitions(graph, targets, native)
    return ["-DLLVM_DISTRIBUTION_COMPONENTS=", "-DLLVM_DISTRIBUTIONS=Base;Extra;Reference",
            "-DLLVM_Base_DISTRIBUTION_COMPONENTS=llvm-headers;llvm-libraries;cmake-exports;base-cmake-exports",
            "-DLLVM_Extra_DISTRIBUTION_COMPONENTS=" + ";".join(sorted(extra)) + ";extra-cmake-exports",
            "-DLLVM_Reference_DISTRIBUTION_COMPONENTS=llvm-config;reference-cmake-exports"]


def record_build(build: Path, prefix: Path) -> None:
    graph = read_components(build / "tools/llvm-config/LibraryDependencies.inc")
    extensions = (build / "tools/llvm-config/ExtensionDependencies.inc").read_text()
    if not re.search(r"array<ExtensionDescriptor, 0>", extensions):
        raise RuntimeError("Unexpected LLVM extensions: their dependency graph needs explicit support")
    config = prefix / "lib/cmake/llvm/LLVMConfig.cmake"
    native = cmake_value(config, "LLVM_NATIVE_ARCH")
    targets = cmake_value(config, "LLVM_TARGETS_TO_BUILD").split(";")
    native_graph, extra = partitions(graph, targets, native)
    executable = prefix / "bin" / ("llvm-config.exe" if os.name == "nt" else "llvm-config")
    flags = {}
    for name in ("cflags", "cppflags", "cxxflags", "ldflags", "system-libs"):
        output = subprocess.check_output([str(executable), "--" + name], text=True).strip()
        # Windows paths contain backslashes; list2cmdline-compatible parsing is
        # needed there instead of treating backslashes as POSIX escapes.
        tokens = shlex.split(output, posix=os.name != "nt")
        flags[name] = [token.strip('"').replace(str(prefix), "${prefix}").replace(prefix.as_posix(), "${prefix}")
                       for token in tokens if not token.startswith("-I") and not token.startswith(("-L", "-LIBPATH:"))]
    data = {"components": graph, "native_components": native_graph, "extra_libraries": sorted(extra),
            "native": native, "targets": targets, "flags": flags,
            "host_target": subprocess.check_output([str(executable), "--host-target"], text=True).strip()}
    directory = prefix / "share/mlc-llvm-static"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "build.json").write_text(json.dumps(data, indent=2) + "\n")


def hashes(root: Path) -> dict:
    return {path.relative_to(root).as_posix(): {"size": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in sorted(root.rglob("*")) if path.is_file()}


def filter_headers(base: Path, extra: Path, native: str) -> None:
    config = base / "include/llvm/Config"
    extra_config = extra / "include/llvm/Config"
    names = [path.name for path in config.glob("*.def") if re.search(
        r"^LLVM_\w+\(\w+\)", path.read_text(), re.MULTILINE)]
    names.append("Targets.h")
    for name in names:
        contents = (config / name).read_text()
        native_contents = re.sub(r"^LLVM_\w+\((\w+)\).*\n", lambda m: m[0] if m[1] == native else "",
                                 contents, flags=re.MULTILINE)
        if name == "Targets.h":
            native_contents = re.sub(r"^(#define LLVM_HAS_(\w+)_TARGET) [01]$",
                                     lambda m: m[1] + (" 1" if m[2] == native.upper() else " 0"),
                                     contents, flags=re.MULTILINE)
        (config / "mlc-native").mkdir(exist_ok=True)
        (extra_config / "mlc-all").mkdir(parents=True, exist_ok=True)
        (config / "mlc-native" / name).write_text(native_contents)
        (extra_config / "mlc-all" / name).write_text(contents)
        (config / name).write_text(
            "/* Profile dispatcher: immutable files are owned by separate wheels. */\n"
            f'#if !defined(MLC_LLVM_STATIC_NATIVE_ONLY) && __has_include("llvm/Config/mlc-all/{name}")\n'
            f'#include "llvm/Config/mlc-all/{name}"\n#else\n'
            f'#include "llvm/Config/mlc-native/{name}"\n#endif\n')


def profile_cmake(prefix: Path, data: dict, base_libs: list[str], all_libs: list[str]) -> None:
    path = prefix / "lib/cmake/llvm/LLVMConfig.cmake"
    text = path.read_text()
    block = '''
# Both wheels own disjoint files under LLVM_INSTALL_PREFIX. Do not edit them
# when switching profiles; the profile applies to this CMake configuration.
file(READ "${LLVM_INSTALL_PREFIX}/share/mlc-llvm-static/base.json" _mlc_base)
string(JSON _mlc_build GET "${_mlc_base}" build_id)
string(JSON _mlc_version GET "${_mlc_base}" sdk_version)
set(_mlc_has_extra OFF)
if(EXISTS "${LLVM_INSTALL_PREFIX}/share/mlc-llvm-static/extra.json")
  file(READ "${LLVM_INSTALL_PREFIX}/share/mlc-llvm-static/extra.json" _mlc_extra)
  string(JSON _mlc_extra_build GET "${_mlc_extra}" build_id)
  string(JSON _mlc_extra_version GET "${_mlc_extra}" sdk_version)
  if(NOT _mlc_extra_build STREQUAL _mlc_build OR NOT _mlc_extra_version STREQUAL _mlc_version)
    message(FATAL_ERROR "LLVM base and extra-targets packages have different build IDs or versions")
  endif()
  set(_mlc_has_extra ON)
endif()
if(NOT DEFINED MLC_LLVM_STATIC_PROFILE)
  set(MLC_LLVM_STATIC_PROFILE "$ENV{MLC_LLVM_STATIC_PROFILE}")
endif()
if(NOT MLC_LLVM_STATIC_PROFILE OR MLC_LLVM_STATIC_PROFILE STREQUAL "auto")
  if(_mlc_has_extra)
    set(MLC_LLVM_STATIC_PROFILE "all")
  else()
    set(MLC_LLVM_STATIC_PROFILE "native")
  endif()
endif()
if(MLC_LLVM_STATIC_PROFILE STREQUAL "all" AND NOT _mlc_has_extra)
  message(FATAL_ERROR "The all LLVM profile requires mlc-llvm-static-extra-targets")
elseif(NOT MLC_LLVM_STATIC_PROFILE MATCHES "^(native|all)$")
  message(FATAL_ERROR "LLVM profile must be auto, native, or all")
endif()
'''
    base_text = ";".join(base_libs)
    all_text = ";".join(all_libs)
    block += (f'if(MLC_LLVM_STATIC_PROFILE STREQUAL "native")\n'
              f'  set(LLVM_AVAILABLE_LIBS {base_text})\n  set(LLVM_TARGETS_TO_BUILD {data["native"]})\n'
              f'else()\n  set(LLVM_AVAILABLE_LIBS {all_text})\n'
              f'  set(LLVM_TARGETS_TO_BUILD {";".join(data["targets"])})\nendif()\n')
    text = re.sub(r"set\(LLVM_AVAILABLE_LIBS [^\n]*\)", lambda _: block, text, count=1)
    text = re.sub(r"^set\(LLVM_TARGETS_TO_BUILD [^\n]*\)\n", "", text, flags=re.MULTILINE)
    # Export sets are generated by LLVM_DISTRIBUTIONS, with upstream's import
    # location and target-interface handling preserved intact.
    text = text.replace('include("${LLVM_CMAKE_DIR}/LLVMExtraExports.cmake" OPTIONAL)',
                        'if(MLC_LLVM_STATIC_PROFILE STREQUAL "all")\n'
                        '  include("${LLVM_CMAKE_DIR}/LLVMExtraExports.cmake")\nendif()')
    text = text.replace('include("${LLVM_CMAKE_DIR}/LLVMReferenceExports.cmake" OPTIONAL)', "")
    text += '\nif(MLC_LLVM_STATIC_PROFILE STREQUAL "native")\n  string(APPEND LLVM_DEFINITIONS " -DMLC_LLVM_STATIC_NATIVE_ONLY=1")\nendif()\n'
    text += 'set_property(GLOBAL PROPERTY LLVM_COMPONENT_LIBS ${LLVM_AVAILABLE_LIBS})\n'
    path.write_text(text)


def split_sdk(raw: Path, native: Path, extra: Path, version: str, runtime: Path) -> dict:
    source = raw / "static"
    metadata = json.loads((raw / "staticlib.json").read_text())
    data = json.loads((source / "share/mlc-llvm-static/build.json").read_text())
    all_libs = cmake_value(source / "lib/cmake/llvm/LLVMConfig.cmake", "LLVM_AVAILABLE_LIBS").split(";")
    base_libs = [name for name in all_libs if name not in data["extra_libraries"]]
    for destination in (native, extra):
        if destination.exists():
            shutil.rmtree(destination)
        (destination / "static").mkdir(parents=True)
    base, added = native / "static", extra / "static"
    shutil.copytree(source, base, dirs_exist_ok=True)
    for path in (base / "lib/cmake/llvm").glob("LLVMReferenceExports*.cmake"):
        path.unlink()
    libraries = {}
    for path in (base / "lib").glob("*"):
        if path.suffix in (".a", ".lib"):
            name = path.stem.removeprefix("lib")
            libraries[name] = path.relative_to(base).as_posix()
            if name in data["extra_libraries"]:
                target = added / path.relative_to(base)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(path, target)
    for path in (base / "lib/cmake/llvm").glob("LLVMExtraExports*.cmake"):
        target = added / path.relative_to(base)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(path, target)
    if not (added / "lib/cmake/llvm/LLVMExtraExports.cmake").is_file():
        raise RuntimeError("SDK must be built with LLVM's Base and Extra export sets")
    filter_headers(base, added, data["native"])
    profile_cmake(base, data, base_libs, all_libs)
    shutil.rmtree(base / "bin")
    (base / "bin").mkdir()
    shutil.copy2(runtime, base / "bin/llvm-config.py")
    if metadata["system"] != "Windows":
        shutil.copy2(runtime, base / "bin/llvm-config")
        (base / "bin/llvm-config").chmod(0o755)
    (base / "share/mlc-llvm-static/build.json").unlink()
    # Exact build identity catches mismatched cached/rebuilt payloads even if
    # their Python version metadata happens to match.
    identity = hashlib.sha256(json.dumps(metadata, sort_keys=True).encode()).hexdigest()
    manifests = {}
    for profile, destination in (("native", native), ("all", extra)):
        prefix = destination / "static"
        record = {key: value for key, value in metadata.items() if key != "files"}
        record.update(schema_version=2, sdk_version=version, build_id=identity,
                      targets=[data["native"]] if profile == "native" else data["targets"])
        record["files"] = hashes(prefix)
        record["archive_count"] = sum(name.endswith((".a", ".lib")) for name in record["files"])
        if profile == "native":
            record.update(flags=data["flags"], host_target=data["host_target"], profiles={
                "native": {"components": data["native_components"],
                           "libraries": {name: path for name, path in libraries.items() if name not in data["extra_libraries"]}},
                "all": {"components": data["components"], "libraries": libraries}})
        directory = prefix / "share/mlc-llvm-static"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / ("base.json" if profile == "native" else "extra.json")).write_text(json.dumps(record, indent=2) + "\n")
        manifests[profile] = record
    shutil.copytree(raw / "licenses", native / "licenses")
    # Keep the existing package-level manifest API, without giving either wheel
    # ownership of the other wheel's manifest or licenses.
    (native / "staticlib.json").write_text(json.dumps(manifests["native"], indent=2) + "\n")
    return manifests
