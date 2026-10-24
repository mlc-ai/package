# Building Utils

[![Wheel-AppleSiliconMac](https://github.com/mlc-ai/package/actions/workflows/wheel_applesiliconmac.yaml/badge.svg)](https://github.com/mlc-ai/package/actions/workflows/wheel_applesiliconmac.yaml)
[![Wheel-Windows](https://github.com/mlc-ai/package/actions/workflows/wheel_win.yaml/badge.svg)](https://github.com/mlc-ai/package/actions/workflows/wheel_win.yaml)
[![Wheel-Manylinux](https://github.com/mlc-ai/package/actions/workflows/wheel_manylinux.yaml/badge.svg)](https://github.com/mlc-ai/package/actions/workflows/wheel_manylinux.yaml)
[![Prune-Nightly](https://github.com/mlc-ai/package/actions/workflows/prune_nightly.yaml/badge.svg)](https://github.com/mlc-ai/package/actions/workflows/prune_nightly.yaml)


## Package Layout

Native-artifact Python packages under `packages/` (currently `mlc-z3-static`,
`mlc-doxygen-bin`, and `mlc-llvm-static`) follow one standard layout:

```text
packages/<pkg>/
  pyproject.toml   scikit-build-core build; version read from version.py;
                   `test` extra, pytest testpaths, and cibuildwheel config
  version.py       single source of the package version and upstream pins
                   (release, commit, archive SHA-256); a bump edits only this
  CMakeLists.txt   runs scripts/prepare_<upstream>.py and installs its staged
                   output into the wheel
  README.md
  LICENSE
  scripts/
    prepare_<upstream>.py   download, verify, build, and stage the upstream
    stamp_version.py        apply a release suffix (e.g. .post1) to version.py
    copy_wheel.py           cibuildwheel repair command (keeps the wheel as is)
    cibuildwheel_run.sh     run the pinned cibuildwheel through uv
    wheel_manylinux_2_28.sh, wheel_macos.sh, wheel_windows.ps1
                            local release-wheel builds per platform
    ...                     platform build-tool installers, if needed
  python/<module>/  the Python package; _version.py is generated from
                    version.py at build time and gitignored
  tests/python/     pytest suite run against the installed wheel
```

Helpers are copied per package rather than shared so each package builds from
its own sdist.

`mlc-llvm-static` keeps this layout with its own build scripts instead of
cibuildwheel. Its wheel-only `mlc-llvm-static-extra-targets` add-on lives in
`packages/mlc-llvm-static/extra-targets/` and reads the parent `version.py`, so
both distributions share one version.
