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
cp -r $VULKAN_SDK/include/vulkan/ /usr/local/include/
cp -P $VULKAN_SDK/lib/libvulkan.so* /usr/local/lib/
cp $VULKAN_SDK/lib/libVkLayer_*.so /usr/local/lib/
mkdir -p /usr/local/share/vulkan/explicit_layer.d
cp $VULKAN_SDK/etc/vulkan/explicit_layer.d/VkLayer_*.json /usr/local/share/vulkan/explicit_layer.d

# Install SPIRV-Headers
git clone -b sdk-1.3.236 https://github.com/KhronosGroup/SPIRV-Headers.git
ln -s /usr/include/spirv SPIRV-Headers/include/spirv
