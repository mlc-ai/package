#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${project_dir}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "wheel_macos_v4_16_0.sh must run on macOS" >&2
  exit 1
fi

detect_python_org_version() {
  pkgutil --pkgs \
    | sed -n 's/^org\.python\.Python\.PythonFramework-\([0-9][0-9.]*\)$/\1/p' \
    | sort -t. -k1,1n -k2,2n \
    | tail -n 1
}

host_arch="$(uname -m)"
: "${MLC_Z3_STATIC_ARCH:=${host_arch}}"
case "${MLC_Z3_STATIC_ARCH}" in
  arm64|x86_64) ;;
  *)
    echo "Unsupported macOS architecture: ${MLC_Z3_STATIC_ARCH}" >&2
    exit 1
    ;;
esac

if command -v sysctl >/dev/null 2>&1; then
  cpu_count="$(sysctl -n hw.ncpu)"
else
  cpu_count="2"
fi

: "${MACOSX_DEPLOYMENT_TARGET:=14.0}"
: "${CMAKE_BUILD_PARALLEL_LEVEL:=${cpu_count}}"

platform_suffix="${MACOSX_DEPLOYMENT_TARGET//./_}_${MLC_Z3_STATIC_ARCH}"
: "${MLC_Z3_STATIC_PLAT_NAME:=macosx_${platform_suffix}}"

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
  export CIBW_BUILD="${python_tag}-macosx_${MLC_Z3_STATIC_ARCH}"
fi
export CIBW_ARCHS_MACOS="${CIBW_ARCHS_MACOS:-${MLC_Z3_STATIC_ARCH}}"
export CIBW_BUILD_VERBOSITY="${CIBW_BUILD_VERBOSITY:-1}"
export CIBW_ENVIRONMENT="${CIBW_ENVIRONMENT:-MLC_Z3_STATIC_ALLOW_SOURCE_BUILD='1' MACOSX_DEPLOYMENT_TARGET='${MACOSX_DEPLOYMENT_TARGET}' CMAKE_BUILD_PARALLEL_LEVEL='${CMAKE_BUILD_PARALLEL_LEVEL}'}"

scripts/cibuildwheel_run.sh macos wheelhouse .

shopt -s nullglob
wheels=(wheelhouse/*-py3-none-"${MLC_Z3_STATIC_PLAT_NAME}".whl)
if [[ "${#wheels[@]}" -eq 0 ]]; then
  echo "No ${MLC_Z3_STATIC_PLAT_NAME} wheels found in wheelhouse" >&2
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
  scripts/wheel_verify.sh "${wheel}"
done
