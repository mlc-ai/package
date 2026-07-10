#!/usr/bin/env bash
# Shared helpers for the manylinux mlc-ai / mlc-llm wheel builds.
#
# Source this from a build script after setting BUILD_TARGET (a human-readable
# label used in messages, e.g. "TVM" or "MLC-LLM"):
#
#   BUILD_TARGET="TVM"
#   source "$(dirname "${BASH_SOURCE[0]}")/manylinux_build_common.sh"
#   parse_gpu_args "$@"                    # validates, sets GPU and USE_CUTLASS
#   ...
#   CUDA_ARCHS=$(cuda_archs_for "$GPU")    # inside the cuda branch

# GPU versions accepted by the build scripts. Keep in sync with the CI build
# matrix and the --gpu choices in sync_package.py.
GPU_OPTIONS=("none" "cuda-12.8" "cuda-13.0" "rocm-6.1" "rocm-6.2")

function usage() {
	echo "Usage: $0 [--gpu GPU-VERSION] [--no-cutlass]"
	echo
	echo -e "--gpu {${GPU_OPTIONS[*]}}"
	echo -e "\tSpecify the GPU version (CUDA/ROCm) in the ${BUILD_TARGET} (default: none)."
}

function in_array() {
	local key=$1
	shift
	local e
	for e in "$@"; do
		if [[ "$e" == "$key" ]]; then
			return 0
		fi
	done
	return 1
}

# Parse the common build arguments. Sets the GPU and USE_CUTLASS globals and
# validates the GPU selection (exits on error).
function parse_gpu_args() {
	GPU="none"
	USE_CUTLASS="ON"
	while [[ $# -gt 0 ]]; do
		case "$1" in
		--gpu)
			GPU="$2"
			shift 2
			;;
		--no-cutlass)
			USE_CUTLASS="OFF"
			shift
			;;
		-h | --help)
			usage
			exit 1
			;;
		*)
			echo "Unknown argument: $1"
			echo
			usage
			exit 1
			;;
		esac
	done

	if ! in_array "${GPU}" "${GPU_OPTIONS[@]}"; then
		echo "Invalid GPU option: ${GPU}"
		echo
		echo "GPU version can only be {${GPU_OPTIONS[*]}}"
		exit 1
	fi

	if [[ ${GPU} == "none" ]]; then
		echo "Building ${BUILD_TARGET} for CPU only"
	else
		echo "Building ${BUILD_TARGET} with GPU ${GPU}"
	fi
}

# Echo the CMAKE_CUDA_ARCHITECTURES list for the given CUDA GPU version.
function cuda_archs_for() {
	local gpu=$1
	local archs="80;89;90a"
	if [[ ${gpu} == cuda-12.8 || ${gpu} == cuda-13.0 ]]; then
		archs="${archs};120"
	fi
	if [[ ${gpu} == cuda-13.0 ]]; then
		archs="${archs};110"
	fi
	echo "${archs}"
}
