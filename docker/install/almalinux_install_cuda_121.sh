#!/bin/bash

set -e
set -o pipefail

dnf install epel-release -y
dnf update -y
rpm -q epel-release
yum config-manager --add-repo http://developer.download.nvidia.com/compute/cuda/repos/rhel8/x86_64/cuda-rhel8.repo
dnf install kernel-devel -y
dnf install cuda-12-1 -y
dnf install libnccl libnccl-devel libnccl-static -y
