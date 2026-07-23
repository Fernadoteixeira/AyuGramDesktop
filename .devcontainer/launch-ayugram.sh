#!/bin/bash

set -euo pipefail

StateDirectory="${XDG_STATE_HOME:-$HOME/.local/state}/ayugram-desktop"
IfPresent=false

if [ "${1:-}" = "--if-present" ]; then
	IfPresent=true
fi

if [ -f "$StateDirectory/session.env" ]; then
	source "$StateDirectory/session.env"
fi

Candidates=(
	"$HOME/out/Debug/Telegram"
	"$HOME/out/Release/Telegram"
	"$HOME/out/Telegram"
	"/usr/src/tdesktop/out/Debug/Telegram"
	"/usr/src/tdesktop/out/Release/Telegram"
)

for Binary in "${Candidates[@]}"; do
	if [ -x "$Binary" ]; then
		if [ -s "$StateDirectory/ayugram.pid" ] && kill -0 "$(cat "$StateDirectory/ayugram.pid")" 2>/dev/null; then
			exit 0
		fi
		"$Binary" >"$StateDirectory/ayugram.log" 2>&1 &
		echo $! >"$StateDirectory/ayugram.pid"
		printf 'AyuGram started from %s\n' "$Binary"
		exit 0
	fi
done

if [ "$IfPresent" = true ]; then
	exit 0
fi

printf 'No AyuGram binary found under %s or /usr/src/tdesktop/out.\n' "$HOME/out" >&2
exit 1