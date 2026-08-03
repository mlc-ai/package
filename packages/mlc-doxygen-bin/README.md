# mlc-doxygen-bin

`mlc-doxygen-bin` builds platform wheels containing the Doxygen 1.17.0 command-line
executable. It is intended for Python-driven build systems that want a pinned
Doxygen binary without relying on a system package manager.

The wheel installs a `doxygen` console script that delegates to the executable
stored inside the Python package.

## Build Wheels

For Doxygen 1.17.0 on macOS:

```bash
scripts/wheel_macos_v1_17_0.sh
```

For Doxygen 1.17.0 on manylinux_2_28:

```bash
scripts/wheel_manylinux_2_28_v1_17_0.sh
```

For Doxygen 1.17.0 on Windows:

```powershell
scripts\wheel_windows_v1_17_0.ps1
```

The scripts run `cibuildwheel==3.3.1` through `uv`. During CIBW's
`before-build` phase, `scripts/prepare_doxygen_v1_17_0.py` downloads the pinned
upstream source archive, verifies its SHA-256 digest, builds the CLI executable,
and copies the install tree into `src/mlc_doxygen_bin`.

Build artifacts are written to `wheelhouse/`.

## Platform And Architecture

The Linux and macOS scripts default to the host architecture. Override the
target architecture with:

```bash
MLC_DOXYGEN_BIN_ARCH=aarch64 scripts/wheel_manylinux_2_28_v1_17_0.sh
MLC_DOXYGEN_BIN_ARCH=arm64 scripts/wheel_macos_v1_17_0.sh
```

Supported values are:

- Linux: `x86_64`, `aarch64`
- macOS: `arm64`, `x86_64`
- Windows: `AMD64`

## Build Dependencies

The build needs CMake, Ninja, Python, Flex, Bison, and a C++ compiler. The
manylinux script installs Bison from the manylinux distribution and builds a
pinned Flex 2.6.4 into `/usr/local`, because AlmaLinux 8's Flex 2.6.1 can fail
while generating Doxygen's large scanners.

On macOS, use Homebrew Flex and Bison if the Apple-provided versions are too
old:

```bash
brew install flex bison
```

The macOS script automatically prepends Homebrew's `flex` and `bison`
directories to `PATH` when Homebrew is available.

On Windows, install Visual Studio Build Tools and `winflexbison3`.

## Runtime Scope

This package intentionally builds only the Doxygen CLI executable. It does not
bundle `doxywizard`, `doxyindexer`, `doxysearch.cgi`, libclang, Graphviz,
LaTeX, Ghostscript, or PlantUML. Those tools remain external runtime
dependencies for Doxygen features that need them.

## Usage

```bash
python -m pip install mlc-doxygen-bin==1.17.0
doxygen --version
```

Programmatic path lookup is also available:

```python
import mlc_doxygen_bin

print(mlc_doxygen_bin.get_executable_path())
print(mlc_doxygen_bin.metadata())
```
