<div align="center">

# TURMO Linux

**Modular Linux sender + PySide6 GUI for TURMO / UsbMonitor / Turing-style 3.5" USB serial screens**

[![CI](https://github.com/ncorrea-13/turmo-screen/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ncorrea-13/turmo-screen/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Podman/Docker](https://img.shields.io/badge/Container-GHCR-2496ED?logo=docker&logoColor=white)](https://github.com/ncorrea-13?tab=packages&repo_name=turmo-screen)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](#license)

[Español](README.es.md)

</div>

---

Sends a system dashboard, static images, test patterns, or a live view of your other
homelab machines (via [Heimdall](https://github.com/kinncj/Heimdall)) to a small USB serial screen over the RevA protocol. Non-commercial, personal-use project.

Tested screen profile:

| Port           | Baud      | Protocol | Framebuffer | Pixel format |
| -------------- | --------- | -------- | ------------ | ------------ |
| `/dev/ttyACM0` | `4000000` | `reva`   | `320x480`    | `rgb565le`   |

## Stack

| Layer          | Tech                                            |
| -------------- | ------------------------------------------------ |
| Language       | Python 3.14                                      |
| GUI            | PySide6 (desktop only, not in the container image) |
| Image/pixel    | Pillow                                           |
| Serial         | pyserial                                         |
| Remote metrics | [Heimdall](https://github.com/kinncj/Heimdall) (`heimdall-cli`, external binary) |
| Container      | Podman/Docker, `python:3.14-alpine`              |

More: [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Quick start

```bash
git clone https://github.com/ncorrea-13/turmo-screen.git
cd turmo-screen
./install.sh        # creates .venv, installs requirements.txt
./run_gui.sh
```

If the screen gives a permission error:

```bash
sudo chmod a+rw /dev/ttyACM0
```

Permanent fix:

```bash
sudo usermod -aG dialout "$USER"
sudo usermod -aG uucp "$USER"
reboot
```

`turmo_lite.py`/`turmo_gui.py` are the CLI/GUI entry points; real implementation lives in `turmo/`.

## Homelab dashboard (other machines)

Instead of this host's own metrics, show live stats from every machine in your homelab:

```bash
python turmo_lite.py --fleet --width 480 --height 320 --orientation landscape
```

Reads `HEIMDALL_HUB` (default `localhost:9090`) and `HEIMDALL_TOKEN` from the environment;
needs `heimdall-cli` on `$PATH`. See [Development](#development-container) /
[Production](#production-container) below for the containerized setup.

### Daemon setup on each host

On every machine you want turmo to show, run `heimdall-daemon` pointed at the hub. Keep the
token out of the command line (same reasoning as the fix in `fetch_fleet_hosts`) — use an
env file, not `--token`:

```bash
mkdir -p ~/.config/heimdall
printf 'HEIMDALL_TOKEN=<same-token-as-the-hub>\n' > ~/.config/heimdall/daemon.env
chmod 600 ~/.config/heimdall/daemon.env

curl -fsSL https://github.com/kinncj/Heimdall/releases/download/v2.7.4/heimdall-daemon_linux_<arch> -o ~/.local/bin/heimdall-daemon
chmod +x ~/.local/bin/heimdall-daemon
```

`~/.config/systemd/user/heimdall-daemon.service`:

```ini
[Unit]
Description=Heimdall daemon

[Service]
EnvironmentFile=%h/.config/heimdall/daemon.env
ExecStart=%h/.local/bin/heimdall-daemon --hub <hub-host>:9090 --name %H
Restart=on-failure

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now heimdall-daemon.service
loginctl enable-linger "$USER"   # starts on boot without an active login session
```

TLS (`--tls`/`--tls-ca`) is optional here if the hub is only reachable over Tailscale — the
mesh already encrypts the transport. Add it if the hub is reachable over a less trusted network.

## GIF support

GUI: **Open GIF** → choose a `.gif` → set **GIF FPS** (`3–8` recommended) → **Play GIF** → **Stop** to end the loop.

Full-screen GIFs are slow: 320×480 RGB565 is ~307 KB/frame. Smaller/lower-FPS GIFs work better.

```bash
python turmo_lite.py --gif sample_spinner.gif --gif-loop --gif-fps 8   # loop
python turmo_lite.py --gif sample_spinner.gif --gif-fps 5              # one cycle
python turmo_lite.py --gif sample_spinner.gif --dry-run gif_first.png  # save first frame, no send
```

## Image examples

```bash
python turmo_lite.py --image your_image.png --fit contain --once
```

`--pink-bg`/`--green-to-bg`/`--red-to-blue`/`--force-black` are optional color-cleanup
flags for images with a chroma-key background; see `python turmo_lite.py --help`.

## Test pattern

```bash
python turmo_lite.py --test-pattern --once
```

## Development (container)

`compose.dev.yaml` builds `heimdall-hub` + `heimdall-daemon` (self-monitoring the dev
container, just to have something to display) + `turmo` from local sources — no image
registry needed:

```bash
podman-compose -f compose.dev.yaml up --build
```

Rebuild after code changes with `--build` again. Needs `/dev/ttyACM0` present on the host.

## Production (container)

CI builds and pushes the image on every push to `main` (see `.github/workflows/ci.yml`),
tagged `latest`, `<branch>`, and `<sha>` at `ghcr.io/<owner>/<repo>`.

`compose.yaml`:

```yaml
services:
  turmo:
    image: ghcr.io/ncorrea-13/turmo-screen:latest
    container_name: turmo
    restart: unless-stopped
    devices:
      - /dev/ttyACM0:/dev/ttyACM0
    environment:
      - HEIMDALL_HUB=heimdall-hub:9090
      - HEIMDALL_TOKEN=${HEIMDALL_TOKEN}
    logging:
      driver: journald
```

Notes:

- Swap the image tag/registry once the pipeline publishes the real one.
- `HEIMDALL_HUB`/`HEIMDALL_TOKEN` are read by `turmo/metrics.py:fetch_fleet_hosts`; omit `HEIMDALL_TOKEN` if the hub has no token configured.
- Default entrypoint runs `--fleet --port /dev/ttyACM0 --width 480 --height 320 --orientation landscape` (see `Containerfile`); override `command:` for a different mode.
- No GUI in this image (`PySide6` dropped, see `requirements-docker.txt`) — headless dashboard only.

## Testing

```bash
python -m unittest discover tests -v
```

No hardware needed — serial I/O is mocked. Covers parsing, pixel encoding, RevA coordinate
packing, and the Heimdall fetch/render error paths.

## Project structure

Real implementation lives in `turmo/`, entry points (`turmo_lite.py`/`turmo_gui.py`) are thin
backward-compatible wrappers. Full layout and send-pipeline notes: [`ARCHITECTURE.md`](ARCHITECTURE.md).

## About

Personal, non-commercial project. This codebase's own provenance (before the RevA protocol
was traced to its real source, and before the Heimdall/container work in this repo) is
murky — see [`NOTICE.md`](NOTICE.md) for what's actually known.

## License

GPL-3.0-or-later — see [LICENSE](LICENSE). The RevA serial protocol in
`turmo/serial_device.py` is reimplemented from
[turing-smart-screen-python](https://github.com/mathoudebine/turing-smart-screen-python)
by Matthieu Houdebine (GPL-3.0-or-later); as a combined work, this repo carries the same
license. Full provenance: [`NOTICE.md`](NOTICE.md).

**Nicolás Correa** — [github.com/ncorrea-13](https://github.com/ncorrea-13)
