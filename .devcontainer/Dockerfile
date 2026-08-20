# syntax=docker/dockerfile:1

ARG BASE_IMAGE=ghcr.io/telegramdesktop/tdesktop/centos_env@sha256:94a14999adb4b9b34d4f0b758b890474c51ceb35c5c327a682e3e3fc830062ae
FROM ${BASE_IMAGE}

USER root
RUN dnf -y install epel-release \
	&& dnf config-manager --set-enabled powertools \
	&& dnf -y install dbus-x11 fluxbox novnc python3-websockify \
		x11vnc xorg-x11-server-Xvfb xterm mesa-dri-drivers xcb-util-cursor \
		xdotool wmctrl xorg-x11-utils ImageMagick clang \
	&& dnf clean all \
	&& rm -rf /var/cache/dnf

COPY --chmod=0755 .devcontainer/start-desktop.sh /usr/local/bin/start-ayugram-desktop
COPY --chmod=0755 .devcontainer/launch-ayugram.sh /usr/local/bin/launch-ayugram

USER user

CMD ["/usr/local/bin/start-ayugram-desktop"]