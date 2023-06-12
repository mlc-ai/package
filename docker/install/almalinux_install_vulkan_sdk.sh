#!/bin/bash

set -e
set -o pipefail

yum install vulkan-headers vulkan-loader-devel vulkan-tools spirv-tools -y
dnf --enablerepo=powertools install spirv-tools-devel -y
