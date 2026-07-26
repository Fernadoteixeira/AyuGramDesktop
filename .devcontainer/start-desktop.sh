#!/bin/bash

set -euo pipefail

StateDirectory="${XDG_STATE_HOME:-$HOME/.local/state}/ayugram-desktop"
RuntimeDirectory="${XDG_RUNTIME_DIR:-$HOME/.local/run}"
Display="${DISPLAY:-:1}"
Geometry="${AYUGRAM_DESKTOP_GEOMETRY:-1920x1080x24}"
VncPort="${AYUGRAM_VNC_PORT:-5900}"
WebPort="${AYUGRAM_DESKTOP_PORT:-6080}"
VncPassword="${AYUGRAM_VNC_PASSWORD:-ayugram}"

mkdir -p "$StateDirectory" "$RuntimeDirectory" "$HOME/.vnc" "$HOME/out" "/tmp/.X11-unix"
chmod 1777 "/tmp/.X11-unix"
chmod 700 "$StateDirectory" "$RuntimeDirectory" "$HOME/.vnc"

if [ "$(cat "$StateDirectory/container" 2>/dev/null || true)" != "${HOSTNAME:-unknown}" ]; then
	rm -f "$StateDirectory"/*.pid "$RuntimeDirectory/bus"
	printf '%s\n' "${HOSTNAME:-unknown}" >"$StateDirectory/container"
fi

startProcess() {
	local Name="$1"
	shift
	local Command="$1"
	local PidFile="$StateDirectory/$Name.pid"
	local Pid
	if [ -s "$PidFile" ]; then
		Pid="$(cat "$PidFile")"
		if [[ "$Pid" != *[!0-9]* ]] && kill -0 "$Pid" 2>/dev/null; then
			if grep -q "${Command##*/}" "/proc/$Pid/cmdline" 2>/dev/null || [ "$(cat "/proc/$Pid/comm" 2>/dev/null || true)" = "${Command##*/}" ]; then
				return
			fi
		fi
		rm -f "$PidFile"
	fi
	"$@" >"$StateDirectory/$Name.log" 2>&1 &
	echo $! >"$PidFile"
}

if [ -s "$StateDirectory/password" ]; then
	VncPassword="$(cat "$StateDirectory/password")"
else
	umask 077
	printf '%s\n' "$VncPassword" >"$StateDirectory/password"
fi

if [ ! -s "$StateDirectory/vnc.passwd" ]; then
	x11vnc -storepasswd "$VncPassword" "$StateDirectory/vnc.passwd" >/dev/null
fi

DisplayNumber="${Display#:}"

# Clean up stale Xvfb lock files and sockets if Xvfb isn't running
LockFile="/tmp/.X${DisplayNumber}-lock"
if [ -f "$LockFile" ]; then
	LockPid="$(cat "$LockFile" 2>/dev/null || true)"
	if [ -z "$LockPid" ] || [[ "$LockPid" =~ [^0-9] ]] || ! kill -0 "$LockPid" 2>/dev/null; then
		rm -f "$LockFile" "/tmp/.X11-unix/X${DisplayNumber}"
	fi
fi

startProcess xvfb Xvfb "$Display" -screen 0 "$Geometry" -dpi 96 -nolisten tcp -ac

for ((Attempt = 1; Attempt <= 100; ++Attempt)); do
	if [ -S "/tmp/.X11-unix/X$DisplayNumber" ]; then
		break
	fi
	if [ "$Attempt" -eq 100 ]; then
		printf 'Xvfb did not become ready on %s.\n' "$Display" >&2
		exit 1
	fi
	sleep 0.1
done

export DISPLAY="$Display"
export XDG_RUNTIME_DIR="$RuntimeDirectory"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$RuntimeDirectory/bus"

if [ -S "$RuntimeDirectory/bus" ]; then
	if [ -s "$StateDirectory/dbus.pid" ]; then
		DbusPid="$(cat "$StateDirectory/dbus.pid")"
		if ! kill -0 "$DbusPid" 2>/dev/null; then
			rm -f "$RuntimeDirectory/bus" "$StateDirectory/dbus.pid"
		fi
	else
		rm -f "$RuntimeDirectory/bus"
	fi
fi

if [ ! -S "$RuntimeDirectory/bus" ]; then
	dbus-daemon --session --fork --address="$DBUS_SESSION_BUS_ADDRESS" --print-pid=1 >"$StateDirectory/dbus.pid"
fi

cat >"$StateDirectory/session.env" <<EOF
export DISPLAY='$Display'
export XDG_RUNTIME_DIR='$RuntimeDirectory'
export DBUS_SESSION_BUS_ADDRESS='$DBUS_SESSION_BUS_ADDRESS'
export QT_QPA_PLATFORM='xcb'
export QT_X11_NO_MITSHM='1'
export LIBGL_ALWAYS_SOFTWARE='1'
EOF

startProcess fluxbox fluxbox
startProcess x11vnc x11vnc -display "$Display" -localhost -forever -shared -rfbport "$VncPort" -rfbauth "$StateDirectory/vnc.passwd"
startProcess websockify websockify --web=/usr/share/novnc "0.0.0.0:$WebPort" "localhost:$VncPort"
startProcess xterm xterm -u8 -geometry 120x36+24+24 -title "AyuGram Development Environment" -bg "#1e1e1e" -fg "#d4d4d4"

/usr/local/bin/launch-ayugram --if-present

printf 'Desktop URL: http://localhost:%s/vnc.html?autoconnect=true&resize=scale&password=%s\n' "$WebPort" "$VncPassword"
printf 'VNC Password: %s\n' "$VncPassword"

wait