#!/bin/bash

set -e
set -o pipefail

dnf install epel-release -y
dnf update -y
rpm -q epel-release
if [ "$1" == "aarch64" ]; then
  yum config-manager --add-repo http://developer.download.nvidia.com/compute/cuda/repos/rhel8/sbsa/cuda-rhel8.repo
else
  yum config-manager --add-repo http://developer.download.nvidia.com/compute/cuda/repos/rhel8/x86_64/cuda-rhel8.repo
fi
sed -i '2imodule_hotfixes=1' /etc/yum.repos.d/cuda-rhel8.repo
dnf install kernel-devel -y
dnf install cuda-12-8 -y

NCCL_VERSION=$(dnf --showduplicates list libnccl | grep "cuda12.8" | tail -1 | awk '{print $2}')
dnf install libnccl-$NCCL_VERSION libnccl-devel-$NCCL_VERSION libnccl-static-$NCCL_VERSION -y
dnf install nvshmem -y
