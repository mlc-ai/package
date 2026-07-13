#!/usr/bin/env bash

source /multibuild/manylinux_utils.sh
source /opt/rh/gcc-toolset-13/enable # Keep in sync with z3-static manylinux builds.
source "$(dirname "${BASH_SOURCE[0]}")/manylinux_build_common.sh"

MLC_LLM_DIR="/workspace/mlc-llm"
BUILD_TARGET="MLC-LLM"

parse_gpu_args "$@"

AUDITWHEEL_OPTS="--plat ${AUDITWHEEL_PLAT} -w repaired_wheels/"
AUDITWHEEL_OPTS="--exclude libtvm --exclude libtvm_runtime --exclude libtvm_runtime_extra --exclude libtvm_runtime_cuda --exclude libtvm_ffi --exclude libvulkan ${AUDITWHEEL_OPTS}"
if [[ ${GPU} == rocm* ]]; then
	AUDITWHEEL_OPTS="--exclude libamdhip64 --exclude libhsa-runtime64 --exclude librocm_smi64 --exclude librccl --exclude libhipblas --exclude libhipblaslt ${AUDITWHEEL_OPTS}"
elif [[ ${GPU} == cuda* ]]; then
	AUDITWHEEL_OPTS="--exclude libcuda --exclude libcudart --exclude libnvrtc  --exclude libcublas --exclude libcublasLt ${AUDITWHEEL_OPTS}"
fi

# config the cmake
cd "${MLC_LLM_DIR}"
echo set\(USE_VULKAN ON\) >>config.cmake

if [[ ${GPU} == rocm* ]]; then
	echo set\(USE_ROCM ON\) >>config.cmake
elif [[ ${GPU} == cuda* ]]; then
	CUDA_ARCHS=$(cuda_archs_for "$GPU")
	echo set\(USE_CUDA ON\) >>config.cmake
	echo set\(CMAKE_CUDA_ARCHITECTURES "${CUDA_ARCHS}"\) >>config.cmake
	echo set\(CMAKE_CUDA_FLAGS \"--expt-relaxed-constexpr\"\) >>config.cmake
fi

# update rust
dnf update rust -y
# compile the mlc-llm
git config --global --add safe.directory $MLC_LLM_DIR
pip wheel --no-deps -w dist . -v

echo "Running auditwheel..."
mkdir -p repaired_wheels
auditwheel repair ${AUDITWHEEL_OPTS} dist/mlc_llm*.whl

rm -rf ${MLC_LLM_DIR}/dist ${MLC_LLM_DIR}/build
