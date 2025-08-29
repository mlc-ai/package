#!/bin/bash

set -e
set -u

MACOSX_DEPLOYMENT_TARGET=${MACOSX_DEPLOYMENT_TARGET:-10.15}

python --version
python -m pip install wheel

cd mlc-llm
rm -f config.cmake

rm -rf build
mkdir -p build

echo set\(CMAKE_OSX_DEPLOYMENT_TARGET ${MACOSX_DEPLOYMENT_TARGET}\) >>config.cmake
echo set\(USE_METAL ON\) >>config.cmake
echo set\(CMAKE_POLICY_VERSION_MINIMUM 3.5\) >>config.cmake

pip wheel --no-deps -w dist . -v
cd ..
