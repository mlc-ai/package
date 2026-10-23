#!/usr/bin/env python3
"""Static SDK configuration, also installed as a standalone Python script.

The component graph and flags come from this SDK's LLVM build. No compiler,
network access, package discovery, or guessed archive ordering is needed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import subprocess
import sys


class ConfigurationError(ValueError):
    pass


def sdk_prefix() -> Path:
    override = os.environ.get("MLC_LLVM_STATIC_SDK_PREFIX")
    if override:
        return Path(override).resolve()
    here = Path(__file__).resolve()
    return here.parent.parent if here.parent.name == "bin" else here.parent / "static"


class Configuration:
    def __init__(self, prefix: Path | None = None, profile: str | None = None):
        self.prefix = (prefix or sdk_prefix()).resolve()
        directory = self.prefix / "share/mlc-llvm-static"
        self.base = json.loads((directory / "base.json").read_text(encoding="utf-8"))
        self.extra = None
        if (directory / "extra.json").is_file():
            self.extra = json.loads((directory / "extra.json").read_text(encoding="utf-8"))
            for key in ("build_id", "sdk_version"):
                if self.extra[key] != self.base[key]:
                    raise ConfigurationError("LLVM base and extra-targets packages are from different SDK builds")
        self.profile = profile or os.environ.get("MLC_LLVM_STATIC_PROFILE", "auto")
        if self.profile not in ("auto", "native", "all"):
            raise ConfigurationError("LLVM profile must be auto, native, or all")
        if self.profile == "auto":
            self.profile = "all" if self.extra else "native"
        if self.profile == "all" and self.extra is None:
            raise ConfigurationError("The all profile requires the matching mlc-llvm-static-extra-targets wheel")
        self.targets = self.base["targets"] if self.profile == "native" else self.extra["targets"]
        self.components = self.base["profiles"][self.profile]["components"]
        self.libraries = self.base["profiles"][self.profile]["libraries"]

    def ordered_libraries(self, components: list[str]) -> list[str]:
        graph = self.components
        visited, result = set(), []

        def visit(name):
            name = name.lower()
            if name not in graph:
                raise ConfigurationError(f"component {name!r} is unavailable in the {self.profile} profile")
            if name in visited:
                return
            visited.add(name)
            entry = graph[name]
            for dep in entry["requires"]:
                visit(dep)
            library = entry["library"]
            if library:
                path = self.prefix / self.libraries[library]
                if not path.is_file():
                    raise ConfigurationError(f"missing static archive: {path}")
                result.append(library)

        for component in components or ["all"]:
            visit(component)
        return list(reversed(result))

    def query(self, args: list[str]) -> str:
        quote = "--quote-paths" in args
        windows = self.base["system"] == "Windows"

        def render(value):
            value = str(value)
            if not quote:
                return value
            return subprocess.list2cmdline([value]) if windows else shlex.quote(value)

        direct = {
            "--version": self.base["llvm_version"], "--prefix": str(self.prefix),
            "--bindir": str(self.prefix / "bin"), "--includedir": str(self.prefix / "include"),
            "--libdir": str(self.prefix / "lib"), "--cmakedir": str(self.prefix / "lib/cmake/llvm"),
            "--obj-root": str(self.prefix), "--host-target": self.base["host_target"],
            "--targets-built": " ".join(self.targets), "--components": " ".join(sorted(self.components)),
            "--build-mode": self.base["build"]["type"], "--build-system": "cmake",
            "--has-rtti": "YES" if self.base["build"]["rtti"] else "NO",
            "--assertion-mode": "ON" if self.base["build"]["assertions"] else "OFF",
        }
        outputs, components, deferred = [], [], set()
        flags = self.base["flags"]
        for arg in args:
            if not arg.startswith("-"):
                components.append(arg)
            elif arg in direct:
                outputs.append(render(direct[arg]) if arg in {
                    "--prefix", "--bindir", "--includedir", "--libdir", "--cmakedir", "--obj-root",
                } else direct[arg])
            elif arg in ("--cflags", "--cppflags", "--cxxflags"):
                values = ["-I" + str(self.prefix / "include"), *flags[arg[2:]]]
                if self.profile == "native":
                    values.append("-DMLC_LLVM_STATIC_NATIVE_ONLY=1")
                outputs.append(" ".join(render(value) for value in values))
            elif arg == "--ldflags":
                values = [("-LIBPATH:" if windows else "-L") + str(self.prefix / "lib"), *flags["ldflags"]]
                outputs.append(" ".join(render(value) for value in values))
            elif arg in ("--libs", "--libfiles", "--libnames", "--system-libs", "--shared-mode"):
                deferred.add(arg)
            elif arg in ("--link-static", "--ignore-libllvm", "--quote-paths"):
                pass
            elif arg == "--link-shared":
                raise ConfigurationError("This SDK only provides static LLVM libraries")
            elif arg == "--help":
                outputs.append("usage: llvm-config [--profile=native|all|auto] <OPTION>... [<COMPONENT>...]\n"
                               + " ".join(sorted([*direct, "--cflags", "--cppflags", "--cxxflags", "--ldflags",
                                                  "--libs", "--libfiles", "--libnames", "--system-libs",
                                                  "--link-static", "--quote-paths", "--shared-mode"])))
            else:
                raise ConfigurationError(f"unknown option: {arg}")
        if not args or (components and not deferred):
            raise ConfigurationError("Specify a configuration option; components require a library query")
        if deferred:
            libraries = self.ordered_libraries(components)
            if "--shared-mode" in deferred:
                outputs.append("static")
            else:
                if deferred & {"--libs", "--libfiles", "--libnames"}:
                    values = []
                    for library in libraries:
                        path = self.prefix / self.libraries[library]
                        if "--libnames" in deferred:
                            values.append(path.name)
                        elif "--libfiles" in deferred or windows:
                            values.append(str(path))
                        else:
                            values.append("-l" + library)
                    outputs.append(" ".join(render(value) for value in values))
                if "--system-libs" in deferred:
                    outputs.append(" ".join(render(value.replace("${prefix}", str(self.prefix)))
                                            for value in flags["system-libs"]))
        return "\n".join(outputs) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    profile = None
    for arg in list(args):
        if arg.startswith("--profile="):
            profile = arg.partition("=")[2]
            args.remove(arg)
    try:
        sys.stdout.write(Configuration(profile=profile).query(args))
        return 0
    except (ConfigurationError, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"llvm-config: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
