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

All Linux/Windows packages (both CPU/CUDA versions) supports Vulkan.

### Note for Pip Installation under Conda

If you install the pip wheel under a Conda environment, please also install the latest gcc
in Conda to resolve possible libstdc++.so issue:
```bash
conda install -c conda-forge gcc
```

## MLC-Chat-CLI

We provide conda packages for MLC-Chat-CLI nightly build, which can be installed with conda:

```bash
conda create -n mlc-chat-venv -c mlc-ai -c conda-forge mlc-chat-cli-nightly
conda activate mlc-chat-venv
```
