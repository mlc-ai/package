#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${project_dir}"

if [[ "$(uname -s)" != "Linux" ]]; then
  echo "wheel_manylinux_2_28_v1_17_0.sh must run on Linux with Docker available" >&2
  exit 1
fi

host_arch="$(uname -m)"
if [[ "${host_arch}" == "arm64" ]]; then
  host_arch="aarch64"
fi

: "${MLC_DOXYGEN_BIN_ARCH:=${host_arch}}"
case "${MLC_DOXYGEN_BIN_ARCH}" in
  x86_64|aarch64) ;;
  *)
    echo "Unsupported manylinux architecture: ${MLC_DOXYGEN_BIN_ARCH}" >&2
    exit 1
    ;;
esac

if command -v nproc >/dev/null 2>&1; then
  cpu_count="$(nproc)"
else
  cpu_count="2"
fi

: "${CMAKE_BUILD_PARALLEL_LEVEL:=${cpu_count}}"
: "${MLC_DOXYGEN_BIN_PLAT_NAME:=manylinux_2_28_${MLC_DOXYGEN_BIN_ARCH}}"
: "${MLC_DOXYGEN_BIN_TOOLS_PREFIX:=/usr/local}"

export CIBW_BUILD="${CIBW_BUILD:-cp311-manylinux_${MLC_DOXYGEN_BIN_ARCH}}"
export CIBW_ARCHS_LINUX="${CIBW_ARCHS_LINUX:-${MLC_DOXYGEN_BIN_ARCH}}"
export CIBW_MANYLINUX_X86_64_IMAGE="${CIBW_MANYLINUX_X86_64_IMAGE:-manylinux_2_28}"
export CIBW_MANYLINUX_AARCH64_IMAGE="${CIBW_MANYLINUX_AARCH64_IMAGE:-manylinux_2_28}"
export CIBW_BUILD_VERBOSITY="${CIBW_BUILD_VERBOSITY:-1}"
export CIBW_ENVIRONMENT="${CIBW_ENVIRONMENT:-MLC_DOXYGEN_BIN_PLAT_NAME='${MLC_DOXYGEN_BIN_PLAT_NAME}' CMAKE_BUILD_PARALLEL_LEVEL='${CMAKE_BUILD_PARALLEL_LEVEL}' MLC_DOXYGEN_BIN_TOOLS_PREFIX='${MLC_DOXYGEN_BIN_TOOLS_PREFIX}' FLEX_EXECUTABLE='${MLC_DOXYGEN_BIN_TOOLS_PREFIX}/bin/flex' BISON_EXECUTABLE='/usr/bin/bison'}"

scripts/cibuildwheel_run.sh linux wheelhouse .

shopt -s nullglob
wheels=(wheelhouse/*-py3-none-"${MLC_DOXYGEN_BIN_PLAT_NAME}".whl)
if [[ "${#wheels[@]}" -eq 0 ]]; then
  echo "No ${MLC_DOXYGEN_BIN_PLAT_NAME} wheels found in wheelhouse" >&2
  exit 1
fi
for wheel in "${wheels[@]}"; do
  filename="$(basename "${wheel}")"
  case "${filename}" in
    *-py3-none-*) ;;
    *)
      echo "Expected Python-agnostic py3-none wheel tag, got ${filename}" >&2
      exit 1
      ;;
  esac
done
