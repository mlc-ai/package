#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${project_dir}"

: "${UV:=uv}"
if ! command -v "${UV}" >/dev/null 2>&1; then
  echo "uv executable not found: ${UV}" >&2
  exit 1
fi

"${UV}" sync --extra build

mlc_z3_static_prefix="$("${UV}" run python -c 'import mlc_z3_static as z; print(z.get_cmake_prefix_path("static"))')"

"${UV}" run --extra build cmake -S . -B build \
  -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="${mlc_z3_static_prefix}" \
  -DMLC_Z3_STATIC_EXPECTED_PREFIX="${mlc_z3_static_prefix}"
"${UV}" run --extra build cmake --build build --config Release

exe="build/mlc_z3_static_uv_example"
if [[ -x "${exe}" ]]; then
  "${exe}"
else
  "${exe}.exe"
fi
