#!/bin/bash

set -e
set -o pipefail

dnf makecache --refresh
dnf install -y llvm llvm-devel
dnf install -y libxml2-devel
