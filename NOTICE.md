# Provenance / Credits

## RevA serial protocol — confirmed source

`turmo/serial_device.py`'s RevA command set and coordinate-packing
(`pack_reva_command`, `Command.*` values 101/102/103/108/109/110/121/197/69)
is a reimplementation of `LcdCommRevA` from:

- https://github.com/mathoudebine/turing-smart-screen-python
- Copyright (C) 2021 Matthieu Houdebine (mathoudebine)
- Licensed **GPL-3.0-or-later**

Same command bytes, same bit-packing formula. This repo is therefore a
combined/derivative work and is licensed **GPL-3.0-or-later** as a whole
(see `LICENSE`), regardless of what license the rest of the code would
otherwise carry.

## Everything else — unverified origin

The rest of this codebase (CLI/GUI wrapper, GIF handling, dashboard
rendering, project layout) was obtained as a `.zip` from a GitHub repo with
no license and no verifiable original author:

- https://github.com/vagimtemnikov2007-cmd/turomo-monitor-for-linux

That repo has 3 commits, no `LICENSE`, and contains only a `README.md` plus
the zip — no commit history for the actual source. The listed author
("Denis Temnikov") does not appear to be the original author either. Given
the confirmed GPL derivation above, this part is GPL-3.0-or-later too now
(as part of the combined work), independent of whoever wrote it originally.

## Third-party components used by this repo

- **[Heimdall](https://github.com/kinncj/Heimdall)** by kinncj — cross-platform
  fleet hardware monitor (hub/daemon/CLI), licensed **AGPL-3.0**. Used here as
  an external binary (`heimdall-cli`) queried over gRPC/JSON, not modified or
  linked into this codebase. See `turmo/metrics.py:fetch_fleet_hosts`.

  **Why this doesn't extend AGPL to this repo** (unlike the RevA case above):
  we download the official, unmodified `heimdall-cli` binary from upstream's
  GitHub releases and invoke it as a subprocess, parsing its JSON stdout —
  the same arm's-length relationship this repo already has with `nvidia-smi`.
  No Heimdall source is copied, modified, or linked into this codebase, and we
  don't distribute Heimdall ourselves. AGPL's copyleft (including its §13
  network clause) attaches to copying/modifying/conveying the AGPL program
  itself, not to an unrelated program that merely shells out to it over a
  documented CLI. Compare to RevA: there we copied the actual protocol
  logic/constants into our own source — that's what makes it a derivative
  work and pulls the whole repo under GPL-3.0-or-later.
