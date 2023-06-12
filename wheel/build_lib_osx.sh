#!/bin/bash

set -e
set -u

cd tvm
rm -f config.cmake
rm -rf build
mkdir -p build
cd build

MACOSX_DEPLOYMENT_TARGET=${MACOSX_DEPLOYMENT_TARGET:-10.15}

cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_OSX_DEPLOYMENT_TARGET=${MACOSX_DEPLOYMENT_TARGET} \
      -DUSE_RPC=ON \
      -DUSE_CPP_RPC=OFF \
      -DUSE_LLVM="llvm-config --link-static" \
      -DHIDE_PRIVATE_SYMBOLS=ON \
      -DUSE_METAL=ON \
      ..

make -j3
cd ../..
