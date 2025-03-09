#!/bin/bash
set -exo pipefail

NODE_MAJOR=18
curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg
echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_$NODE_MAJOR.x nodistro main" >/etc/apt/sources.list.d/nodesource.list
apt-get -qy update
apt-get -qy install nodejs

git clone https://github.com/emscripten-core/emsdk.git /emsdk
cd /emsdk
./emsdk install 4.0.4
./emsdk activate 4.0.4
