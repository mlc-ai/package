#!/bin/bash

set -e
set -o pipefail

dnf install epel-release -y
dnf update -y
rpm -q epel-release
yum config-manager --add-repo http://developer.download.nvidia.com/compute/cuda/repos/rhel8/x86_64/cuda-rhel8.repo
sed -i '2imodule_hotfixes=1' /etc/yum.repos.d/cuda-rhel8.repo
dnf install kernel-devel -y
# dnf install cuda-12-8 -y
wget https://developer.download.nvidia.com/compute/cuda/12.8.0/local_installers/cuda-repo-rhel8-12-8-local-12.8.0_570.86.10-1.x86_64.rpm
rpm -i cuda-repo-rhel8-12-8-local-12.8.0_570.86.10-1.x86_64.rpm
dnf clean all
dnf -y install cuda-toolkit-12-8

NCCL_VERSION=$(dnf --showduplicates list libnccl | grep "cuda12.8" | tail -1 | awk '{print $2}')
dnf install libnccl-$NCCL_VERSION libnccl-devel-$NCCL_VERSION libnccl-static-$NCCL_VERSION -y
dnf install nvshmem -y
