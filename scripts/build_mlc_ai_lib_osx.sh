#!/bin/bash

set -e
set -u

# export so `pip wheel` tags the wheel with the deployment target, not the host macOS version
export MACOSX_DEPLOYMENT_TARGET=${MACOSX_DEPLOYMENT_TARGET:-14.0}

python --version
python -m pip install wheel

cd tvm
rm -f config.cmake

rm -rf build
mkdir -p build

echo set\(CMAKE_OSX_DEPLOYMENT_TARGET ${MACOSX_DEPLOYMENT_TARGET}\) >>config.cmake
echo set\(HIDE_PRIVATE_SYMBOLS ON\) >>config.cmake
echo set\(USE_RPC ON\) >>config.cmake
echo set\(USE_CPP_RPC OFF\) >>config.cmake
echo set\(USE_LLVM \"llvm-config --link-static\"\) >>config.cmake
echo set\(USE_METAL ON\) >>config.cmake
echo set\(USE_Z3 OFF\) >>config.cmake

pip wheel --no-deps -w dist . -v
cd ..
