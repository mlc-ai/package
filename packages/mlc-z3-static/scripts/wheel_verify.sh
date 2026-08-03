#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -ne 1 ]]; then
  echo "usage: wheel_verify.sh <path-to-wheel>" >&2
  exit 1
fi

: "${UV:=uv}"
if ! command -v "${UV}" >/dev/null 2>&1; then
  echo "uv executable not found: ${UV}" >&2
  exit 1
fi

wheel="$1"
wheel_path="$(cd "$(dirname "${wheel}")" && pwd)/$(basename "${wheel}")"
tmpdir="$(mktemp -d)"

cleanup() {
  rm -rf "${tmpdir}"
}
trap cleanup EXIT

venv_dir="${tmpdir}/venv"
venv_bin="${venv_dir}/bin"
venv_python="${venv_bin}/python"
venv_cmake="${venv_bin}/cmake"
venv_ninja="${venv_bin}/ninja"
src_dir="${tmpdir}/src"
build_dir="${tmpdir}/build"

echo "Verifying static CMake linkage for $(basename "${wheel_path}")"

"${UV}" venv --no-project "${venv_dir}"
"${UV}" pip install --python "${venv_python}" cmake ninja "${wheel_path}"

export PATH="${venv_bin}:${PATH}"
if [[ ! -x "${venv_ninja}" ]]; then
  echo "ninja executable was not installed into the temporary venv: ${venv_ninja}" >&2
  exit 1
fi

static_prefix="$("${venv_python}" -c 'import mlc_z3_static as z; print(z.get_cmake_prefix_path("static"))')"
static_library="$("${venv_python}" -c 'import mlc_z3_static as z; print(z.get_static_library_path())')"
case "${static_library}" in
  *.a|*.lib) ;;
  *)
    echo "Expected a static Z3 library, got ${static_library}" >&2
    exit 1
    ;;
esac

mkdir -p "${src_dir}"
cat > "${src_dir}/CMakeLists.txt" <<'EOF'
cmake_minimum_required(VERSION 3.20)
project(mlc_z3_static_link_verify LANGUAGES C CXX)

find_package(Z3 CONFIG REQUIRED)

get_target_property(Z3_IMPORTED_LOCATION z3::libz3 IMPORTED_LOCATION_RELEASE)
if(NOT Z3_IMPORTED_LOCATION)
  get_target_property(Z3_IMPORTED_LOCATION z3::libz3 IMPORTED_LOCATION)
endif()
if(NOT Z3_IMPORTED_LOCATION)
  message(FATAL_ERROR "z3::libz3 does not expose an imported library location")
endif()

file(REAL_PATH "${Z3_IMPORTED_LOCATION}" Z3_IMPORTED_LOCATION_REAL)
file(REAL_PATH "${MLC_Z3_STATIC_EXPECTED_PREFIX}" MLC_Z3_STATIC_EXPECTED_PREFIX_REAL)
string(FIND "${Z3_IMPORTED_LOCATION_REAL}" "${MLC_Z3_STATIC_EXPECTED_PREFIX_REAL}/" Z3_PREFIX_POSITION)
if(NOT Z3_PREFIX_POSITION EQUAL 0)
  message(
    FATAL_ERROR
    "z3::libz3 resolves outside the installed wheel prefix.\n"
    "  imported: ${Z3_IMPORTED_LOCATION_REAL}\n"
    "  expected prefix: ${MLC_Z3_STATIC_EXPECTED_PREFIX_REAL}"
  )
endif()

add_executable(mlc_z3_static_link_verify main.cpp)
target_link_libraries(mlc_z3_static_link_verify PRIVATE z3::libz3)
target_compile_features(mlc_z3_static_link_verify PRIVATE cxx_std_20)
EOF
cat > "${src_dir}/main.cpp" <<'EOF'
#include <z3++.h>

int main() {
  z3::context cxx_ctx;
  z3::expr x = cxx_ctx.bool_const("x");
  z3::solver cxx_solver(cxx_ctx);
  cxx_solver.add(x);
  if (cxx_solver.check() != z3::sat) {
    return 1;
  }

  Z3_config cfg = Z3_mk_config();
  Z3_context ctx = Z3_mk_context(cfg);
  Z3_solver solver = Z3_mk_solver(ctx);
  Z3_solver_inc_ref(ctx, solver);
  Z3_solver_dec_ref(ctx, solver);
  Z3_del_context(ctx);
  Z3_del_config(cfg);
  return 0;
}
EOF

"${venv_cmake}" -S "${src_dir}" -B "${build_dir}" \
  -G Ninja \
  -DCMAKE_MAKE_PROGRAM="${venv_ninja}" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH="${static_prefix}" \
  -DMLC_Z3_STATIC_EXPECTED_PREFIX="${static_prefix}"
"${venv_cmake}" --build "${build_dir}" --config Release

exe="${build_dir}/mlc_z3_static_link_verify"
case "$(uname -s)" in
  Darwin)
    if command -v otool >/dev/null 2>&1; then
      if otool -L "${exe}" | grep -E 'libz3\.(dylib|so)' >/dev/null; then
        echo "Expected static Z3 linkage, but executable links a dynamic libz3:" >&2
        otool -L "${exe}" >&2
        exit 1
      fi
    fi
    ;;
  Linux)
    if command -v ldd >/dev/null 2>&1; then
      if ldd "${exe}" | grep -E 'libz3\.so' >/dev/null; then
        echo "Expected static Z3 linkage, but executable links a dynamic libz3:" >&2
        ldd "${exe}" >&2
        exit 1
      fi
    fi
    ;;
esac

"${exe}"
