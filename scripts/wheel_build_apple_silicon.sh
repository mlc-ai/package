#!/bin/bash
set -euxo pipefail

eval "$(command conda 'shell.bash' 'hook' 2> /dev/null)"

# Need to first
# - create these enviroments,
# - install dependencies in https://github.com/tlc-pack/tlcpack/blob/main/conda/build-environment.yaml for these env.
declare -a conda_env_names=("wheel-3-8" "wheel-3-9" "wheel-3-10" "wheel-3-11")

export GITHUB_TOKEN=$1

for name in "${conda_env_names[@]}"
do
    echo "Start build for $name"

    # conda activate
    conda activate $name

    # cleanup and clone tvm mlc
    rm -rf tvm && git clone https://github.com/mlc-ai/relax tvm --recursive --single-branch --branch mlc
    # sync package
    python common/sync_package.py mlc-ai-nightly --revision origin/mlc
    # build tvm
    ./scripts/build_lib_apple_silicon.sh

    # build wheel
    cd tvm/python && python setup.py bdist_wheel && cd -

    # deploy wheel
    python scripts/wheel_upload.py --repo mlc-ai/utils --tag v0.9.dev0 tvm/python/dist
done
