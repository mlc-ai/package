# Build environment

Package wheel workflows use this action after checkout to default
`CMAKE_BUILD_PARALLEL_LEVEL` to the runner's available CPU count. Linux uses CPU
affinity when available; other hosts use the system CPU count.

An existing `CMAKE_BUILD_PARALLEL_LEVEL` takes precedence, so memory-constrained
runners can select a lower limit. The action exports the setting through
`GITHUB_ENV` and logs the selected value.

The LLVM Docker build and `docker/bash.sh` forward the setting into containers.
The Z3 and Doxygen workflows also include it in cibuildwheel's environment for
each platform. Native Windows and macOS builds inherit it directly.
