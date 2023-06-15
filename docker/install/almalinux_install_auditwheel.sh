#!/bin/bash

set -e

source /multibuild/manylinux_utils.sh

# use a forked version with skip-libs option
git clone https://github.com/mlc-ai/auditwheel
cd auditwheel
python3 setup.py install
