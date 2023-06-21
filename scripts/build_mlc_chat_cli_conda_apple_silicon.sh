#!/bin/bash
set -euxo pipefail

PKG="mlc-chat-cli-nightly"
CONDA_ENV_NAME="mlc-llm-build"
export CONDA_PKG_PATH="osx-arm64"
deploy="${DEPLOY_WHEEL:-0}"

rm -rf mlc-llm
git clone https://github.com/mlc-ai/mlc-llm.git mlc-llm --recursive

python3 scripts/sync_package.py --package mlc-llm --package-name $PKG

source "$CONDA_HOME/etc/profile.d/conda.sh"
conda deactivate
conda env remove -n ${CONDA_ENV_NAME}
conda env create --file conda/mlc-llm/osx-build-environment.yaml
conda activate ${CONDA_ENV_NAME}
conda build -c conda-forge --output-folder=conda/pkg -m conda/mlc-llm/build_config.yaml conda/mlc-llm/recipe

if [ "$deploy" -eq "1" ]; then
  anaconda upload -u mlc-ai --force --label main conda/pkg/${CONDA_PKG_PATH}/*.tar.bz2
fi
