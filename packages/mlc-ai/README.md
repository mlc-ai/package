# mlc-ai

Nightly and stable wheel builds for `mlc-ai` and `mlc-llm`, published to the
`v0.9.dev0` GitHub release of this repository and indexed at
https://mlc.ai/wheels.

Unlike the other packages, this folder does not follow the standard package
layout: it holds build scripts for upstream projects that are cloned at build
time.

```text
packages/mlc-ai/
  scripts/            sync, build, upload, and prune scripts
  conda/              conda build environments
  3rdparty/tlcpack/   tlcpack submodule (conda recipes)
```

## Workflows

| Workflow | Builds |
| --- | --- |
| `wheel_manylinux.yaml` | Linux wheels (CPU, CUDA, ROCm), in the images from the repo-root `docker/` folder |
| `wheel_win.yaml` | Windows wheels |
| `wheel_applesiliconmac.yaml` | macOS arm64 wheels |
| `prune_nightly.yaml` | Prunes old nightly wheels and refreshes the wheel index |

The wheel workflows run from this folder; the upstream checkouts land in `tvm/`
and `mlc-llm/` here. They build nightly, on manual runs, and on pull requests
that change this folder (see the
[root README](../../README.md#when-workflows-run)). Only runs on `main` upload.

A manual run with an empty `tag` builds the nightly packages
(`mlc-ai-nightly-*`, `mlc-llm-nightly-*`). A manual run with a `tag` such as
`v0.20.0` builds the stable packages (`mlc-ai-*`, `mlc-llm-*`) from that tag,
which must exist in both mlc-ai/relax and mlc-ai/mlc-llm.
