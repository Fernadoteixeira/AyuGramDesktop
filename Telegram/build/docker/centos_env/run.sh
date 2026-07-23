#!/bin/bash

set -e
FullExecPath=$PWD
pushd `dirname $0` > /dev/null
FullScriptPath=`pwd`
popd > /dev/null

if [ ! -d "$FullScriptPath/../../../../../DesktopPrivate" ]; then
  echo ""
  echo "This script is for building the production version of Telegram Desktop."
  echo ""
  echo "For building custom versions please visit the build instructions page at:"
  echo "https://github.com/telegramdesktop/tdesktop/#build-instructions"
  exit
fi

Command=("$@")
if [ ${#Command[@]} -eq 0 ]; then
  Command=("bash")
fi

docker run -it --rm \
  --cpus="${DOCKER_CPUS:-16}" \
  --memory="${DOCKER_MEMORY:-24g}" \
  --memory-swap="${DOCKER_MEMORY_SWAP:-32g}" \
  --pids-limit=4096 \
  --shm-size=2g \
  --cap-drop=ALL \
  --security-opt=no-new-privileges=true \
  --read-only \
  --tmpfs=/tmp:rw,noexec,nosuid,size=4g \
  --tmpfs=/run:rw,noexec,nosuid,size=64m \
  --tmpfs=/var/tmp:rw,noexec,nosuid,size=1g \
  --user="$(id -u):$(id -g)" \
  --mount=type=bind,source="$HOME/Telegram/DesktopPrivate",target=/usr/src/DesktopPrivate,readonly \
  --mount=type=bind,source="$HOME/Telegram/tdesktop",target=/usr/src/tdesktop \
  tdesktop:centos_env \
  "${Command[@]}"
