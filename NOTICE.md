# Provenance / Credits

## Base project

This code was obtained as a `.zip` from a GitHub repo with no license and no
verifiable original author:

- https://github.com/vagimtemnikov2007-cmd/turomo-monitor-for-linux

That repo has 3 commits, no `LICENSE` file, and contains only a `README.md`
plus the zip — no commit history for the actual source. The listed author
("Denis Temnikov") does not appear to be the original creator either; there is
no earlier reference found. **True upstream/author is unknown.** If you find
the real source, credit it here and replace this note.

Treat this project as unlicensed (default copyright, all rights reserved to
an unknown party) rather than open source. Fine for personal/non-commercial
homelab use; do not redistribute it as your own or assume permissive terms.

## Third-party components used by this repo

- **[Heimdall](https://github.com/kinncj/Heimdall)** by kinncj — cross-platform
  fleet hardware monitor (hub/daemon/CLI), licensed **AGPL-3.0**. Used here as
  an external binary (`heimdall-cli`) queried over gRPC/JSON, not modified or
  linked into this codebase. See `turmo/metrics.py:fetch_fleet_hosts`.
