# mlc-ai

Nightly and stable wheel builds for `mlc-ai` (TVM) and `mlc-llm`, published to
the `v0.9.dev0` release and indexed at https://mlc.ai/wheels.

This folder does not follow the standard package layout: it holds the build
scripts for upstream projects that are cloned at build time.

```text
packages/mlc-ai/
  scripts/            sync, build, upload, and prune scripts
  conda/              conda build environments
  docker/             build images (mlcaidev/package-*, mlcaidev/ci-*)
  3rdparty/tlcpack/   tlcpack submodule (conda recipes)
```

Workflows: `wheel_manylinux.yaml`, `wheel_win.yaml`, `wheel_applesiliconmac.yaml`,
`prune_nightly.yaml`, `build_docker_package.yaml`, and `build_docker_ci.yaml`.
The wheel workflows run from this folder; the upstream checkouts land in
`tvm/` and `mlc-llm/` here. They build nightly, on manual runs, and on pull
requests that change this folder. Only runs on `main` upload.
