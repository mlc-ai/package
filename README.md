# Packaging Utils

This project contains a set of packaging utils to build packages in the
community. Each package lives in `packages/<package>/` with its own README and
GitHub Actions workflow.

| Package | Workflow | Published to |
| --- | --- | --- |
| [`mlc-z3-static`](packages/mlc-z3-static) | `mlc_z3_static_wheel.yml` | PyPI |
| [`mlc-doxygen-bin`](packages/mlc-doxygen-bin) | `mlc_doxygen_bin_wheel.yml` | PyPI |
| [`mlc-llvm-static`](packages/mlc-llvm-static) | `mlc_llvm_static_wheel.yml` | PyPI |
| [`mlc-ai`](packages/mlc-ai) (`mlc-ai`, `mlc-llm` wheels) | `wheel_manylinux.yaml`, `wheel_win.yaml`, `wheel_applesiliconmac.yaml` | [mlc.ai/wheels](https://mlc.ai/wheels) |

`docker/` at the repo root holds the build environment images, built manually
by `build_docker_package.yaml` and `build_docker_ci.yaml`.

## When workflows run

- **Pull requests** build a package only when files in its `packages/<package>/`
  folder or its own workflow file change. Changes that touch only Markdown files
  there do not trigger a build. Pull request runs never publish.
- **Manual runs** (Actions -> workflow -> Run workflow) build every platform.
  The PyPI packages publish only when *Publish to PyPI* is checked, optionally
  to a custom repository URL; `version_suffix` stamps a suffix such as `.post1`.
- **Nightly**: the `mlc-ai` wheel workflows build on a daily schedule and upload
  from `main`; `prune_nightly.yaml` then prunes old nightly wheels and refreshes
  the wheel index.

## Package Layout

Native-artifact Python packages under `packages/` follow one standard layout:

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
