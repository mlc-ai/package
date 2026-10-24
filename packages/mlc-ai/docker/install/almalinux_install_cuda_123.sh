#!/bin/bash

set -e
set -o pipefail

dnf install epel-release -y
dnf update -y
rpm -q epel-release
yum config-manager --add-repo http://developer.download.nvidia.com/compute/cuda/repos/rhel8/x86_64/cuda-rhel8.repo
sed -i '2imodule_hotfixes=1' /etc/yum.repos.d/cuda-rhel8.repo
dnf install kernel-devel -y
dnf install cuda-12-3 -y

NCCL_VERSION=$(dnf --showduplicates list libnccl | grep "cuda12.3" | tail -1 | awk '{print $2}')
dnf install libnccl-$NCCL_VERSION libnccl-devel-$NCCL_VERSION libnccl-static-$NCCL_VERSION -y
dnf install nvshmem-cuda-12 -y
