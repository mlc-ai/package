#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -lt 1 || "$#" -gt 3 ]]; then
  echo "usage: cibuildwheel_run.sh <platform> [output-dir] [package-dir]" >&2
  exit 1
fi

platform="$1"
output_dir="${2:-wheelhouse}"
package_dir="${3:-.}"

: "${UV:=uv}"
if ! command -v "${UV}" >/dev/null 2>&1; then
  echo "uv executable not found: ${UV}" >&2
  exit 1
fi

"${UV}" tool run --isolated --from "cibuildwheel==3.3.1" \
  cibuildwheel --platform "${platform}" --output-dir "${output_dir}" "${package_dir}"
