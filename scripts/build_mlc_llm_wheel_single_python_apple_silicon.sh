#!/bin/bash
set -euxo pipefail

eval "$(command conda 'shell.bash' 'hook' 2> /dev/null)"

CONDA_ENV_NAME=$1
deploy="${DEPLOY_WHEEL:-0}"
stable="${STABLE_BUILD:-0}"
MACOSX_DEPLOYMENT_TARGET=${MACOSX_DEPLOYMENT_TARGET:-13.02}

source $CONDA_HOME/etc/profile.d/conda.sh

echo "Start build for $CONDA_ENV_NAME"

# conda activate
conda activate $CONDA_ENV_NAME

# sync package
if [ "$stable" -eq "0" ]; then
  python scripts/sync_package.py --package mlc-llm --package-name mlc-llm-nightly --revision origin/main --skip-checkout
else
  python scripts/sync_package.py --package mlc-llm --package-name mlc-llm --revision origin/main
fi

# build mlc-llm
cd mlc-llm
rm -rf build
echo set\(CMAKE_OSX_DEPLOYMENT_TARGET ${MACOSX_DEPLOYMENT_TARGET}\) >>config.cmake
echo set\(USE_METAL ON\) >>config.cmake

pip wheel --no-deps -w dist . -v
cd ..

# deploy wheel
if [ "$deploy" -eq "1" ]; then
  python scripts/wheel_upload.py --repo mlc-ai/package --tag v0.9.dev0 mlc-llm/dist
fi
