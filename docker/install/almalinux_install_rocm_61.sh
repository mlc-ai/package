#!/bin/bash

set -e
set -o pipefail

dnf install -y epel-release

for ver in 6.1; do
tee --append /etc/yum.repos.d/rocm.repo <<EOF
[ROCm-$ver]
name=ROCm$ver
baseurl=https://repo.radeon.com/rocm/rhel8/$ver/main
enabled=1
priority=50
gpgcheck=1
gpgkey=https://repo.radeon.com/rocm/rocm.gpg.key
EOF
done

dnf install -y rocm-hip-sdk
