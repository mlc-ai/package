# FlashKDA wheels for B200

Built from [MoonshotAI/FlashKDA](https://github.com/MoonshotAI/FlashKDA/tree/7afb9f454f160a6c4bbc0999beca0a8c40a38934)
at commit `7afb9f454f160a6c4bbc0999beca0a8c40a38934`, with CUTLASS
`5c149f52a436782210263fb2f19b354443a61c6a`.

- CPython 3.12 and 3.13, Linux x86_64, glibc 2.32 or newer.
- PyTorch 2.13.0+cu132.
- NVIDIA B200 (`sm_100a`); other GPU architectures are not included.

Python and native kernel files are unchanged from the upstream build. The wheels
include the FlashKDA MIT license and the CUTLASS BSD-3-Clause license.
SHA256SUMS records the distribution hashes.

To rebuild for this target, install the matching PyTorch version and CUDA Toolkit,
check out the upstream commit with its submodules, then run:

```bash
FLASH_KDA_CUDA_ARCHS=100a python -m pip wheel --no-build-isolation --no-deps .
```

The distributed wheels add the CUTLASS license notice to the wheel metadata.
Their Python and compiled kernel contents match the original upstream builds
byte for byte.
