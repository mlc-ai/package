# mlc-llvm-static

An LLVM 23.1.1 development SDK distributed as a Python-version-independent,
platform-specific wheel. Initial verification uses GitHub Releases; there is no
PyPI publishing step.

The SDK contains:

- PIC LLVM static libraries with native objects, without LTO bitcode.
- LLVM headers, including the matching generated configuration headers.
- Relocatable LLVM CMake exports and the matching `llvm-config` executable.
- Static zlib 1.3.1 and zstd 1.5.7, with their headers and license notices.
- The matching ORC runtime archive on Linux.

The first release matches the existing native-target LLVM archives: X86 on
x86_64/AMD64 hosts and AArch64 on arm64/aarch64 hosts. Additional code-generation
backends are explicit build overrides, rather than part of the initial release.
Other LLVM tools, Clang, LLD, MLIR, and shared LLVM libraries are excluded.
Optional compilers and vendor toolchains remain separate dependencies.
Optional DIA SDK, libpfm, ICU, iconv, and language-binding integrations are
disabled to keep the SDK independent of packages installed on its build host.

The wheel is a **build dependency**. Statically linked downstream wheels do not
need to depend on this SDK at runtime.

## Install and locate

Install the wheel matching your platform, using a downloaded file or its GitHub
release asset URL:

```bash
python -m pip install /path/to/mlc_llvm_static-<version>-py3-none-<platform>.whl
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
`lib/clang/23/lib/`, matching the addon's discovery convention.

## Builds and GitHub verification

The `Build LLVM static SDK wheels` workflow builds and verifies Linux x86_64,
Linux aarch64, macOS arm64 (14.0+), and Windows AMD64 wheels. Linux builds run in
manylinux_2_28; Windows uses the MSVC dynamic CRT (`/MD`). It runs for relevant
pull requests and can also be dispatched manually. `publish_release=true`
creates a **new draft prerelease** containing all four verified wheels and
`SHA256SUMS`. It does not overwrite an existing release or publish to PyPI.

Verification installs the wheel and copies its SDK to a new directory containing
spaces. It checks artifact hashes, `llvm-config` relocation, CMake import paths,
and absence of unrequested tools/shared libraries. A shared consumer then parses
LLVM IR, optimizes it, writes bitcode, and JIT-executes a function returning 42.
The consumer must not depend on dynamic LLVM, zlib, or zstd. Linux also checks
the required GLIBC/GLIBCXX/CXXABI symbol versions against the manylinux baseline.
CI caches the compiled SDK by platform, package version, and build-recipe files.
Verification-only changes repackage and recheck that SDK without recompiling
LLVM. A cached SDK is always verified before it becomes a release artifact.

Use remote build machines for LLVM compilation. Source builds are explicitly
opt-in to avoid a lengthy accidental build when a wheel is unavailable:

```bash
MLC_LLVM_STATIC_ALLOW_SOURCE_BUILD=1 CMAKE_BUILD_PARALLEL_LEVEL=8 \
  python -m build --wheel
```

The source archive digests are pinned in `scripts/prepare_llvm.py`. Useful build
overrides:

- `MLC_LLVM_STATIC_SOURCE_CACHE`: reusable directory of downloaded source archives.
- `MLC_LLVM_STATIC_LLVM_SOURCE_DIR`, `MLC_LLVM_STATIC_ZLIB_SOURCE_DIR`, and
  `MLC_LLVM_STATIC_ZSTD_SOURCE_DIR`: explicit source trees for development.
- `MLC_LLVM_STATIC_TARGETS`: semicolon-separated targets (default `Native`);
  use a distinct package version when adding other backends.
- `MLC_LLVM_STATIC_PREFIX`: package an SDK already produced by this build script.
  Its parent must also contain the generated `licenses/` and `staticlib.json`.

Build settings are Release, assertions off, RTTI on, exceptions off, PIC on, and
LTO off. `staticlib.json` records source hashes, selected targets, build settings,
and per-file hashes. Source overrides are development inputs and are not covered
by the pinned archive digests.

Static libraries and generated configuration must stay together. External Clang
versions can compile native objects independently, but Clang producing LLVM IR
for this SDK should use a tested matching LLVM release. Android and ROCm tools
should come from their corresponding vendor toolchains.
