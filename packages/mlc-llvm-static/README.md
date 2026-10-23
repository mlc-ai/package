# mlc-llvm-static

An LLVM 23.1.1 development SDK distributed as a Python-version-independent,
platform-specific wheel. Initial verification uses GitHub Releases; PyPI
publishing is an optional manual workflow action.

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

## Install and locate

Install the wheel matching your platform, using a downloaded file or its GitHub
release asset URL:

```bash
python -m pip install /path/to/mlc_llvm_static-<version>-py3-none-<platform>.whl
# Optional: add every standard code-generation backend from the same build.
python -m pip install /path/to/mlc_llvm_static_extra_targets-<version>-py3-none-<platform>.whl
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

The package metadata also defines `mlc-llvm-static[all]` to install the exact
matching add-on when both distributions are available from an index. During
GitHub-release validation, install their wheel paths/URLs explicitly. Once both
distributions are published to PyPI, install the native SDK with
`python -m pip install mlc-llvm-static`, or every standard backend with
`python -m pip install 'mlc-llvm-static[all]'`.
The `all` extra pins the add-on to the base wheel's exact version, and the add-on
pins the base to that same version, including any RC suffix. The base wheel can
be installed on its own.

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

## Builds and GitHub verification

The `Build LLVM static SDK wheels` workflow builds and verifies both wheel
families for Linux x86_64, Linux aarch64, macOS arm64 (14.0+), and Windows AMD64.
Linux builds run in manylinux_2_28; Windows uses the MSVC dynamic CRT (`/MD`).
Relevant pull requests build and validate the wheels. Manual runs publish both
wheel families to PyPI, with `version_suffix` as the only input. Every run
validates all four host platforms. Publishing waits for every host's validation
and checks all eight wheels and their package metadata before uploading. PyPI
receives wheels only; source distributions are built for validation, since these
packages provide a prebuilt SDK.
The SDK is compiled once per host and partitioned into both wheel families.
Separate publishing jobs download their project's validated wheels and do not
build anything. Wait for both jobs to succeed before using the All profile from
the index. Publishing jobs reuse the validated artifacts and can be rerun
independently.

The workflow appends the optional `version_suffix` string to the pinned
`LLVM_VERSION` in `_version.py`, then validates and normalizes it with Python's
packaging version parser:

| `version_suffix` | Both package versions |
| --- | --- |
| Empty (default) | `23.1.1` |
| `rc0` | `23.1.1rc0` |
| `dev0` | `23.1.1.dev0` |
| `post0` | `23.1.1.post0` |

Other valid suffixes, including alpha/beta and combined suffixes, work the same
way. Both distributions, wheel filenames, and exact-version requirements are
stamped together. Cache restores require the exact recipe key; changing the
package suffix reuses the same compiled LLVM SDK.

Python packaging normalizes `23.1.1.rc0` to `23.1.1rc0`. To test an RC from PyPI,
pin it explicitly, for example:

```bash
python -m pip install 'mlc-llvm-static[all]==23.1.1rc0'
```

To enable PyPI publishing, configure a
[trusted publisher](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)
for **each** project using these settings:

| PyPI publisher field | Native SDK | Extra targets |
| --- | --- | --- |
| Project | `mlc-llvm-static` | `mlc-llvm-static-extra-targets` |
| Owner | `mlc-ai` | `mlc-ai` |
| Repository | `package` | `package` |
| Workflow filename | `mlc_llvm_static_wheel.yml` | `mlc_llvm_static_wheel.yml` |
| Environment | `pypi` | `pypi-all-targets` |

For projects that do not exist yet, register
[pending publishers](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
for both names. PyPI requires
[pending publishers to have distinct identities](https://github.com/pypi/warehouse/blob/main/warehouse/oidc/models/github.py)
for the repository/workflow/environment combination; the separate environments above
allow both projects to be registered before their first upload. Existing
projects can share a publisher, but this setup keeps the first release independent
for each project. Use these same environment names in GitHub's environment
settings when configuring protection rules.
Each publishing job requests its own OIDC token; no PyPI API-token secret is
required. After setup, dispatch this workflow with the desired version suffix.
No workflow change is needed. Existing filenames on PyPI cause an error rather
than being silently skipped.

Verification installs the wheel and copies its SDK to a new directory containing
spaces. It checks artifact hashes, `llvm-config` relocation, CMake import paths,
and absence of unrequested tools/shared libraries. A shared consumer then parses
LLVM IR, optimizes it, writes bitcode, and JIT-executes a function returning 42.
The consumer must not depend on dynamic LLVM, zlib, or zstd. Linux also checks
the required GLIBC/GLIBCXX/CXXABI symbol versions against the manylinux baseline.
The probe also round-trips both compression formats, reads compressed ELF DWARF,
and checks its exports, allowing LLVM's two forced GDB JIT hooks on Windows.
CI caches the raw All-target SDK by platform and a fingerprint of the compilation
and graph-generation recipe. Frontend, packaging, and verification changes reuse
that build. Windows packaging uses `llvm-objcopy` on a copy of the raw archives
to remove unreferenced local labels and unused undefined declarations. Public
definitions, relocation/weak-reference targets, linker directive references,
COMDAT section definitions and key symbols, compiler feature flags, debug/PCH
metadata, and unwind data are retained.
Generic `--strip-unneeded` is unsuitable because
it removes COMDAT records required by MSVC's linker. Install LLVM's
`llvm-objcopy` as a build tool or set `MLC_LLVM_STATIC_OBJCOPY` to its path; the
tool is not included in either wheel. The resulting archive hashes and tool
version are included in the SDK fingerprint. The packager rejects any change to
public symbol definitions or non-debug section contents, including code, data,
and unwind information. Windows verification also links every archive member
using `/WHOLEARCHIVE`. All hosts use 7-Zip for stronger standard ZIP DEFLATE
encoding. Linux and macOS packaging fetch an official 7-Zip 26.05 binary with
a pinned SHA-256; Windows uses the installed 7-Zip. Set `MLC_LLVM_STATIC_7ZIP`
to use an existing executable, including for offline packaging. Neither
packaging tool is needed by installed consumers. Recompression runs after
retagging and preserves the unpacked files, permissions, and RECORD hashes. Packaging fails if
either wheel reaches 100,000,000 bytes, leaving no ambiguity between MB and MiB.

A remote compression-only benchmark of the dev2 release measured these savings
over zlib level 9 (decimal MB). Every unpacked file's SHA-256, mode, and timestamp
was identical. This reduces downloads; installed SDK size is unchanged.

| Host | Native: zlib → 7-Zip | Extra targets: zlib → 7-Zip |
| --- | ---: | ---: |
| Linux x86_64 | 64.2 → 61.3 | 34.4 → 32.3 |
| Linux aarch64 | 62.2 → 59.3 | 33.2 → 31.2 |
| macOS arm64 | 48.5 → 46.2 | 25.7 → 24.1 |

An additional Linux aarch64 `objcopy --strip-unneeded` experiment on the eight
largest archives saved 4.58 MB installed but only 0.65 MB compressed (2.5%).
It preserved allocated section bytes and externally defined symbols in those
samples. This transformation is not enabled: it changes object metadata and
requires separate exhaustive native linker validation, unlike lossless ZIP
recompression. Linux/macOS archives retain their original symbols and sections;
no code generation targets or compiler optimizations are removed to save space.

The packager compares native-component library queries with upstream
`llvm-config`. Wheel verification covers Native and All, explicit Native with
the add-on present, and add-on uninstall. It initializes every selected backend
and emits/parses x86_64, AArch64, RISC-V, and WebAssembly objects for All.

Use remote build machines for LLVM compilation. Source builds are explicitly
opt-in to avoid a lengthy accidental build when a wheel is unavailable:

```bash
MLC_LLVM_STATIC_ALLOW_SOURCE_BUILD=1 CMAKE_BUILD_PARALLEL_LEVEL=8 \
  python scripts/build_wheels.py --output wheelhouse
