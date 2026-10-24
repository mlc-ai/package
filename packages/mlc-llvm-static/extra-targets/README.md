# mlc-llvm-static-extra-targets

Additional LLVM code-generation backends for the exact matching
`mlc-llvm-static` native SDK. Install `mlc-llvm-static[all]` to obtain both.
The two wheels own disjoint files under the same SDK prefix. The add-on is
specific to the host platform, even though it generates code for other targets.
It does not include Clang, linkers, target sysroots, or other LLVM tools.

Both payloads must come from one All-target LLVM build. Build and verify them
with `packages/mlc-llvm-static/scripts/build_wheels.py` in this repository.
Source compilation requires `MLC_LLVM_STATIC_ALLOW_SOURCE_BUILD=1`. This add-on
shares the version in `packages/mlc-llvm-static/version.py` and is published as
wheels only.
