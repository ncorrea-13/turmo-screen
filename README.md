# TURMO Linux UI modular alpha

Simple non-commercial modular Linux sender + PySide6 GUI for TURMO / UsbMonitor / Turing-style 3.5-inch USB serial screens.

Current default profile based on testing:

- Port: `/dev/ttyACM0`
- Baud: `4000000`
- Protocol: `reva`
- Framebuffer: `320x480`
- Pixel format: `rgb565le`

## Install

```bash
cd ~/Загрузки/turmo-linux-ui-modular
./install.sh
```

## Run GUI

```bash
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

## GIF support

GUI:

1. Press **Open GIF**.
2. Choose a `.gif`.
3. Set **GIF FPS**. Recommended: `3–8 FPS`.
4. Press **Play GIF**.
5. Press **Stop** to stop looping.

Full-screen GIFs are slow because 320×480 RGB565 is ~307 KB per frame. Small / low-FPS GIFs work better.

CLI examples:

```bash
python turmo_lite.py --gif sample_spinner.gif --gif-loop --gif-fps 8
```

Play one GIF cycle:

```bash
python turmo_lite.py --gif sample_spinner.gif --gif-fps 5
```

Save first prepared GIF frame:

```bash
python turmo_lite.py --gif sample_spinner.gif --dry-run gif_first.png
```

## Image examples

```bash
python turmo_lite.py --image picture.png --pink-bg --green-to-bg --red-to-blue --force-black --once
```

## Test pattern

```bash
python turmo_lite.py --test-pattern --once
```

## Notes

- `turmo_lite.py` remains a backward-compatible CLI wrapper.
- `turmo_gui.py` remains a backward-compatible GUI wrapper.
- Real implementation lives in the `turmo/` package. See `ARCHITECTURE.md`.
- GIF playback currently sends full frames for reliability. Partial-window GIF updates can be added later after the RevA protocol is fully stable on the device.

## Production (container)

CI builds and pushes the image on every push to `main` (see `.github/workflows/ci.yml`),
tagged `latest`, `<branch>`, and `<sha>` at `ghcr.io/<owner>/<repo>`.

`compose.yaml`:

```yaml
services:
  turmo:
    image: ghcr.io/ncorrea-13/turmo-linux-ui-modular:latest
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
- Default entrypoint runs `--fleet --port /dev/ttyACM0` (see `Containerfile`); override `command:` for a different mode.
- No GUI in this image (`PySide6` dropped, see `requirements-docker.txt`) — headless dashboard only.
