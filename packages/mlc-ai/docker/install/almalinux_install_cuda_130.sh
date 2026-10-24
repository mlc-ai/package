#!/bin/bash

set -e
set -o pipefail

dnf install epel-release -y
dnf update -y
rpm -q epel-release
yum config-manager --add-repo http://developer.download.nvidia.com/compute/cuda/repos/rhel8/x86_64/cuda-rhel8.repo
sed -i '2imodule_hotfixes=1' /etc/yum.repos.d/cuda-rhel8.repo
dnf install kernel-devel -y
# dnf install cuda-13-0 -y
wget https://developer.download.nvidia.com/compute/cuda/13.0.1/local_installers/cuda-repo-rhel8-13-0-local-13.0.1_580.82.07-1.x86_64.rpm
rpm -i cuda-repo-rhel8-13-0-local-13.0.1_580.82.07-1.x86_64.rpm
dnf clean all
dnf -y install cuda-toolkit-13-0

NCCL_VERSION=$(dnf --showduplicates list libnccl | grep "cuda13.0" | tail -1 | awk '{print $2}')
dnf install libnccl-$NCCL_VERSION libnccl-devel-$NCCL_VERSION libnccl-static-$NCCL_VERSION -y
dnf install nvshmem-cuda-13 -y
