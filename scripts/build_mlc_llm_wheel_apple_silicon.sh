#!/bin/bash
set -euxo pipefail

eval "$(command conda 'shell.bash' 'hook' 2> /dev/null)"

# Need to first
# - create these enviroments,
# - install dependencies in https://github.com/tlc-pack/tlcpack/blob/main/conda/build-environment.yaml for these env.
declare -a conda_env_names=("wheel-3-9" "wheel-3-10" "wheel-3-11" "wheel-3-12" "wheel-3-13")

export DEPLOY_WHEEL=1

# cleanup and clone mlc-llm
rm -rf mlc-llm && git clone https://github.com/mlc-ai/mlc-llm mlc-llm --recursive --single-branch --branch main

for name in "${conda_env_names[@]}"
do
    ./scripts/build_mlc_llm_wheel_single_python_apple_silicon.sh $name
done
