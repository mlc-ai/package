#!/usr/bin/env bash
set -euo pipefail

flex_version="2.6.4"
flex_url="https://github.com/westes/flex/releases/download/v${flex_version}/flex-${flex_version}.tar.gz"
flex_sha256="e87aae032bf07c26f85ac0ed3250998c37621d95f8bd748b31f15b33c45ee995"

: "${MLC_DOXYGEN_BIN_TOOLS_PREFIX:=/usr/local}"

if command -v yum >/dev/null 2>&1; then
  yum install -y bison m4 make gcc gcc-c++ curl tar gzip
elif command -v dnf >/dev/null 2>&1; then
  dnf install -y bison m4 make gcc gcc-c++ curl tar gzip
else
  echo "Neither yum nor dnf is available; cannot install manylinux build tools" >&2
  exit 1
fi

if [[ -x "${MLC_DOXYGEN_BIN_TOOLS_PREFIX}/bin/flex" ]]; then
  installed_version="$("${MLC_DOXYGEN_BIN_TOOLS_PREFIX}/bin/flex" --version | sed -n '1s/.* \([0-9][0-9.]*\).*/\1/p')"
  if [[ "${installed_version}" == "${flex_version}" ]]; then
    "${MLC_DOXYGEN_BIN_TOOLS_PREFIX}/bin/flex" --version
    bison --version | sed -n '1p'
    exit 0
  fi
fi

work_dir="$(mktemp -d)"
cleanup() {
  rm -rf "${work_dir}"
}
trap cleanup EXIT

cd "${work_dir}"
curl -fsSL -o "flex-${flex_version}.tar.gz" "${flex_url}"
echo "${flex_sha256}  flex-${flex_version}.tar.gz" | sha256sum -c -
tar -xzf "flex-${flex_version}.tar.gz"
cd "flex-${flex_version}"

# Flex 2.6.4 detects reallocarray on manylinux_2_28, but GCC 14 builds fail
# unless glibc exposes its declaration. Keep the feature macro explicit instead
# of suppressing implicit-function-declaration diagnostics.
export CFLAGS="${CFLAGS:-} -D_GNU_SOURCE"

./configure --prefix="${MLC_DOXYGEN_BIN_TOOLS_PREFIX}" --disable-shared --enable-static
make -j"$(nproc)"
make install

"${MLC_DOXYGEN_BIN_TOOLS_PREFIX}/bin/flex" --version
bison --version | sed -n '1p'
