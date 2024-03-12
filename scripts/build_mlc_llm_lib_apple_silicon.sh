#!/bin/bash

set -e
set -u

cd mlc-llm
rm -f config.cmake
rm -rf build
mkdir -p build
cd build

MACOSX_DEPLOYMENT_TARGET=${MACOSX_DEPLOYMENT_TARGET:-13.02}

cmake -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_OSX_DEPLOYMENT_TARGET=${MACOSX_DEPLOYMENT_TARGET} \
      -DUSE_METAL=ON \
      ..

make -j12
cd ../..
