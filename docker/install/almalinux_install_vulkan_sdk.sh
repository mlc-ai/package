#!/bin/bash

set -e
set -o pipefail

export vulkan_version="1.3.236.0"
mkdir -p ~/vulkan
cd /tmp
wget https://sdk.lunarg.com/sdk/download/${vulkan_version}/linux/vulkansdk-linux-x86_64-${vulkan_version}.tar.gz
tar xf vulkansdk-linux-x86_64-${vulkan_version}.tar.gz -C ~/vulkan
rm vulkansdk-linux-x86_64-${vulkan_version}.tar.gz
export VULKAN_SDK=~/vulkan/${vulkan_version}/x86_64
cp -ar $VULKAN_SDK/include/* /usr/include/
cp -p $VULKAN_SDK/lib/libSPIRV* /usr/lib64/
cp -P $VULKAN_SDK/lib/libvulkan* /usr/lib64/
cp -P $VULKAN_SDK/lib/libVkLayer_* /usr/lib64/
ln -s /usr/lib64/libSPIRV-Tools-shared.so /usr/lib64/libSPIRV-Tools.so
