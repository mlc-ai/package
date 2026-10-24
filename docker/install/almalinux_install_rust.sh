#!/bin/bash
set -euxo pipefail

export RUSTUP_HOME=/opt/rust
export CARGO_HOME=/opt/rust

# this rustc is one supported by the installed version of rust-sgx-sdk
HOST_ARG=
if [ "$(getconf LONG_BIT)" == "32" ]; then
    # When building in the i386 docker image on a 64-bit host, rustup doesn't
    # correctly detect the arch to install for so set it manually
    HOST_ARG="--default-host i686-unknown-linux-gnu"
fi

# shellcheck disable=SC2086 # word splitting is intentional here
curl -s -S -L https://sh.rustup.rs -sSf | sh -s -- -y --no-modify-path --profile minimal --default-toolchain stable $HOST_ARG
export PATH=$CARGO_HOME/bin:$PATH
rustup component add rustfmt
rustup component add clippy

# make rust usable by all users after install during container build
chmod -R a+rw /opt/rust