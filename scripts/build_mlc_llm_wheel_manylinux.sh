#!/usr/bin/env bash

source /multibuild/manylinux_utils.sh
source /opt/rh/gcc-toolset-11/enable # GCC-11 is the hightest GCC version compatible with NVCC < 12

function usage() {
	echo "Usage: $0 [--gpu GPU-VERSION]"
	echo
	echo -e "--gpu {none cuda-12.1 cuda-12.2 cuda-12.3 cuda-12.4 cuda-12.8 cuda-13.0 rocm-6.1 rocm-6.2}"
	echo -e "\tSpecify the GPU version (CUDA/ROCm) in the MLC-LLM (default: none)."
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

MLC_LLM_DIR="/workspace/mlc-llm"
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
	echo "Building MLC-LLM for CPU only"
else
	echo "Building MLC-LLM with GPU ${GPU}"
fi

AUDITWHEEL_OPTS="--plat ${AUDITWHEEL_PLAT} -w repaired_wheels/"
AUDITWHEEL_OPTS="--exclude libtvm --exclude libtvm_runtime --exclude libtvm_ffi --exclude libvulkan ${AUDITWHEEL_OPTS}"
if [[ ${GPU} == rocm* ]]; then
	AUDITWHEEL_OPTS="--exclude libamdhip64 --exclude libhsa-runtime64 --exclude librocm_smi64 --exclude librccl --exclude libhipblas --exclude libhipblaslt ${AUDITWHEEL_OPTS}"
elif [[ ${GPU} == cuda* ]]; then
	AUDITWHEEL_OPTS="--exclude libcuda --exclude libcudart --exclude libnvrtc  --exclude libcublas --exclude libcublasLt ${AUDITWHEEL_OPTS}"
fi

# config the cmake
cd "${MLC_LLM_DIR}"
echo set\(USE_VULKAN ON\) >>config.cmake

if [[ ${GPU} == cuda* ]]; then
	CUDA_ARCHS="80;86;89;90;90a"
fi
if [[ ${GPU} == cuda-12.8 || ${GPU} == cuda-13.0 ]]; then
	CUDA_ARCHS="${CUDA_ARCHS};100;120"
fi
if [[ ${GPU} == cuda-13.0 ]]; then
	CUDA_ARCHS="${CUDA_ARCHS};110"
fi

if [[ ${GPU} == rocm* ]]; then
	echo set\(USE_ROCM ON\) >>config.cmake
elif [[ ${GPU} == cuda* ]]; then
	echo set\(USE_CUDA ON\) >>config.cmake
	echo set\(CMAKE_CUDA_ARCHITECTURES "${CUDA_ARCHS}"\) >>config.cmake
	echo set\(CMAKE_CUDA_FLAGS \"--expt-relaxed-constexpr\"\) >>config.cmake
fi

# compile the mlc-llm
git config --global --add safe.directory $MLC_LLM_DIR
pip wheel --no-deps -w dist . -v

echo "Running auditwheel..."
mkdir -p repaired_wheels
auditwheel repair ${AUDITWHEEL_OPTS} dist/mlc_llm*.whl

rm -rf ${MLC_LLM_DIR}/dist ${MLC_LLM_DIR}/build
