# mlc-llvm-static

An LLVM development SDK packaged as Python-version-independent,
platform-specific wheels for build systems. The pinned LLVM release (23.1.1) is
recorded in [`version.py`](version.py). The optional
`mlc-llvm-static-extra-targets` add-on in [`extra-targets/`](extra-targets)
adds the remaining code-generation backends.

The SDK contains:

- PIC LLVM static libraries with native objects, without LTO bitcode.
- LLVM headers, including the matching generated configuration headers.
- Relocatable LLVM CMake exports and a Python `llvm-config` compatibility frontend.
- Static zlib 1.3.1 and zstd 1.5.7, with their headers and license notices.
- The matching ORC runtime archive on Linux.

The base wheel contains X86 on x86_64/AMD64 hosts and AArch64 on arm64/aarch64
hosts. The exact-version `mlc-llvm-static-extra-targets` wheel adds all other
standard LLVM backends. Both are partitioned from one All-target build and own
disjoint files in the same `static/lib` directory. Build fingerprints reject
mismatched base/add-on artifacts, including different builds of the same version.
Experimental LLVM backends are excluded.

Installing the add-on selects the All profile automatically; removing it
restores Native without overwriting base-owned files. Set
`MLC_LLVM_STATIC_PROFILE=native` or `all` for an explicit profile. CMake users
can also set `-DMLC_LLVM_STATIC_PROFILE=native` or `all`. Generated target
initialization headers, target-availability macros, CMake exports, and the
configuration frontend use the same selection. Archives remain host-specific:
an x86_64 wheel's AArch64 backend is x86_64 code that generates AArch64 objects.
Cross-platform linking still needs a suitable linker, sysroot, and target runtime.
Other LLVM tools, Clang, LLD, MLIR, and shared LLVM libraries are excluded.
Optional compilers and vendor toolchains remain separate dependencies.
Optional DIA SDK, libpfm, ICU, iconv, and language-binding integrations are
disabled to keep the SDK independent of packages installed on its build host.

The wheel is a **build dependency**. Statically linked downstream wheels do not
need to depend on this SDK at runtime.

See the [dependency audit](DEPENDENCIES.md) for optional-feature consequences,
platform libraries, transitive linking, and requirements for additional backends.
libxml2 is needed for LLVM's Windows manifest merger, which this profile disables;
it is not required by the selected IR/code-generation/ORC paths. Host system and
C++ runtimes remain downstream dependencies.

## Usage

Install the native SDK, then add every standard code-generation backend if needed:

```bash
python -m pip install mlc-llvm-static
python -m pip install 'mlc-llvm-static[all]'
python -m mlc_llvm_static.config --prefix
python -m mlc_llvm_static.config --cmake-dir
python -m mlc_llvm_static.config --llvm-config
```

```python
import mlc_llvm_static as llvm

print(llvm.get_prefix())
print(llvm.get_cmake_dir())
print(llvm.get_llvm_config())
print(llvm.metadata()["targets"])
```

The `all` extra pins the add-on to the base wheel's exact version, and the add-on
pins the base to that same version, including any RC suffix. The base wheel can
be installed on its own. Downloaded wheel files can also be passed to
`pip install`; install both matching wheels explicitly when using files.

The frontend supports `--profile=native|all|auto` and normal static LLVM queries,
including components, compiler flags, library paths/order, and system libraries.
It reads a build-generated component graph and requires Python 3.10+ at build
time. The upstream executable is retained only in the build/cache for comparison.
On Unix, `static/bin/llvm-config` is a standalone Python script; on Windows,
`get_llvm_config()` locates pip's console launcher in the Python environment.
For a copied SDK prefix on either platform, run
`python /copied/prefix/bin/llvm-config.py`. A copied Windows SDK is not a
standalone executable toolchain.

Pass `LLVM_DIR` explicitly so a system or Conda LLVM installation does not
accidentally supply different headers, libraries, or exports:

```bash
cmake -S . -B build \
  -DLLVM_DIR="$(python -m mlc_llvm_static.config --cmake-dir)" \
  -DCMAKE_PREFIX_PATH="$(python -m mlc_llvm_static.config --prefix)" \
  -DZLIB_USE_STATIC_LIBS=ON
```

```cmake
find_package(LLVM CONFIG REQUIRED)
llvm_map_components_to_libnames(LLVM_LIBS Core OrcJIT Support native)
target_include_directories(my_target SYSTEM PRIVATE ${LLVM_INCLUDE_DIRS})
separate_arguments(LLVM_FLAGS NATIVE_COMMAND "${LLVM_DEFINITIONS}")
target_compile_options(my_target PRIVATE ${LLVM_FLAGS})
target_link_libraries(my_target PRIVATE ${LLVM_LIBS})
```

For TIRx's existing command-based discovery, set `TVM_TIRX_USE_LLVM` to the result
of `--llvm-config` followed by `--link-static`. For the FFI ORC JIT addon, set
`LLVM_PREFIX` to the result of `--prefix`. Linux ORC runtime archives live under
`lib/clang/<LLVM-major>/lib/`, matching the addon's discovery convention.

