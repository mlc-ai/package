#!/bin/bash

set -e
set -u

# export so `pip wheel` tags the wheel with the deployment target, not the host macOS version
export MACOSX_DEPLOYMENT_TARGET=${MACOSX_DEPLOYMENT_TARGET:-14.0}

python --version
python -m pip install wheel

cd mlc-llm
rm -f config.cmake

rm -rf build
mkdir -p build

echo set\(CMAKE_OSX_DEPLOYMENT_TARGET ${MACOSX_DEPLOYMENT_TARGET}\) >>config.cmake
echo set\(USE_METAL ON\) >>config.cmake
echo set\(CMAKE_POLICY_VERSION_MINIMUM 3.5\) >>config.cmake

# sentencepiece (3rdparty/tokenizers-cpp) links libatomic on every arm/aarch
# target, but macOS/clang has no libatomic -- atomics are built into the compiler
# -- so the link fails with "library 'atomic' not found". Drop that append for the
# macOS build; the Linux build (build_mlc_llm_wheel_manylinux.sh) still links it.
sed -i '' 's/list(APPEND SPM_LIBS "atomic")/# libatomic omitted on macOS/' \
  3rdparty/tokenizers-cpp/sentencepiece/src/CMakeLists.txt

pip wheel --no-deps -w dist . -v
cd ..
