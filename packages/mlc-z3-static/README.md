# mlc-z3-static

`mlc-z3-static` builds platform wheels containing Z3 4.16.0 development artifacts:

- C and C++ headers.
- A position-independent static `libz3`.
- A shared `libz3`.
- CMake and pkg-config metadata for each library flavor.

The package does not provide Z3 Python bindings. It is intended for native
build systems that want to consume pinned Z3 libraries from a Python wheel.

## Build Wheels

From this directory:

```bash
scripts/wheel_macos_v4_16_0.sh
```

```bash
scripts/wheel_manylinux_2_28_v4_16_0.sh
```

The scripts use `uv` for host-side Python tooling, so Debian/Ubuntu system
Python restrictions such as PEP 668 and missing `ensurepip` do not affect the
host CIBW runner or post-build verifier.

The manylinux script defaults to the host architecture. Set
`MLC_Z3_STATIC_ARCH=x86_64` or `MLC_Z3_STATIC_ARCH=aarch64` to choose explicitly.

On macOS, local CIBW builds require an official python.org CPython installation.
The script defaults to the newest installed python.org CPython only as the build
interpreter. The output wheel is still Python-agnostic and must be tagged
`py3-none-<platform>`. Override `CIBW_BUILD` to force a specific installed build
interpreter, for example `CIBW_BUILD=cp313-macosx_arm64`.

Both scripts run `cibuildwheel==3.3.1` through `uv tool run`. During CIBW's
`before-build` phase, `scripts/prepare_z3_v4_16_0.py` downloads the source
archive for the pinned Z3 commit, verifies its SHA-256 digest, builds static
and shared installs, and copies both prefixes into `src/mlc_z3_static`.

After CIBW finishes, each script verifies the produced wheel from a clean
temporary virtual environment by calling:

```bash
scripts/wheel_verify.sh wheelhouse/<wheel-file>.whl
```

The verifier installs the wheel, configures a small CMake project against
`mlc_z3_static.get_cmake_prefix_path("static")`, links to `z3::libz3`, runs the
executable, and checks that the executable does not link against a dynamic
`libz3`.

## Python Helpers

```python
import mlc_z3_static

print(mlc_z3_static.get_include_dir("static"))
print(mlc_z3_static.get_library_path("static"))
print(mlc_z3_static.get_library_path("shared"))
print(mlc_z3_static.get_cmake_prefix_path("shared"))
```

Each flavor has its own relocatable CMake prefix:

```bash
cmake -S . -B build \
  -DCMAKE_PREFIX_PATH="$(python -c 'import mlc_z3_static as z; print(z.get_cmake_prefix_path("static"))')"
```

## Downstream CMake Usage

Install the wheel into the Python environment used by the downstream build:

```bash
python -m pip install mlc-z3-static==4.16.0
```

Configure the downstream CMake project with the packaged static Z3 prefix:

```bash
MLC_Z3_STATIC_PREFIX="$(python -c 'import mlc_z3_static as z; print(z.get_cmake_prefix_path("static"))')"

cmake -S . -B build \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="${MLC_Z3_STATIC_PREFIX}"
```

Then use Z3's exported CMake target:

```cmake
cmake_minimum_required(VERSION 3.20)
project(my_z3_consumer LANGUAGES C CXX)

find_package(Z3 CONFIG REQUIRED)

add_executable(my_z3_consumer main.cpp)
target_link_libraries(my_z3_consumer PRIVATE z3::libz3)
target_compile_features(my_z3_consumer PRIVATE cxx_std_20)
```

Use the static prefix explicitly when you want static linking. The package also
contains a shared-library prefix, available through:

```bash
python -c 'import mlc_z3_static as z; print(z.get_cmake_prefix_path("shared"))'
```

Z3 is implemented in C++, so even C-only consumers should enable CXX in the
CMake project and let CMake link through a C++ linker when using the static
archive. To avoid accidentally finding a system Z3 first, pass the package
prefix before other entries in `CMAKE_PREFIX_PATH` or pass the exact CMake
package directory:

```bash
cmake -S . -B build \
  -DZ3_DIR="$(python -c 'import mlc_z3_static as z; print(z.get_cmake_dir("static"))')"
```
