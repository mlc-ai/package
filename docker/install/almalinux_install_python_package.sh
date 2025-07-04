#!/bin/bash

set -exo pipefail

source /multibuild/manylinux_utils.sh

eval "$(conda shell.bash hook)"

PYTHON_PACKAGES="six numpy pytest cython Cython decorator scipy tornado mypy \
antlr4-python3-runtime attrs requests Pillow packaging junitparser synr cloudpickle xgboost==1.5.0"

for env in $(conda env list | grep py | awk '{print $1}'); do
    conda activate "$env"
    pip install ${PYTHON_PACKAGES}
done
