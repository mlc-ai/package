#!/bin/bash
set -euxo pipefail

export TZ=America/Los_Angeles
echo $TZ >/etc/timezone
ln -snf /usr/share/zoneinfo/$TZ /etc/localtime

apt update
apt --yes full-upgrade
apt install --yes wget curl git zsh tmux htop vim ccache cmake subversion gdb build-essential unzip \
	software-properties-common locales tzdata apt-transport-https openssh-server libgtest-dev \
	python3-pip

locale-gen "en_US.UTF-8"

git config --global --add safe.directory "*"
