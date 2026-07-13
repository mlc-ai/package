#!/usr/bin/env bash

# Remove the per-build source checkouts and generated artifacts. This runs as
# root inside the build container so it can delete root-owned files the build
# left behind; otherwise the self-hosted runner's next `git clone` fails with
# "destination path 'tvm' already exists". Remove the whole directories (not
# just their contents) so a stale .git can't linger either.
rm -rf /workspace/tvm /workspace/mlc-llm /workspace/nvshmem
