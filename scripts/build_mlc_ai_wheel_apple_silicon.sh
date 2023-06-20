#!/bin/bash
set -euxo pipefail

eval "$(command conda 'shell.bash' 'hook' 2> /dev/null)"

# Need to first
# - create these enviroments,
# - install dependencies in https://github.com/tlc-pack/tlcpack/blob/main/conda/build-environment.yaml for these env.
declare -a conda_env_names=("wheel-3-8" "wheel-3-9" "wheel-3-10" "wheel-3-11")

export DEPLOY_WHEEL=1

# cleanup and clone tvm mlc
rm -rf tvm && git clone https://github.com/mlc-ai/relax tvm --recursive --single-branch --branch mlc

for name in "${conda_env_names[@]}"
do
    ./scripts/build_mlc_ai_wheel_single_python_apple_silicon.sh $name
done