## Build from source

Use remote build machines for LLVM compilation. Source builds are explicitly
opt-in to avoid a lengthy accidental build when a wheel is unavailable:

```bash
MLC_LLVM_STATIC_ALLOW_SOURCE_BUILD=1 CMAKE_BUILD_PARALLEL_LEVEL=8 \
  python scripts/build_wheels.py --output wheelhouse
python scripts/verify_split_wheels.py wheelhouse
```

`build_wheels.py` compiles one All-target SDK per host and partitions it into
the base and add-on wheels. The LLVM source archive digest is pinned in
`version.py`; the zlib and zstd digests are pinned in `scripts/prepare_llvm.py`.
Useful build overrides:

- `MLC_LLVM_STATIC_SOURCE_CACHE`: reusable directory of downloaded source archives.
- `MLC_LLVM_STATIC_LLVM_SOURCE_DIR`, `MLC_LLVM_STATIC_ZLIB_SOURCE_DIR`, and
  `MLC_LLVM_STATIC_ZSTD_SOURCE_DIR`: explicit source trees for development.
- `MLC_LLVM_STATIC_BUILD_WORK`: node-local directory for source extraction and
  LLVM objects, keeping slow shared filesystems out of compilation.
- `MLC_LLVM_STATIC_PREFIX`: repackage a raw All-target SDK produced by this
  recipe, or a staged Native SDK when invoking the base wheel's build backend.
  Its parent must contain the matching `licenses/` and `staticlib.json`.
