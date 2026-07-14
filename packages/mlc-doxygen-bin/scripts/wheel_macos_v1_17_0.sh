#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${project_dir}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "wheel_macos_v1_17_0.sh must run on macOS" >&2
  exit 1
fi

detect_python_org_version() {
  pkgutil --pkgs \
    | sed -n 's/^org\.python\.Python\.PythonFramework-\([0-9][0-9.]*\)$/\1/p' \
    | sort -t. -k1,1n -k2,2n \
    | tail -n 1
}

prepend_homebrew_tool() {
  local formula="$1"
  if command -v brew >/dev/null 2>&1; then
    local prefix
    if prefix="$(brew --prefix --installed "${formula}" 2>/dev/null)" && [[ -d "${prefix}/bin" ]]; then
      PATH="${prefix}/bin:${PATH}"
    fi
  fi
}

prepend_homebrew_tool flex
prepend_homebrew_tool bison
export PATH

host_arch="$(uname -m)"
: "${MLC_DOXYGEN_BIN_ARCH:=${host_arch}}"
case "${MLC_DOXYGEN_BIN_ARCH}" in
  arm64|x86_64) ;;
  *)
    echo "Unsupported macOS architecture: ${MLC_DOXYGEN_BIN_ARCH}" >&2
    exit 1
    ;;
esac

for tool in flex bison; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "${tool} is required to build Doxygen. Install it with: brew install flex bison" >&2
    exit 1
  fi
done
flex_executable="$(command -v flex)"
bison_executable="$(command -v bison)"

check_tool_version() {
  local tool="$1"
  local executable="$2"
  local minimum="$3"
  local actual
  actual="$("${executable}" --version | sed -n '1s/.* \([0-9][0-9.]*\).*/\1/p')"
  if [[ -z "${actual}" ]]; then
    echo "Could not determine ${tool} version" >&2
    exit 1
  fi
  python3 - "${tool}" "${actual}" "${minimum}" <<'PY'
import re
import sys

tool, actual, minimum = sys.argv[1:]

def parts(version):
    return tuple(int(part) for part in re.findall(r"\d+", version))

if parts(actual) < parts(minimum):
    raise SystemExit(
        f"{tool} {minimum} or newer is required to build Doxygen; found {actual}. "
        "Install Homebrew flex and bison with: brew install flex bison"
    )
PY
}

check_tool_version flex "${flex_executable}" 2.5.37
check_tool_version bison "${bison_executable}" 2.7

if command -v sysctl >/dev/null 2>&1; then
  cpu_count="$(sysctl -n hw.ncpu)"
else
  cpu_count="2"
fi

: "${MACOSX_DEPLOYMENT_TARGET:=13.0}"
: "${CMAKE_BUILD_PARALLEL_LEVEL:=${cpu_count}}"

platform_suffix="${MACOSX_DEPLOYMENT_TARGET//./_}_${MLC_DOXYGEN_BIN_ARCH}"
: "${MLC_DOXYGEN_BIN_PLAT_NAME:=macosx_${platform_suffix}}"

if [[ -z "${CIBW_BUILD:-}" ]]; then
  python_org_version="$(detect_python_org_version)"
  if [[ -z "${python_org_version}" ]]; then
    cat >&2 <<'EOF'
No python.org CPython installation was found.

cibuildwheel on local macOS will not install CPython for you. Install one of
the official python.org packages, then rerun this script. The wheel produced by
this package is tagged py3-none, so the local build interpreter version only
needs to be supported by cibuildwheel.
EOF
    exit 1
  fi
  python_tag="cp${python_org_version//./}"
  export CIBW_BUILD="${python_tag}-macosx_${MLC_DOXYGEN_BIN_ARCH}"
fi
export CIBW_ARCHS_MACOS="${CIBW_ARCHS_MACOS:-${MLC_DOXYGEN_BIN_ARCH}}"
export CIBW_BUILD_VERBOSITY="${CIBW_BUILD_VERBOSITY:-1}"
export CIBW_ENVIRONMENT="${CIBW_ENVIRONMENT:-MLC_DOXYGEN_BIN_PLAT_NAME='${MLC_DOXYGEN_BIN_PLAT_NAME}' MACOSX_DEPLOYMENT_TARGET='${MACOSX_DEPLOYMENT_TARGET}' CMAKE_BUILD_PARALLEL_LEVEL='${CMAKE_BUILD_PARALLEL_LEVEL}' FLEX_EXECUTABLE='${flex_executable}' BISON_EXECUTABLE='${bison_executable}'}"

scripts/cibuildwheel_run.sh macos wheelhouse .

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
