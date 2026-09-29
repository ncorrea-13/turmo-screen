<div align="center">

# turmo-screen

**Server dashboard and media sender for TURMO / Turing-style 3.5" USB screens on Linux**

[![CI](https://github.com/ncorrea-13/turmo-screen/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/ncorrea-13/turmo-screen/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org)
[![Podman/Docker](https://img.shields.io/badge/Container-GHCR-2496ED?logo=docker&logoColor=white)](https://github.com/ncorrea-13?tab=packages&repo_name=turmo-screen)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/License-GPL--3.0--or--later-blue.svg)](#license)

[Español](README.es.md)

</div>

Sends a system dashboard, images, GIFs, test patterns, or a live view of your servers
(via [Heimdall](https://github.com/kinncj/Heimdall)) to a USB serial screen over the RevA protocol.

<p align="center">
  <img src="./pictures/fleet-landscape.png" alt="Server dashboard" width="480">
</p>

Unofficial project, not affiliated with TURMO or the screen's manufacturer.

Tested screen: `/dev/ttyACM0`, 4000000 baud, `reva`, 320x480, `rgb565le`.

## Quick start

```bash
git clone https://github.com/ncorrea-13/turmo-screen.git
cd turmo-screen
./scripts/install.sh    # creates .venv, installs requirements.txt
./scripts/run_gui.sh
```

Permission error on the port? `sudo usermod -aG dialout "$USER"` (`uucp` on Arch) and re-login.

## Usage

`turmo_lite.py` is the CLI, `turmo_gui.py` the GUI. Everything lives in `turmo/`.

```bash
python turmo_lite.py --test-pattern --once
python turmo_lite.py --image pic.png --fit contain --once
python turmo_lite.py --gif assets/sample_spinner.gif --gif-loop --gif-fps 5
python turmo_lite.py --gif assets/sample_spinner.gif --dry-run frame.png   # save first frame, no send
python turmo_lite.py --help
```

Full-screen GIFs are slow (~307 KB/frame). Keep them small, 3-8 FPS.

## Server dashboard

Live CPU/RAM/disk/temp for every server reporting to a Heimdall hub. Multi-server is supported: one hub, any number of daemons, one card per host.

```bash
python turmo_lite.py --fleet --width 480 --height 320 --orientation landscape
python turmo_lite.py --fleet ... --fleet-bg ~/wallpaper.jpg   # optional dimmed background
```

Needs `heimdall-cli` on `$PATH` plus `HEIMDALL_HUB` (default `localhost:9090`) and `HEIMDALL_TOKEN`
in the environment. Bars go yellow at 65% and red at 85%. More renders in [`pictures/`](pictures/).

Cards share the screen height, so around 4 hosts fit in landscape (480x320) and 7 in portrait (320x480). Beyond that, rows overflow.

### Heimdall setup

Hub, once, on any host (single static binary, use `_arm64` on ARM):

```bash
curl -fsSL https://github.com/kinncj/Heimdall/releases/download/v2.7.4/heimdall-hub_linux_amd64 -o /usr/local/bin/heimdall-hub
chmod +x /usr/local/bin/heimdall-hub
heimdall-hub --listen :9090
```

Daemon, on every server to monitor. Keep the token in an env file, not on the command line:

```bash
mkdir -p ~/.config/heimdall
printf 'HEIMDALL_TOKEN=<hub-token>\n' > ~/.config/heimdall/daemon.env && chmod 600 ~/.config/heimdall/daemon.env
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
loginctl enable-linger "$USER"   # start on boot without login
```

TLS (`--tls`/`--tls-ca`) is optional if the hub is only reachable over Tailscale. Add it on less trusted networks.

## Containers

Headless image (no GUI), default command is `--fleet --port /dev/ttyACM0 --width 480 --height 320 --orientation landscape`.
CI pushes it to `ghcr.io/ncorrea-13/turmo-screen` (`latest`, `<branch>`, `<sha>`).

```bash
# dev: builds hub + daemon + turmo from local sources
podman-compose -f deploy/compose.dev.yaml up --build

# prod: one container per screen, pointed at your existing hub
HEIMDALL_HUB=<hub-host>:9090 HEIMDALL_TOKEN=<token> podman-compose -f deploy/compose.prod.yaml up -d
```

Override `command:` in the compose file for another mode. Omit `HEIMDALL_TOKEN` if the hub has none.

## Tests

```bash
python -m unittest discover tests -v
```

No hardware needed, serial is mocked.

## Docs

[`ARCHITECTURE.md`](ARCHITECTURE.md) for layout and send pipeline. [`NOTICE.md`](NOTICE.md) for provenance and third-party licenses.

## License

GPL-3.0-or-later, see [LICENSE](LICENSE). The RevA protocol in `turmo/serial_device.py` is reimplemented from
[turing-smart-screen-python](https://github.com/mathoudebine/turing-smart-screen-python) (GPL-3.0-or-later).
Heimdall is **AGPL-3.0**. It runs as an unmodified external binary and is not bundled, see [`NOTICE.md`](NOTICE.md).

**Nicolás Correa** — [github.com/ncorrea-13](https://github.com/ncorrea-13)