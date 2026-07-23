# Docker development environment

The Docker development environment provides a reproducible Rocky Linux 8 toolchain for AyuGram Desktop. It is designed for Docker Desktop with the WSL2 backend and for the GitHub Actions container pipeline.

## Architecture

| Layer                     | Purpose                                                  | Persistence                        |
| ------------------------- | -------------------------------------------------------- | ---------------------------------- |
| Workspace bind mount      | Source tree and Git state                                | Host filesystem                    |
| `ayugram-dev-home`        | VS Code state, caches, and `/home/user/out` build output | Docker named volume                |
| Read-only container layer | Rocky Linux toolchain and native dependencies            | Recreated from the published image |
| Temporary filesystems     | `/tmp`, `/run`, and `/var/tmp`                           | Removed with the container         |
| noVNC desktop             | Xvfb, Fluxbox, xterm, and AyuGram UI                     | Loopback port `6080`               |

The build directory inside the named home volume avoids the bind-mount I/O penalty on Docker Desktop. Build products remain available across container rebuilds but are intentionally kept outside the Git worktree. The image user remains UID 1000 because mutating `/etc/passwd` is incompatible with the read-only root filesystem. Docker Desktop bind mounts do not require host UID remapping.

## Resource profile

The shared configuration targets a workstation with at least 32 logical processors and 64 GB of RAM.

| Resource         |           WSL2 ceiling |           Container limit |
| ---------------- | ---------------------: | ------------------------: |
| CPU              |  16 logical processors |                   16 CPUs |
| Memory           |                  32 GB |                     24 GB |
| Memory plus swap |                  48 GB |                     32 GB |
| Shared memory    | Not separately limited |                      2 GB |
| Processes        | Not separately limited |                 4096 PIDs |
| Required storage |                 100 GB | Persistent Docker volumes |

On Windows, `%UserProfile%\.wslconfig` carries the WSL2 ceiling. Apply changes with `wsl --shutdown`, then start Docker Desktop again.

## Isolation model

The default container:

- runs as the non-root `user` account;
- uses Docker's minimal init process to reap build subprocesses;
- drops every Linux capability;
- enables `no-new-privileges`;
- uses a read-only root filesystem;
- exposes no Docker socket;
- publishes the authenticated noVNC desktop only through a host-loopback forwarded port;
- mounts only the workspace and named development volumes;
- uses `noexec` and `nosuid` temporary filesystems;
- does not permit `ptrace` debugging.

Native debugging requires an explicitly weakened local container profile. Do not add `SYS_PTRACE` or `seccomp=unconfined` to the shared configuration.

The container retains outbound network access for VS Code extensions and dependency tooling. Treat source code and build scripts as trusted inputs. Network egress filtering, when required, belongs in a dedicated Docker network or host firewall policy and should not be bypassed by mounting the Docker socket.

## Bootstrap

1. Start Docker Desktop with the WSL2 engine.
2. Confirm that Docker Desktop can access GitHub Container Registry.
3. Open the repository in VS Code.
4. Run `Dev Containers: Reopen in Container`.

The container builds its graphical layer from the upstream Telegram Desktop environment by immutable digest, so bootstrap does not depend on a mutable tag or on the first AyuGram publication. A push to `dev` publishes immutable toolchain and UI images with SBOM and provenance. The workflow promotes both digests to their `:dev` tags only after both critical-vulnerability gates pass. Adopt published AyuGram images only by digest after successful publication and scan.

## Graphical desktop

The Dev Container starts an isolated software-rendered X11 desktop and forwards noVNC through VS Code. It does not require WSLg or a Windows X server.

Open:

```text
http://127.0.0.1:6080/vnc.html?autoconnect=true&resize=scale
```

Retrieve the persistent VNC password from the Dev Container terminal:

```bash
cat ~/.local/state/ayugram-desktop/password
```

The desktop starts Fluxbox and an xterm immediately. If a Telegram binary exists under `/home/user/out/Debug`, `/home/user/out/Release`, or `/home/user/out`, it starts automatically. Launch an existing build manually with:

```bash
launch-ayugram
```

Inspect desktop and application logs with:

```bash
ls -1 ~/.local/state/ayugram-desktop/*.log
```

The graphical layer uses software rendering and intentionally does not mount host audio, GPU, Wayland, Docker, or D-Bus sockets.

## Persistence operations

List the persistent volumes:

```powershell
docker volume ls --filter name=ayugram-dev
```

Inspect their storage usage:

```powershell
docker system df -v
```

Reset only generated build output:

```powershell
docker run --rm --mount type=volume,source=ayugram-dev-home,target=/home/user ghcr.io/telegramdesktop/tdesktop/centos_env@sha256:94a14999adb4b9b34d4f0b758b890474c51ceb35c5c327a682e3e3fc830062ae rm -rf /home/user/out
```

Reset all container-local development state:

```powershell
docker volume rm ayugram-dev-home
```

Stop the Dev Container before removing a volume. Source code and Git state are not stored in these volumes.

## CI/CD

The `Development container` workflow has two trust boundaries:

- pull requests receive read-only repository permissions and run Dockerfile rendering plus BuildKit validation;
- manual dispatches run validation only;
- pushes to `dev` receive package, attestation, and security-report permissions after validation succeeds.

Published toolchain and UI images use digest-pinned bases, GitHub Actions cache storage, OCI metadata, BuildKit SBOM generation, maximum provenance, immutable full-commit tags, and Trivy scanning. SARIF upload is non-blocking so findings remain visible when GitHub code scanning is unavailable. Promotion of both mutable `dev` tags is blocked when either image contains a fixed critical vulnerability.

All third-party Actions are pinned to full commit SHAs. Dependabot checks those pins and the Rocky Linux base digest weekly.

## Rollback

To roll back the development environment, replace the image digest in `.devcontainer.json` with a previously verified digest and rebuild the container. Named volumes are preserved across this operation.

## Secret handling

Do not bake Telegram API credentials, signing material, SSH agents, Docker credentials, or the Docker socket into the image. Configure application credentials outside version control. The production helper mounts `DesktopPrivate` read-only.