python scripts/verify_split_wheels.py wheelhouse
```

The source archive digests are pinned in `scripts/prepare_llvm.py`. Useful build
overrides:

- `MLC_LLVM_STATIC_SOURCE_CACHE`: reusable directory of downloaded source archives.
- `MLC_LLVM_STATIC_LLVM_SOURCE_DIR`, `MLC_LLVM_STATIC_ZLIB_SOURCE_DIR`, and
  `MLC_LLVM_STATIC_ZSTD_SOURCE_DIR`: explicit source trees for development.
- `MLC_LLVM_STATIC_BUILD_WORK`: node-local directory for source extraction and
  LLVM objects, keeping slow shared filesystems out of compilation.
- `MLC_LLVM_STATIC_PREFIX`: repackage a raw All-target SDK produced by this
  recipe, or a staged Native SDK when invoking the base wheel's build backend.
  Its parent must contain the matching `licenses/` and `staticlib.json`.

Build settings are Release, assertions off, RTTI on, exceptions off, PIC on, and
LTO off. `staticlib.json` records source hashes, selected targets, build settings,
and per-file hashes. Source overrides are development inputs and are not covered
by the pinned archive digests.

Static libraries and generated configuration must stay together. External Clang
versions can compile native objects independently, but Clang producing LLVM IR
for this SDK should use a tested matching LLVM release. Android and ROCm tools
should come from their corresponding vendor toolchains.
