#!/bin/bash
set -e
set -o pipefail

cd /tmp && wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
chmod +x Miniconda3-latest-Linux-x86_64.sh
/tmp/Miniconda3-latest-Linux-x86_64.sh -b -p /opt/conda
rm /tmp/Miniconda3-latest-Linux-x86_64.sh
chmod -R a+w /opt/conda/
conda update --yes -n base -c defaults conda
conda install -n base conda-libmamba-solver
conda config --set solver libmamba
conda upgrade --all
conda install conda-build conda-verify

conda env create -y -n ci-lint -f /install/conda/ci-lint.yml
conda env create -y -n ci-unittest -f /install/conda/ci-unittest.yml
conda clean --yes --all