- `MLC_LLVM_STATIC_OBJCOPY` and `MLC_LLVM_STATIC_7ZIP`: packaging tools (see
  [Packaging details](#packaging-details)).

Build settings are Release, assertions off, RTTI off, exceptions off, PIC on, and
LTO off. `staticlib.json` records source hashes, selected targets, build settings,
and per-file hashes. Source overrides are development inputs and are not covered
by the pinned archive digests.

LLVM retains its upstream Release section defaults. Its bundled compression
libraries use separate function/data sections on Linux and add `/Gw` on Windows,
where Release `/O2` already enables function-level linking. The ORC runtime keeps its
upstream build flags. macOS retains native Mach-O dead-stripping behavior. Consumers must enable their linker's dead-code
removal to discard unused sections. Code using C++ RTTI (`dynamic_cast` or
`typeid`) on LLVM classes is unsupported; compile LLVM-facing code consistently
with the SDK's RTTI setting (reported by `llvm-config --has-rtti` and
`LLVM_ENABLE_RTTI` in the CMake package).

Static libraries and generated configuration must stay together. External Clang
versions can compile native objects independently, but Clang producing LLVM IR
for this SDK should use a tested matching LLVM release. Android and ROCm tools
should come from their corresponding vendor toolchains.

## Release wheels

The `Publish mlc-llvm-static wheels` workflow
([`mlc_llvm_static_wheel.yml`](../../.github/workflows/mlc_llvm_static_wheel.yml))
builds and verifies both wheel families for Linux x86_64, Linux aarch64, macOS
arm64 (14.0+), and Windows AMD64/ARM64. See the
[root README](../../README.md#when-workflows-run) for when it runs.

- Linux builds run in manylinux_2_28.
- Windows uses the MSVC dynamic CRT (`/MD`) and builds LLVM with `clang-cl`
  against the MSVC headers, libraries, and linker. `clang-cl` objects carry
  about half the sections and symbols of MSVC's, which keeps the wheels well
  under PyPI's size limit, and MSVC's ARM64 optimizer cannot build the AMDGPU
  backend. Consumer verification uses MSVC on both Windows hosts, so MSVC
  projects link the `clang-cl` libraries. Windows ARM64 uses a native Windows 11
  runner and ARM64 Python; its wheels use the `win_arm64` platform tag.
- The SDK is compiled once per host and partitioned into both wheel families.
  CI caches the raw All-target SDK by platform and a fingerprint of the
  compilation and graph-generation recipe, including explicit `CC`/`CXX`
  overrides, so frontend, packaging, and verification changes reuse that build.
- Both packages publish wheels only, since they provide a prebuilt SDK.

### Publishing to PyPI

Manual runs take `version_suffix`, `publish` (*Publish to PyPI*, off by
default), and `repository_url` (a custom PyPI-compatible repository URL; empty
means PyPI), plus `publish_packages` (`both` by default, or only
`mlc-llvm-static` or `mlc-llvm-static-extra-targets`, for example to finish a
release where one upload failed). Publishing waits for every host's validation
and checks the complete wheel set and its metadata. Separate jobs then upload
each project's validated wheels without rebuilding; they can be rerun
independently. Wait for both jobs to succeed before using the All profile from
the index. Existing
filenames on PyPI cause an error rather than being silently skipped.

The workflow appends `version_suffix` to `LLVM_VERSION` and normalizes it with
Python's packaging version parser. Both distributions, wheel filenames, and
exact-version requirements are stamped together, and the compiled SDK cache is
reused:

| `version_suffix` | Both package versions |
| --- | --- |
| Empty (default) | `23.1.1` |
| `rc0` | `23.1.1rc0` |
| `dev0` | `23.1.1.dev0` |
| `post0` | `23.1.1.post0` |

Python packaging normalizes `23.1.1.rc0` to `23.1.1rc0`. To test an RC from
PyPI, pin it explicitly:

```bash
python -m pip install 'mlc-llvm-static[all]==23.1.1rc0'
```

Each project needs a
[trusted publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/);
no API-token secret is required:

| PyPI publisher field | Native SDK | Extra targets |
| --- | --- | --- |
| Project | `mlc-llvm-static` | `mlc-llvm-static-extra-targets` |
| Owner | `mlc-ai` | `mlc-ai` |
| Repository | `package` | `package` |
| Workflow filename | `mlc_llvm_static_wheel.yml` | `mlc_llvm_static_wheel.yml` |
| Environment | `pypi` | `pypi-extra-targets` |

For projects that do not exist yet, register
[pending publishers](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).
PyPI requires
[distinct identities](https://github.com/pypi/warehouse/blob/main/warehouse/oidc/models/github.py)
for pending publishers, which is why the two projects use separate
environments. Use the same environment names in GitHub's environment settings
when configuring protection rules.

### Verification

Verification installs the wheel and copies its SDK to a new directory containing
spaces. It checks artifact hashes, `llvm-config` relocation, CMake import paths,
and absence of unrequested tools/shared libraries. A shared consumer then parses
LLVM IR, optimizes it, writes bitcode, and JIT-executes a function returning 42.
The consumer must not depend on dynamic LLVM, zlib, or zstd. Linux also checks
the required GLIBC/GLIBCXX/CXXABI symbol versions against the manylinux baseline.
The probe also round-trips both compression formats, reads compressed ELF DWARF,
and checks its exports, allowing LLVM's two forced GDB JIT hooks on Windows.

The packager compares native-component library queries with upstream
`llvm-config`. Wheel verification covers Native and All, explicit Native with
the add-on present, and add-on uninstall. It initializes every selected backend
and emits/parses x86_64, AArch64, RISC-V, and WebAssembly objects for All.
Windows verification also links every archive member using `/WHOLEARCHIVE`.

### Packaging details

Windows packaging uses `llvm-objcopy` on a copy of the raw archives to remove
unreferenced local labels and unused undefined declarations. Public
definitions, relocation/weak-reference targets, linker directive references,
COMDAT section definitions and key symbols, compiler feature flags, debug/PCH
metadata, and unwind data are retained. Generic `--strip-unneeded` is
unsuitable because it removes COMDAT records required by MSVC's linker. Install
LLVM's `llvm-objcopy` as a build tool or set `MLC_LLVM_STATIC_OBJCOPY` to its
path. The resulting archive hashes and tool version are included in the SDK
fingerprint. The packager rejects any change to public symbol definitions or
non-debug section contents, including code, data, and unwind information.
Linux/macOS archives retain their original symbols and sections.

All hosts recompress wheels with 7-Zip's standard ZIP DEFLATE encoder. Linux
and macOS packaging fetch an official 7-Zip 26.05 binary with a pinned SHA-256;
Windows uses the installed 7-Zip. Set `MLC_LLVM_STATIC_7ZIP` to use an existing
executable, including for offline packaging. Recompression runs after retagging
and preserves the unpacked files, permissions, and RECORD hashes, so it reduces
downloads without changing the installed SDK. Packaging fails if either wheel
reaches 100,000,000 bytes. Neither packaging tool is needed by installed
consumers or included in either wheel.

## Tests

The pytest suite under `tests/python/` covers the build scripts and the Python
frontend without building LLVM. From this directory:

```bash
python -m pip install pytest packaging
pytest
```

Wheel verification on real builds is described in [Verification](#verification).

## License

`LICENSE` is LLVM's license (Apache-2.0 with LLVM exceptions). The wheel also
bundles zlib and zstd, so its metadata declares
`Apache-2.0 WITH LLVM-exception AND Zlib AND BSD-3-Clause`, and each
component's license notice is installed under `mlc_llvm_static/licenses/`.

## Bumping the version

[`version.py`](version.py) is the single version source for both
distributions. To move to a new LLVM release, edit only that file:

- `LLVM_VERSION`: the upstream release (the source archive is
  `llvm-project-<LLVM_VERSION>.src.tar.xz` from the `llvmorg-<LLVM_VERSION>`
  GitHub release).
- `__version__`: the Python package version; it must equal `LLVM_VERSION`, or
  `LLVM_VERSION` plus a PEP 440 suffix such as `.post1`.
- `LLVM_ARCHIVE_SHA256`: the SHA-256 of that source archive.

Then run `python scripts/stamp_version.py` to update the exact-version
requirements between `mlc-llvm-static` and `mlc-llvm-static-extra-targets` in
both `pyproject.toml` files. The build generates the runtime
`mlc_llvm_static/_version.py` from `version.py`; it is not checked in.
