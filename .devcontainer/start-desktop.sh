#!/bin/bash

set -euo pipefail

StateDirectory="${XDG_STATE_HOME:-$HOME/.local/state}/ayugram-desktop"
RuntimeDirectory="${XDG_RUNTIME_DIR:-$HOME/.local/run}"
Display="${DISPLAY:-:1}"
Geometry="${AYUGRAM_DESKTOP_GEOMETRY:-1920x1080x24}"
VncPort="${AYUGRAM_VNC_PORT:-5900}"
WebPort="${AYUGRAM_DESKTOP_PORT:-6080}"

mkdir -p "$StateDirectory" "$RuntimeDirectory" "$HOME/.vnc" "$HOME/out"
chmod 700 "$StateDirectory" "$RuntimeDirectory" "$HOME/.vnc"

startProcess() {
	local Name="$1"
	shift
	local PidFile="$StateDirectory/$Name.pid"
	if [ -s "$PidFile" ] && kill -0 "$(cat "$PidFile")" 2>/dev/null; then
		return
	fi
	"$@" >"$StateDirectory/$Name.log" 2>&1 &
	echo $! >"$PidFile"
}

if [ ! -s "$StateDirectory/password" ]; then
	umask 077
	openssl rand -hex 16 >"$StateDirectory/password"
fi

if [ ! -s "$StateDirectory/vnc.passwd" ]; then
	x11vnc -storepasswd "$(cat "$StateDirectory/password")" "$StateDirectory/vnc.passwd" >/dev/null
fi

startProcess xvfb Xvfb "$Display" -screen 0 "$Geometry" -dpi 96 -nolisten tcp -ac

export DISPLAY="$Display"
export XDG_RUNTIME_DIR="$RuntimeDirectory"
export DBUS_SESSION_BUS_ADDRESS="unix:path=$RuntimeDirectory/bus"

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
startProcess xterm xterm -geometry 120x36+24+24 -title "AyuGram Development Environment"

/usr/local/bin/launch-ayugram --if-present

printf 'Desktop URL: http://localhost:%s/vnc.html?autoconnect=true&resize=scale\n' "$WebPort"
printf 'VNC password: %s\n' "$(cat "$StateDirectory/password")"