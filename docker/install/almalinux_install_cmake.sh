#!/bin/bash

set -e
set -u
set -o pipefail

dnf makecache --refresh
dnf -y install cmake
dnf -y --enablerepo=powertools install ninja-build
