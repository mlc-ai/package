# mlc-z3-static

Native Z3 development artifacts (headers, a static library, and CMake
metadata) packaged as Python wheels for build systems. It does not provide Z3
Python bindings. The pinned Z3 release is recorded in
[`version.py`](version.py) and exposed at runtime as
`mlc_z3_static.Z3_VERSION`, `mlc_z3_static.Z3_TAG`, and
`mlc_z3_static.Z3_COMMIT`.

The wheel contains:

- Z3 C and C++ headers.
- A position-independent static `libz3` (`libz3.a` on Unix-like platforms,
  `.lib` on Windows).
- Relocatable CMake and pkg-config metadata under
  `mlc_z3_static/static/lib/cmake/z3` and `mlc_z3_static/static/lib/pkgconfig`.

Prebuilt wheels are published to PyPI for common platforms; elsewhere pip
builds from the sdist (see [Build from source](#build-from-source)).

## Usage

```bash
python -m pip install mlc-z3-static
```

Build systems can locate the packaged artifacts from Python:

```python
import mlc_z3_static

print(mlc_z3_static.get_cmake_dir("static"))
print(mlc_z3_static.get_cmake_prefix_path())
print(mlc_z3_static.get_static_library_path())
```

Or from a build script through the configuration CLI:

```bash
python -m mlc_z3_static.config --cmake-dir
python -m mlc_z3_static.config --prefix
```

### CMake

Install the wheel into the Python environment used by the downstream build,
then point CMake at the packaged static Z3 and use Z3's exported target:

```bash
cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DZ3_DIR="$(python -m mlc_z3_static.config --cmake-dir)"
```

```cmake
cmake_minimum_required(VERSION 3.20)
project(my_z3_consumer LANGUAGES C CXX)

find_package(Z3 CONFIG REQUIRED)

add_executable(my_z3_consumer main.cpp)
target_link_libraries(my_z3_consumer PRIVATE z3::libz3)
target_compile_features(my_z3_consumer PRIVATE cxx_std_20)
```

Or resolve the directory from inside CMake:

```cmake
find_package(Python3 COMPONENTS Interpreter REQUIRED)
execute_process(
  COMMAND "${Python3_EXECUTABLE}" -m mlc_z3_static.config --cmake-dir
  OUTPUT_STRIP_TRAILING_WHITESPACE
  OUTPUT_VARIABLE Z3_DIR
)
find_package(Z3 CONFIG REQUIRED)
```

Z3 is implemented in C++, so even C-only consumers should enable CXX in the
CMake project and let CMake link through a C++ linker when using the static
archive. No shared Z3 library or DLL is bundled. See
`example_project/` for a complete uv-managed consumer.

## Build from source

The package is built with scikit-build-core: building a wheel runs
`scripts/prepare_z3.py`, which downloads the pinned Z3 source archive, verifies
its SHA-256 digest, and builds the static library.

This needs a C++20 compiler with `<format>` support (Z3 5.x requires it; e.g.
GCC >= 13, Clang >= 17, Visual Studio 2022), Python, and network access to
download the source archive. CMake (>= 3.26) and Ninja are pulled in as build
requirements. A static Z3 build takes a while; set `CMAKE_BUILD_PARALLEL_LEVEL`
to use more cores:

```bash
CMAKE_BUILD_PARALLEL_LEVEL=8 python -m pip install --no-binary mlc-z3-static mlc-z3-static
```

Build a wheel from a checkout:

```bash
python -m build --wheel
```

Use an existing Z3 checkout instead of downloading the pinned archive:

```bash
MLC_Z3_STATIC_SOURCE_DIR=/path/to/z3 python -m build --wheel
```

## Release wheels

The `Publish mlc-z3-static wheels` workflow
([`mlc_z3_static_wheel.yml`](../../.github/workflows/mlc_z3_static_wheel.yml))
builds `py3-none` wheels for manylinux_2_28
(`x86_64`, `aarch64`), macOS (`arm64`, `x86_64`), and Windows (`AMD64`,
`ARM64`). On Windows the inner Z3 build uses the same Visual Studio platform
(`-A x64` or `-A ARM64`) as the wheel being built. GNU and Clang builds on
non-Apple platforms use `-ffunction-sections -fdata-sections`; MSVC builds use
`/Gy /Gw` to package functions and global data in individual COMDATs, together
with `/Zc:inline` to omit unused inline COMDATs. Mach-O already provides
function/data granularity for dead stripping. These settings preserve the
static linking interface and let consumers discard unused code and data when
they enable linker garbage collection, such as `--gc-sections`, `/OPT:REF`, or
`-dead_strip` on the corresponding platform. The package does not impose
consumer link options, and section granularity can increase archive size even
when it reduces the linked binary. See the
[root README](../../README.md#when-workflows-run) for when it runs and how to
publish.

To build release wheels locally, from this directory:

```bash
scripts/wheel_manylinux_2_28.sh
```

```bash
scripts/wheel_macos.sh
```

```powershell
scripts\wheel_windows.ps1
```

The scripts use `uv` for host-side Python tooling, so Debian/Ubuntu system
Python restrictions such as PEP 668 and missing `ensurepip` do not affect the
host CIBW runner. They run `cibuildwheel==3.3.1`, which tests each wheel in a
clean virtual environment with the pytest suite (see [Tests](#tests)). The
manylinux script retags Linux wheels as `manylinux_2_28`. Wheels are written
to `wheelhouse/`.

The manylinux script defaults to the host architecture. Set
`MLC_Z3_STATIC_ARCH=x86_64` or `MLC_Z3_STATIC_ARCH=aarch64` to choose explicitly.

On macOS, local CIBW builds require an official python.org CPython installation.
The script defaults to the newest installed python.org CPython only as the build
interpreter. The output wheel is still Python-agnostic and tagged
`py3-none-<platform>`. Override `CIBW_BUILD` to force a specific installed build
interpreter, for example `CIBW_BUILD=cp313-macosx_arm64`.

## Tests

The pytest suite under `tests/python/` exercises the installed package. It
checks the version metadata, artifact paths, and the config CLI, and builds,
links, and runs a small CMake consumer against `z3::libz3`, checking that it
does not link a dynamic `libz3` (this needs a C++ compiler). From this
directory:

```bash
python -m pip install ".[test]"   # or: python -m pip install <wheel> pytest
pytest
```

Run pytest against an installed wheel; the tests import the installed
package, not `python/`. cibuildwheel runs the same suite on every built wheel.

## License

This package is distributed under the MIT License, the license of the Z3
artifacts it bundles. `LICENSE` is a verbatim copy of Z3's upstream
`LICENSE.txt`, so this directory and its sdist are self-contained. The wheel
also carries the license copied during packaging from the SHA-256-verified
upstream source archive as `mlc_z3_static/licenses/LICENSE-Z3.txt`; the build
fails if that file is missing.

## Bumping the version

[`version.py`](version.py) is the single version source. To move to a new Z3
release, edit only that file:

- `Z3_VERSION`: the upstream release (the Git tag is derived as
  `z3-<Z3_VERSION>`).
- `__version__`: the Python package version; it must equal `Z3_VERSION`, or
  `Z3_VERSION` plus a PEP 440 suffix such as `.post1`.
- `Z3_COMMIT`: the commit the release tag points to:

  ```bash
  gh api repos/Z3Prover/z3/commits/z3-<Z3_VERSION> --jq .sha
  ```

- `Z3_ARCHIVE_SHA256`: the SHA-256 of the archive `scripts/prepare_z3.py`
  downloads:

  ```bash
  curl -fsSL https://github.com/Z3Prover/z3/archive/<Z3_COMMIT>.tar.gz | sha256sum
  ```

Package metadata, the build scripts, the default build directory, and the
generated runtime module `mlc_z3_static/_version.py` all read these values.
The publishing workflow's `version_suffix` input runs
`scripts/stamp_version.py --suffix <suffix>`, which rewrites `__version__` in
the build checkout and rejects versions not based on `Z3_VERSION`.
