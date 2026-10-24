#!/bin/bash

set -e
set -o pipefail

dnf install -y epel-release
dnf install -y vulkan-loader-devel
dnf install -y spirv-tools-devel
dnf install -y spirv-headers-devel
dnf install -y vulkan-validation-layers-devel
