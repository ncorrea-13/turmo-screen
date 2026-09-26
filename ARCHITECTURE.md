# TURMO Linux modular architecture

The old alpha version had almost everything in `turmo_lite.py`. This build keeps
the old entry files, but moves the real code into the `turmo/` package.

## Layout

```text
turmo/
  cli.py             # argparse CLI loop
  gui.py             # PySide6 GUI
  constants.py       # screen defaults, pixel formats, protocol constants
  serial_device.py   # TURMO/RevA serial protocol and frame sending
  codecs.py          # RGB/RGB565/BGRA/etc pixel packing
  image_ops.py       # normalize, fit, rotate, margins, color cleanup
  gif.py             # GIF frame decoding/preparation
  renderers.py       # dashboard and test-pattern renderers
  metrics.py         # psutil/nvidia-smi metrics
  ports.py           # serial port discovery
  frame.py           # chooses dashboard/image/test frame
  core.py            # compatibility façade for old imports
  sources/           # future source abstraction for dashboard/GIF/screen capture
turmo_lite.py        # old CLI name, now a small wrapper
turmo_gui.py         # old GUI name, now a small wrapper
```

## Why this is better before screen streaming

Screen streaming should not be added inside one giant CLI or GUI loop. The clean
future shape is:

1. `sources/screen.py` captures the desktop and returns PIL images.
2. `image_ops.py` resizes/rotates/normalizes frames into the exact framebuffer.
3. `codecs.py` converts the image into the selected pixel format.
4. `serial_device.py` sends it through RevA or legacy protocol.
5. CLI/GUI only choose settings and start/stop the sender.

This means GIF, static images, dashboard, test-pattern and future screen capture
all use the same send pipeline.

## Compatibility

Existing commands are preserved:

```bash
python turmo_lite.py --help
python turmo_lite.py --test-pattern --dry-run preview.png
./run_gui.sh
```

Old GUI code that expected `turmo_lite.py` functions can still work through
`turmo.core`, but new code should import specific modules directly.
