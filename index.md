---
layout: default
title: MLC Packages
notitle: true
---

# MLC Packages

## MLC-AI & MLC-Chat

We provide pip wheels for MLC-AI and MLC-Chat nightly build, which can be installed with pip.
Select your operating system/compute platform and run the command in your terminal:

{::nomarkdown}
{% include table-mlc-ai.html %}
{:/nomarkdown}

All Linux/Windows packages (both CPU/CUDA versions) supports vulkan. If you are a AMD GPU user, please install the CPU version where you can use Vulkan for AMD GPUs.

## MLC-Chat-CLI

We provide conda packages for MLC-Chat-CLI nightly build, which can be installed with conda:

```bash
conda create -n mlc-chat-venv -c mlc-ai -c conda-forge mlc-chat-cli-nightly
conda activate mlc-chat-venv
```
