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

    # cleanup and clone mlc-llm
    rm -rf mlc-llm && git clone https://github.com/mlc-ai/mlc-llm mlc-llm --recursive --single-branch --branch main
    # sync package
    python scripts/sync_package.py --package mlc-llm --package-name mlc-chat-nightly --revision origin/main
    # build mlc-llm
    ./scripts/build_mlc_chat_lib_apple_silicon.sh

    # build wheel
    cd mlc-llm/python && python setup.py bdist_wheel && cd -

    # deploy wheel
    python scripts/wheel_upload.py --repo mlc-ai/package --tag v0.9.dev0 mlc-llm/python/dist
done
