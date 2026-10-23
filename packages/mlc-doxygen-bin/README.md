# mlc-doxygen-bin

`mlc-doxygen-bin` builds platform wheels containing the Doxygen command-line
executable. It is intended for Python-driven build systems that want a pinned
Doxygen binary without relying on a system package manager. The pinned Doxygen
release is recorded in [`version.py`](version.py) and exposed at runtime as
`mlc_doxygen_bin.DOXYGEN_VERSION`.

The wheel installs a `doxygen` console script that delegates to the executable
stored inside the Python package.

## Build Wheels

On macOS:

```bash
scripts/wheel_macos.sh
```

On manylinux_2_28:

```bash
scripts/wheel_manylinux_2_28.sh
```

On Windows:

```powershell
scripts\wheel_windows.ps1
```

The scripts run `cibuildwheel==3.3.1` through `uv`. During CIBW's
`before-build` phase, `scripts/prepare_doxygen.py` downloads the pinned
upstream source archive, verifies its SHA-256 digest, builds the CLI executable,
and copies the install tree into `src/mlc_doxygen_bin`.

Build artifacts are written to `wheelhouse/`.

## Platform And Architecture

The Linux and macOS scripts default to the host architecture. Override the
target architecture with:

```bash
MLC_DOXYGEN_BIN_ARCH=aarch64 scripts/wheel_manylinux_2_28.sh
MLC_DOXYGEN_BIN_ARCH=arm64 scripts/wheel_macos.sh
```

Supported values are:

- Linux: `x86_64`, `aarch64`
- macOS: `arm64`, `x86_64`
- Windows: `AMD64`, `ARM64` (defaults to the host's `PROCESSOR_ARCHITECTURE`)

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

On Windows, install Visual Studio Build Tools and `winflexbison3`. The x86
`winflexbison3` tools also work on Windows ARM64 through emulation; they only
generate sources. Doxygen's bundled Windows iconv library is x86/x64 only, so
ARM64 builds compile a pinned static
[win-iconv](https://github.com/win-iconv/win-iconv) for the target and pass it
as `ICONV_DIR` (pass your own `-DICONV_DIR=...` through
`MLC_DOXYGEN_BIN_EXTRA_CMAKE_ARGS` to override).

## Runtime Scope

This package intentionally builds only the Doxygen CLI executable. It does not
bundle `doxywizard`, `doxyindexer`, `doxysearch.cgi`, libclang, Graphviz,
LaTeX, Ghostscript, or PlantUML. Those tools remain external runtime
dependencies for Doxygen features that need them.

## Usage

```bash
python -m pip install mlc-doxygen-bin
doxygen --version
```

Programmatic path lookup is also available:

```python
import mlc_doxygen_bin

print(mlc_doxygen_bin.get_executable_path())
print(mlc_doxygen_bin.metadata())
```

## Bumping the version

[`version.py`](version.py) is the single version source. To move to a new
Doxygen release, edit only that file:

- `DOXYGEN_VERSION`: the upstream release (the Git tag is derived as
  `Release_<major>_<minor>_<patch>`).
- `__version__`: the Python package version; it must equal `DOXYGEN_VERSION`,
  or `DOXYGEN_VERSION` plus a PEP 440 suffix such as `.post1`.
- `DOXYGEN_ARCHIVE_SHA256`: the SHA-256 of the source archive
  `scripts/prepare_doxygen.py` downloads:

  ```bash
  curl -fsSL https://github.com/doxygen/doxygen/releases/download/Release_<X_Y_Z>/doxygen-<X.Y.Z>.src.tar.gz | sha256sum
  ```

Package metadata (through `setup.py`), the build scripts, the default build
directory, and the generated runtime module `mlc_doxygen_bin/_version.py` all
read these values. The publishing workflow's `version_suffix` input runs
`scripts/stamp_version.py --suffix <suffix>`, which rewrites `__version__` in
the build checkout and rejects versions not based on `DOXYGEN_VERSION`.
