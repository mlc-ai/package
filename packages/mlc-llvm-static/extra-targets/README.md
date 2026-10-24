# mlc-llvm-static-extra-targets

Additional LLVM code-generation backends for the matching `mlc-llvm-static`
native SDK. Install `mlc-llvm-static[all]` to get both.

The two wheels own disjoint files under the same SDK prefix and require exactly
the same version. The add-on is specific to the host platform, even though it
generates code for other targets. It does not include Clang, linkers, target
sysroots, or other LLVM tools.

Both wheels come from one All-target LLVM build: build and verify them with
`packages/mlc-llvm-static/scripts/build_wheels.py`, which requires
`MLC_LLVM_STATIC_ALLOW_SOURCE_BUILD=1`. The add-on shares the version in
`packages/mlc-llvm-static/version.py` and is published as wheels only. See the
[mlc-llvm-static README](https://github.com/mlc-ai/package/blob/main/packages/mlc-llvm-static/README.md)
for usage.
