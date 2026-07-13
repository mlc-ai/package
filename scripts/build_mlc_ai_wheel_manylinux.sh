#!/usr/bin/env bash

source /multibuild/manylinux_utils.sh
source /opt/rh/gcc-toolset-13/enable # Keep in sync with z3-static manylinux builds.
source "$(dirname "${BASH_SOURCE[0]}")/manylinux_build_common.sh"

TVM_DIR="/workspace/tvm"
BUILD_TARGET="TVM"

parse_gpu_args "$@"

AUDITWHEEL_OPTS="--plat ${AUDITWHEEL_PLAT} -w repaired_wheels/"
AUDITWHEEL_OPTS="--exclude libtinfo --exclude libtvm_ffi ${AUDITWHEEL_OPTS}"
if [[ ${GPU} == rocm* ]]; then
	AUDITWHEEL_OPTS="--exclude libamdhip64 --exclude libhsa-runtime64 --exclude librocm_smi64 --exclude librccl --exclude libhipblas --exclude libhipblaslt ${AUDITWHEEL_OPTS}"
elif [[ ${GPU} == cuda* ]]; then
	AUDITWHEEL_OPTS="--exclude libcuda --exclude libcudart --exclude libnvrtc --exclude libcublas --exclude libcublasLt ${AUDITWHEEL_OPTS}"
fi

# config the cmake
cd "${TVM_DIR}"

echo set\(HIDE_PRIVATE_SYMBOLS ON\) >>config.cmake
echo set\(USE_RPC ON\) >>config.cmake
echo set\(USE_VULKAN ON\) >>config.cmake
echo set\(USE_Z3 OFF\) >>config.cmake

if [[ ${GPU} == rocm* ]]; then
	echo set\(USE_LLVM \"/opt/rocm/llvm/bin/llvm-config --ignore-libllvm --link-static\"\) >>config.cmake
	echo set\(USE_ROCM ON\) >>config.cmake
	echo set\(USE_HIPBLAS ON\) >>config.cmake
	echo set\(USE_RCCL /opt/rocm/\) >>config.cmake
elif [[ ${GPU} == cuda* ]]; then
	CUDA_ARCHS=$(cuda_archs_for "$GPU")
	echo set\(USE_LLVM \"llvm-config --ignore-libllvm --link-static\"\) >>config.cmake
	echo set\(USE_CUDA ON\) >>config.cmake
	echo set\(USE_CUBLAS ON\) >>config.cmake
	echo set\(USE_CUTLASS ${USE_CUTLASS}\) >>config.cmake
	echo set\(USE_THRUST OFF\) >>config.cmake
	echo set\(USE_NCCL ON\) >>config.cmake
	echo set\(CMAKE_CUDA_ARCHITECTURES "${CUDA_ARCHS}"\) >>config.cmake
	echo set\(CMAKE_CUDA_FLAGS \"--expt-relaxed-constexpr\"\) >>config.cmake

	for cuda_version in 12; do
		if [ -d "/usr/include/nvshmem_${cuda_version}" ]; then
			mkdir -p /workspace/nvshmem
			cp -r /usr/include/nvshmem_${cuda_version} /workspace/nvshmem/include
			cp -r /usr/lib64/nvshmem/${cuda_version} /workspace/nvshmem/lib
			cp -r /usr/bin/nvshmem_${cuda_version} /workspace/nvshmem/bin
			echo set\(USE_NVSHMEM /workspace/nvshmem\) >>config.cmake
			break
		fi
	done
else
	echo set\(USE_LLVM \"llvm-config --ignore-libllvm --link-static\"\) >>config.cmake
fi

# compile the tvm
git config --global --add safe.directory $TVM_DIR
# apache-tvm-ffi (the pip package for 3rdparty/tvm-ffi) can lag PyPI for the
# revision being built, so install it from the in-tree submodule; --no-deps on the
# tvm wheel then keeps pip from re-resolving apache-tvm-ffi (and other deps) from PyPI.
pip install --no-deps ./3rdparty/tvm-ffi
pip wheel --no-deps -w dist . -v

echo "Running auditwheel..."
mkdir -p repaired_wheels
auditwheel repair ${AUDITWHEEL_OPTS} dist/mlc_ai*.whl

rm -rf ${TVM_DIR}/dist ${TVM_DIR}/build
