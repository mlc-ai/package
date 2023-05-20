#!/usr/bin/env bash

source /multibuild/manylinux_utils.sh

function build_mlc_ai_wheel() {
    python_dir=$1
    PYTHON_BIN="${python_dir}/bin/python"

    cd "${TVM_PYTHON_DIR}" && \
        ${PYTHON_BIN} setup.py bdist_wheel
}

function audit_mlc_ai_wheel() {
    python_version_str=$1

    cd "${TVM_PYTHON_DIR}" && \
      mkdir -p repaired_wheel && \
      auditwheel repair ${AUDITWHEEL_OPTS} dist/*cp${python_version_str}*.whl
}

TVM_PYTHON_DIR="/workspace/tvm/python"
PYTHON_VERSIONS=("3.7" "3.8" "3.9" "3.10" "3.11")


echo "Building TVM with Vulkan"

AUDITWHEEL_OPTS="--plat ${AUDITWHEEL_PLAT} -w repaired_wheels/"
if [[ ${CUDA} != "none" ]]; then
    AUDITWHEEL_OPTS="--exclude libcuda.so ${AUDITWHEEL_OPTS}"
fi

# config the cmake
cd /workspace/tvm
rm config.cmake
echo set\(USE_LLVM \"llvm-config --ignore-libllvm --link-static\"\) >> config.cmake
echo set\(HIDE_PRIVATE_SYMBOLS ON\) >> config.cmake
echo set\(USE_RPC ON\) >> config.cmake
echo set\(USE_SORT ON\) >> config.cmake
echo set\(USE_GRAPH_RUNTIME ON\) >> config.cmake
echo set\(USE_VULKAN ${VULKAN_SDK}\) >> config.cmake
echo set\(USE_KHRONOS_SPIRV "/usr/include/spirv-tools/"\) >> config.cmake

# compile the tvm
mkdir -p build
cd build
cmake ..
make -j$(nproc)

UNICODE_WIDTH=32  # Dummy value, irrelevant for Python 3

# Not all manylinux Docker images will have all Python versions,
# so check the existing python versions before generating packages
for python_version in ${PYTHON_VERSIONS[*]}
do
    echo "> Looking for Python ${python_version}."

    # Remove the . in version string, e.g. "3.8" turns into "38"
    python_version_str="$(echo "${python_version}" | sed -r 's/\.//g')"
    cpython_dir="/opt/conda/envs/py${python_version_str}/"

    # For compatibility in environments where Conda is not installed,
    # revert back to previous method of locating cpython_dir.
    if ! [ -d "${cpython_dir}" ]; then
      cpython_dir=$(cpython_path "${python_version}" "${UNICODE_WIDTH}" 2> /dev/null)
    fi

    if [ -d "${cpython_dir}" ]; then
      echo "Generating package for Python ${python_version}."
      build_mlc_ai_wheel ${cpython_dir}

      echo "Running auditwheel on package for Python ${python_version}."
      audit_mlc_ai_wheel ${python_version_str}
    else
      echo "Python ${python_version} not found. Skipping.";
    fi

done
