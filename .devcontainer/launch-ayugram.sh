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

export DISPLAY="${DISPLAY:-:99}"

Candidates=(
	"$HOME/out/Debug/AyuGram"
	"$HOME/out/Release/AyuGram"
	"$HOME/out/AyuGram"
	"/usr/src/tdesktop/out/Debug/AyuGram"
	"/usr/src/tdesktop/out/Release/AyuGram"
	"/usr/src/tdesktop/out/AyuGram"
	"$HOME/out/Debug/Telegram"
	"$HOME/out/Release/Telegram"
	"$HOME/out/Telegram"
	"/usr/src/tdesktop/out/Debug/Telegram"
	"/usr/src/tdesktop/out/Release/Telegram"
	"/usr/src/tdesktop/out/Telegram"
	"/usr/src/tdesktop/Telegram/build/out/Debug/Telegram"
	"/usr/src/tdesktop/Telegram/build/out/Release/Telegram"
)

for Binary in "${Candidates[@]}"; do
	if [ -f "$Binary" ] && [ -x "$Binary" ]; then
		if [ -s "$StateDirectory/ayugram.pid" ] && kill -0 "$(cat "$StateDirectory/ayugram.pid")" 2>/dev/null; then
			exit 0
		fi
		"$Binary" >"$StateDirectory/ayugram.log" 2>&1 &
		echo $! >"$StateDirectory/ayugram.pid"
		printf 'AyuGram started from %s\n' "$Binary"
		exit 0
	fi
done

printf 'No AyuGram binary found.\n' >&2
printf 'Candidates checked:\n' >&2
for Binary in "${Candidates[@]}"; do
	printf ' - %s\n' "$Binary" >&2
done

if [ "$IfPresent" = true ]; then
	for Browser in chromium-browser chromium google-chrome firefox; do
		BrowserPath="$(command -v "$Browser" 2>/dev/null || true)"
		if [ -n "$BrowserPath" ]; then
			if [ -s "$StateDirectory/browser.pid" ] && kill -0 "$(cat "$StateDirectory/browser.pid")" 2>/dev/null; then
				exit 0
			fi
			"$BrowserPath" \
				--no-sandbox \
				--disable-dev-shm-usage \
				--no-first-run \
				--disable-gpu \
				--start-maximized \
				--user-data-dir="$StateDirectory/browser-profile" \
				'https://web.telegram.org/a/' \
				>"$StateDirectory/browser.log" 2>&1 &
			echo $! >"$StateDirectory/browser.pid"
			printf 'Telegram Web started via %s\n' "$BrowserPath"
			exit 0
		fi
	done
	exit 0
fi

exit 1