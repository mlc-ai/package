#!/bin/bash

set -e
set -u

GPU_OPT=""
VULKAN_OPT=""
TOOLCHAIN_OPT=""

if [ "$target_platform" == "osx-arm64" ]; then
	GPU_OPT="-DUSE_METAL=ON"
	TOOLCHAIN_OPT="-DCMAKE_OSX_DEPLOYMENT_TARGET=${MACOSX_DEPLOYMENT_TARGET:-11.0}"
elif [ "$target_platform" == "osx-64" ]; then
	GPU_OPT="-DUSE_METAL=ON"
	TOOLCHAIN_OPT="-DCMAKE_OSX_DEPLOYMENT_TARGET=${MACOSX_DEPLOYMENT_TARGET:-11.0}"
elif [ "$target_platform" == "linux-64" ]; then
	TOOLCHAIN_OPT="-DCMAKE_TOOLCHAIN_FILE=${RECIPE_DIR}/cross-linux.cmake"
	# vulkan should be set to build prefix in non osx
	VULKAN_OPT="-DUSE_VULKAN=${BUILD_PREFIX}"
fi

# When cuda is not set, we default to False
cuda=${cuda:-False}

if [ "$cuda" == "True" ]; then
	GPU_OPT="-DUSE_CUDA=ON -DUSE_CUTLASS=ON -DUSE_NCCL=ON -DUSE_CUBLAS=ON"
	TOOLCHAIN_OPT=""
fi

# remove touched cmake config
rm -f config.cmake
rm -rf build
mkdir -p build
cd build

cmake -DCMAKE_INSTALL_PREFIX="${PREFIX}" \
	-DCMAKE_BUILD_TYPE=Release \
	-DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
	-DHIDE_PRIVATE_SYMBOLS=ON \
	-DINSTALL_DEV=ON \
	${VULKAN_OPT} \
	${GPU_OPT} ${TOOLCHAIN_OPT} \
	${SRC_DIR}

make -j${CPU_COUNT}
cd ..
