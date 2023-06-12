#!/bin/bash

set -e
set -o pipefail

dnf makecache --refresh
dnf install -y llvm llvm-devel
