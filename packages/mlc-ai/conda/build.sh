#!/bin/bash
# quick recipe for local build
# not used in action as the shell code also need to work in windows

set -euxo pipefail

if [ $#  -ne 1 ]; then
    echo "Usage: conda/run_build.sh <pkg>"
    exit 1
fi

pkg=$1

conda build -c conda-forge --output-folder=conda/pkg -m conda/$pkg/build_config.yaml conda/$pkg/recipe
