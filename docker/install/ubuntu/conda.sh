#!/bin/bash
set -exo pipefail

export MAMBA_EXE='/usr/local/bin/micromamba'
export MAMBA_ROOT_PREFIX='/root/micromamba'

curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xvj bin/micromamba
cp bin/micromamba $MAMBA_EXE
ln -s $MAMBA_EXE /usr/local/bin/conda

conda shell init -s bash -p $MAMBA_ROOT_PREFIX
conda env create --yes -f /conda_envs/ci-lint.yml
