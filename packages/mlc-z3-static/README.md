# mlc-z3-static

`mlc-z3-static` is a Python package that carries native Z3 4.16.0 development
artifacts for build systems. It does not provide Z3 Python bindings.

The wheel contains:

- Z3 C and C++ headers.
- A position-independent static `libz3` (`libz3.a` on Unix-like platforms,
  `.lib` on Windows).
- A shared `libz3`.
- Relocatable CMake and pkg-config metadata for each library flavor, under
  `mlc_z3_static/<kind>/lib/cmake/z3` and `mlc_z3_static/<kind>/lib/pkgconfig`
  for `kind` in `static` and `shared`.

The package is built with scikit-build-core: building a wheel runs
`scripts/prepare_z3_v4_16_0.py`, which downloads the pinned Z3 source archive,
verifies its SHA-256 digest, and builds both library flavors. Source builds are
opt-in (`MLC_Z3_STATIC_ALLOW_SOURCE_BUILD=1`) to avoid accidental long Z3
builds when pip cannot find a matching prebuilt wheel.

## Python Helpers

Build systems can locate the packaged artifacts from Python:

```python
import mlc_z3_static

print(mlc_z3_static.get_cmake_dir("static"))
print(mlc_z3_static.get_cmake_prefix_path("shared"))
print(mlc_z3_static.get_static_library_path())
print(mlc_z3_static.get_shared_library_path())
```

Or from a build script through the configuration CLI:

```bash
python -m mlc_z3_static.config --cmake-dir
python -m mlc_z3_static.config --prefix --kind shared
```

## Downstream CMake Usage

Install the wheel into the Python environment used by the downstream build:

```bash
python -m pip install mlc-z3-static==4.16.0
```

Point CMake at the packaged static Z3 and use Z3's exported target:

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
archive. Use `--kind shared` (or `get_cmake_prefix_path("shared")`) to link the
shared flavor instead; each flavor has its own relocatable CMake prefix. See
`example_project/` for a complete uv-managed consumer.

## Local Build

Build a wheel directly:

```bash
MLC_Z3_STATIC_ALLOW_SOURCE_BUILD=1 python -m build --wheel
```

Use an existing Z3 checkout instead of downloading the pinned archive:

```bash
MLC_Z3_STATIC_ALLOW_SOURCE_BUILD=1 \
MLC_Z3_STATIC_SOURCE_DIR=/path/to/z3 \
python -m build --wheel
```

## Build Release Wheels

From this directory:

```bash
scripts/wheel_manylinux_2_28_v4_16_0.sh
```

```bash
scripts/wheel_macos_v4_16_0.sh
```

The scripts use `uv` for host-side Python tooling, so Debian/Ubuntu system
Python restrictions such as PEP 668 and missing `ensurepip` do not affect the
host CIBW runner or post-build verifier. Both run `cibuildwheel==3.3.1`, retag
Linux wheels as `manylinux_2_28`, and verify each produced wheel from a clean
temporary virtual environment with:

```bash
scripts/wheel_verify.sh wheelhouse/<wheel-file>.whl
```

The verifier installs the wheel, configures a small CMake project against
`mlc_z3_static.get_cmake_prefix_path("static")`, links to `z3::libz3`, runs the
executable, and checks that the executable does not link against a dynamic
`libz3`.

The manylinux script defaults to the host architecture. Set
`MLC_Z3_STATIC_ARCH=x86_64` or `MLC_Z3_STATIC_ARCH=aarch64` to choose explicitly.

On macOS, local CIBW builds require an official python.org CPython installation.
The script defaults to the newest installed python.org CPython only as the build
interpreter. The output wheel is still Python-agnostic and tagged
`py3-none-<platform>`. Override `CIBW_BUILD` to force a specific installed build
interpreter, for example `CIBW_BUILD=cp313-macosx_arm64`.
