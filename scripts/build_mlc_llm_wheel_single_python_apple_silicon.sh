#!/bin/bash
set -euxo pipefail

eval "$(command conda 'shell.bash' 'hook' 2> /dev/null)"

CONDA_ENV_NAME=$1
deploy="${DEPLOY_WHEEL:-0}"
stable="${STABLE_BUILD:-0}"

source $CONDA_HOME/etc/profile.d/conda.sh

echo "Start build for $CONDA_ENV_NAME"

# conda activate
conda activate $CONDA_ENV_NAME

# sync package
if [ "$stable" -eq "0" ]; then
  python scripts/sync_package.py --package mlc-llm --package-name mlc-llm-nightly --revision origin/main --skip-checkout --skip-conda
else
  python scripts/sync_package.py --package mlc-llm --package-name mlc-llm --revision origin/main --skip-conda
fi
# build mlc-llm
./scripts/build_mlc_llm_lib_apple_silicon.sh

# build wheel
cd mlc-llm/python && python setup.py bdist_wheel && cd -

# deploy wheel
if [ "$deploy" -eq "1" ]; then
  python scripts/wheel_upload.py --repo mlc-ai/package --tag v0.9.dev0 mlc-llm/python/dist
fi
