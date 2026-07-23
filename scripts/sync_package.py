"""Synchronize name and the tvm version"""

import argparse
import os
import re
import subprocess
import sys

# Tag used for stable build, taken from the MLC_STABLE_BUILD_VER environment
# variable. There is intentionally no default: a stable build must specify the
# tag explicitly (otherwise we error out below rather than silently build a
# stale/wrong tag).
__stable_build__ = os.environ.get("MLC_STABLE_BUILD_VER")


def py_str(cstr):
    return cstr.decode("utf-8")


def checkout_source(src, tag):
    def run_cmd(cmd):
        proc = subprocess.Popen(
            cmd, cwd=src, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
        (out, _) = proc.communicate()
        if proc.returncode != 0:
            msg = "git error: %s" % cmd
            msg += py_str(out)
            raise RuntimeError(msg)

    run_cmd(["git", "checkout", "-f", tag])
    # --init --recursive so nested submodules are synced to the tag too: e.g.
    # mlc-llm pins 3rdparty/tvm, which pins its own 3rdparty/tvm-ffi. A plain
    # `submodule update` moves 3rdparty/tvm to the tag but leaves the nested
    # tvm-ffi at whatever the initial clone had, so tvm gets built against a
    # mismatched tvm-ffi.
    run_cmd(["git", "submodule", "update", "--init", "--recursive"])
    print("git checkout %s" % tag)


def update(file_name, rewrites, dry_run=False):
    update = []
    need_update = False
    for l in open(file_name):
        for pattern, target in rewrites:
            result = re.findall(pattern, l)
            if result and result[0] != target:
                l = re.sub(pattern, target, l)
                need_update = True
                print("%s: %s -> %s" % (file_name, result[0], target))
                break

        update.append(l)

    if need_update and not dry_run:
        with open(file_name, "w") as output_file:
            for l in update:
                output_file.write(l)


def name_with_gpu(args, package_name):
    """Update name with GPU version"""
    if args.gpu == "none":
        return package_name + "-cpu"
    elif args.gpu.startswith("rocm"):
        return package_name + "-rocm" + "".join(args.gpu[5:].split("."))
    else:
        return package_name + "-cu" + "".join(args.gpu[5:].split("."))


def run_version_py(args):
    version_py = os.path.join(args.package, "version.py")
    if __stable_build__ and "nightly" not in args.package_name:
        # stable version comes from the requested tag; the tag's version.py may predate fixes
        rewrites = [
            (r'(?m)(?<=(?<![^\n])version = ")[^\n"]+(?=")', __stable_build__.lstrip("v")),
        ]
        update(os.path.join(args.package, "pyproject.toml"), rewrites, args.dry_run)
    elif os.path.exists(version_py):
        # check=True so wheels never ship the placeholder version from pyproject.toml
        subprocess.run([sys.executable, version_py, "--git-describe"], check=True)
    else:
        # tvm stamps its own version at build time
        print("%s not found; skipping version bump for %s" % (version_py, args.package))
    # Update package name
    rewrites = [
        (r'(?m)(?<=(?<![^\n])name = ")[^\n"]+(?=")', name_with_gpu(args, args.package_name)),
    ]
    update(os.path.join(args.package, "pyproject.toml"), rewrites, args.dry_run)


def main():
    parser = argparse.ArgumentParser(
        description="Synchronize the package name and version."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run the syncronization process without modifying any files.",
    )
    parser.add_argument(
        "--package", type=str, required=True, help="The package to sync for."
    )
    parser.add_argument(
        "--package-name", type=str, required=True, help="The output package name"
    )
    parser.add_argument(
        "--revision",
        type=str,
        default="origin/main",
        help="Specify a revision to build packages from. " "Defaults to 'origin/main'",
    )
    parser.add_argument(
        "--gpu",
        type=str,
        default="none",
        choices=[
            "none",
            "cuda-12.8",
            "cuda-13.0",
            "rocm-6.1",
            "rocm-6.2",
        ],
        help="GPU (CUDA/ROCm) version to be linked to the resultant binaries,"
        "or none, to disable CUDA/ROCm. Defaults to none.",
    )
    parser.add_argument(
        "--skip-checkout",
        action="store_true",
        help="Run the syncronization process without checking out new source."
        "For use when running in an existing checkout.",
    )
    args = parser.parse_args()

    if not args.skip_checkout:
        if "nightly" not in args.package_name:
            # `not` (rather than `is None`) so an unset OR empty-string env var both
            # error out. CI sets `env: X: ${{ ... }}`, which yields "" (not unset)
            # when the expression is empty, so `is None` would miss that case.
            if not __stable_build__:
                raise RuntimeError(
                    "Stable build requires the MLC_STABLE_BUILD_VER environment variable "
                    "to be set to the tag to build (e.g. v0.20.0)."
                )
            checkout_source(args.package, __stable_build__)
        else:
            checkout_source(args.package, args.revision)

    run_version_py(args)


if __name__ == "__main__":
    main()
