#!/usr/bin/env bash

source /multibuild/manylinux_utils.sh
source /opt/rh/gcc-toolset-11/enable # GCC-11 is the hightest GCC version compatible with NVCC < 12

function usage() {
	echo "Usage: $0 [--gpu GPU-VERSION]"
	echo
	echo -e "--gpu {none cuda-12.1 cuda-12.2 cuda-12.3 cuda-12.4 cuda-12.8 cuda-13.0 rocm-6.1 rocm-6.2}"
	echo -e "\tSpecify the GPU version (CUDA/ROCm) in the TVM (default: none)."
}

function in_array() {
	KEY=$1
	ARRAY=$2
	for e in ${ARRAY[*]}; do
		if [[ "$e" == "$1" ]]; then
			return 0
		fi
	done
	return 1
}

TVM_DIR="/workspace/tvm"
GPU_OPTIONS=("none" "cuda-12.1" "cuda-12.2" "cuda-12.3" "cuda-12.4" "cuda-12.8" "cuda-13.0" "rocm-6.1" "rocm-6.2")
GPU="none"

while [[ $# -gt 0 ]]; do
	arg="$1"
	case $arg in
	--gpu)
		GPU=$2
		shift
		shift
		;;
	-h | --help)
		usage
		exit -1
		;;
	*) # unknown option
		echo "Unknown argument: $arg"
		echo
		usage
		exit -1
		;;
	esac
done

if ! in_array "${GPU}" "${GPU_OPTIONS[*]}"; then
	echo "Invalid GPU option: ${GPU}"
	echo
	echo 'GPU version can only be {"none", "cuda-12.1" "cuda-12.2" "cuda-12.3" "cuda-12.4" "cuda-12.8" "cuda-13.0" "rocm-6.1" "rocm-6.2"}'
	exit -1
fi

if [[ ${GPU} == "none" ]]; then
	echo "Building TVM for CPU only"
else
	echo "Building TVM with GPU ${GPU}"
fi

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

if [[ ${GPU} == cuda* ]]; then
	CUDA_ARCHS="80;89;90a"
fi
if [[ ${GPU} == cuda-12.8 || ${GPU} == cuda-13.0 ]]; then
	CUDA_ARCHS="${CUDA_ARCHS};120"
fi
if [[ ${GPU} == cuda-13.0 ]]; then
	CUDA_ARCHS="${CUDA_ARCHS};110"
fi

if [[ ${GPU} == rocm* ]]; then
	echo set\(USE_LLVM \"/opt/rocm/llvm/bin/llvm-config --ignore-libllvm --link-static\"\) >>config.cmake
	echo set\(USE_ROCM ON\) >>config.cmake
	echo set\(USE_HIPBLAS ON\) >>config.cmake
	echo set\(USE_RCCL /opt/rocm/\) >>config.cmake
elif [[ ${GPU} == cuda* ]]; then
	echo set\(USE_LLVM \"llvm-config --ignore-libllvm --link-static\"\) >>config.cmake
	echo set\(USE_CUDA ON\) >>config.cmake
	echo set\(USE_CUBLAS ON\) >>config.cmake
	echo set\(USE_CUTLASS ON\) >>config.cmake
	echo set\(USE_THRUST ON\) >>config.cmake
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
pip wheel -w dist . -v

echo "Running auditwheel..."
mkdir -p repaired_wheels
auditwheel repair ${AUDITWHEEL_OPTS} dist/mlc_ai*.whl

rm -rf ${TVM_DIR}/dist ${TVM_DIR}/build
