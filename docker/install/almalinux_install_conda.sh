#!/bin/bash

set -e
set -u
set -o pipefail

cd /tmp && wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-${1}.sh
chmod +x Miniconda3-latest-Linux-${1}.sh
/tmp/Miniconda3-latest-Linux-${1}.sh -b -p /opt/conda
rm /tmp/Miniconda3-latest-Linux-${1}.sh
/opt/conda/bin/conda update --yes -n base -c defaults conda
/opt/conda/bin/conda install -n base conda-libmamba-solver
/opt/conda/bin/conda config --set solver libmamba
/opt/conda/bin/conda upgrade --all
/opt/conda/bin/conda clean -ya
chmod -R a+w /opt/conda/
